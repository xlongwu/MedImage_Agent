"""Plan Adapter — convert reviewed plans to executor-compatible pipeline dicts.

This module bridges the gap between the candidate plans produced by the
LLM Planner / Plan Review Console and the pipeline dicts expected by
the Pipeline Executor (via load_pipeline_yaml / PipelineSpec).

It also classifies nodes by execution policy so that the gated execution
API can decide which nodes are safe to run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlanAdapterResult:
    """Result of adapting a reviewed plan for execution."""

    ok: bool
    pipeline: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    policy: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "pipeline": self.pipeline,
            "errors": self.errors,
            "warnings": self.warnings,
            "policy": self.policy,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _catalog_map() -> dict[str, Any]:
    from src.backend.app.runtime.tool_catalog import build_tool_catalog  # noqa: E402
    return {item.id: item for item in build_tool_catalog()}


# ── Core conversion ──────────────────────────────────────────────────────────

def reviewed_plan_to_pipeline_dict(
    plan: dict[str, Any],
    *,
    name: str | None = None,
    description: str | None = None,
    modality: str = "rsfmri",
    execution_backend: str = "reviewed-plan",
) -> dict[str, Any]:
    """Convert a reviewed plan dict to an executor-compatible pipeline dict.

    Raises ValueError on structural errors (duplicate ids, unknown deps).
    """
    if not isinstance(plan, dict):
        raise ValueError("Plan must be a dictionary.")

    catalog = _catalog_map()
    errors: list[str] = []
    nodes_out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    pipeline_id = plan.get("pipeline_id", "reviewed_plan")
    plan_nodes = plan.get("nodes", []) or []

    # Collect node ids for dependency validation
    node_ids = set()
    for n in plan_nodes:
        nid = n.get("id")
        if nid:
            node_ids.add(nid)

    for i, node in enumerate(plan_nodes):
        if not isinstance(node, dict):
            raise ValueError(f"Node at index {i} must be a dictionary.")

        nid = node.get("id")
        if not nid:
            raise ValueError(f"Node at index {i} is missing an 'id'.")

        if nid in seen_ids:
            raise ValueError(f"Duplicate node id: {nid}.")
        seen_ids.add(nid)

        cat = catalog.get(nid)

        # Backend fill
        backend = node.get("backend")
        if not backend:
            if cat:
                backend = cat.backend
            else:
                errors.append(f"Node '{nid}' has no backend and is not in Tool Catalog.")
                backend = "unknown"

        # Dependencies
        deps = node.get("depends_on", []) or []
        if not isinstance(deps, list):
            raise ValueError(f"Node '{nid}' has non-list 'depends_on'.")
        for dep in deps:
            if dep not in node_ids:
                raise ValueError(f"Node '{nid}' depends on unknown node: {dep}.")

        # Params
        params = node.get("params", {}) or {}
        if not isinstance(params, dict):
            raise ValueError(f"Node '{nid}' has non-dict 'params'.")

        nodes_out.append({
            "id": nid,
            "name": cat.name if cat else str(nid),
            "agent": "system",
            "backend": backend,
            "depends_on": list(deps),
            "params": dict(params),
            "parallel_level": cat.parallel_level if cat else "project",
            "gpu_supported": False,
            "cache": False,
            "inputs": [],
            "outputs": [],
        })

    return {
        "pipeline_id": name or pipeline_id,
        "version": "0.1.0",
        "modality": modality,
        "description": description or "Pipeline converted from reviewed plan.",
        "execution": {
            "run_id": f"reviewed_{pipeline_id}",
            "stop_on_failure": True,
            "backend": execution_backend,
        },
        "nodes": nodes_out,
    }


# ── Node classification ──────────────────────────────────────────────────────

def _satisfies_sandbox_contract(node: dict[str, Any]) -> bool:
    """Check if a spm_realign_subject node satisfies the sandbox contract.

    Requires sandbox_mode=true and input_bold non-empty.
    """
    params = node.get("params", {}) or {}
    sandbox = params.get("sandbox_mode")
    input_bold = params.get("input_bold")
    if sandbox is not True:
        return False
    if not input_bold or not isinstance(input_bold, str) or not input_bold.strip():
        return False
    return True


def classify_plan_nodes(plan: dict[str, Any]) -> dict[str, list[str]]:
    """Classify every node in a reviewed plan by execution policy.

    Returns a dict with allowed_* and blocked_* lists for gated execution.
    """
    catalog = _catalog_map()
    result: dict[str, list[str]] = {
        "allowed_python_nodes": [],
        "allowed_gpu_nodes": [],
        "allowed_contract_nodes": [],
        "allowed_spm_smoke_nodes": [],             # M6-T004b
        "allowed_spm_realign_sandbox_nodes": [],    # M6-T005d
        "blocked_spm_nodes": [],
        "blocked_dpabi_execution_nodes": [],
        "blocked_gui_nodes": [],
        "blocked_manual_required_nodes": [],
        "blocked_unknown_nodes": [],
        "blocked_uncataloged_nodes": [],
    }

    plan_nodes = plan.get("nodes", []) or []
    for node in plan_nodes:
        nid = node.get("id", "")
        if not nid:
            continue
        cat = catalog.get(nid)

        # Unknown / uncataloged
        if cat is None:
            result["blocked_unknown_nodes"].append(nid)
            continue
        if "uncataloged" in cat.tags:
            result["blocked_uncataloged_nodes"].append(nid)
            continue

        # Manual required
        if cat.manual_required:
            result["blocked_manual_required_nodes"].append(nid)
            continue

        # SPM — M6-T004b: spm_smoke_test, M6-T005d: sandbox-only realign
        if nid == "spm_smoke_test":
            result["allowed_spm_smoke_nodes"].append(nid)
            continue
        if nid == "spm_realign_subject" and _satisfies_sandbox_contract(node):
            result["allowed_spm_realign_sandbox_nodes"].append(nid)
            continue
        if nid.startswith("spm_") or cat.backend == "matlab-spm":
            result["blocked_spm_nodes"].append(nid)
            continue

        # DPABI execution
        if nid.startswith("dpabi_") and not (
            "contract" in nid or "capability" in nid or "preflight" in nid
            or "scaffold" in nid or "signature" in nid or "template" in nid
            or "manifest" in nid or "run_plan" in nid
        ):
            result["blocked_dpabi_execution_nodes"].append(nid)
            continue

        # GUI
        if nid.startswith("gui_") or cat.backend == "gui-agent":
            result["blocked_gui_nodes"].append(nid)
            continue

        # Allowed categories
        if cat.backend == "gpu":
            result["allowed_gpu_nodes"].append(nid)
        elif "contract" in cat.tags or "capability" in nid or "preflight" in nid:
            result["allowed_contract_nodes"].append(nid)
        else:
            result["allowed_python_nodes"].append(nid)

    return result


# ── Convenience ──────────────────────────────────────────────────────────────

def adapt_reviewed_plan(
    plan: dict[str, Any],
    *,
    name: str | None = None,
    description: str | None = None,
) -> PlanAdapterResult:
    """Full adaptation: convert + classify in one call."""
    errors: list[str] = []
    warnings: list[str] = []
    pipeline: dict[str, Any] | None = None
    policy: dict[str, list[str]] = {}

    # Classify
    try:
        policy = classify_plan_nodes(plan)
    except Exception as exc:
        errors.append(f"Node classification failed: {exc}")

    # Check for blocked nodes
    blocked = (policy.get("blocked_spm_nodes", []) +
               policy.get("blocked_dpabi_execution_nodes", []) +
               policy.get("blocked_gui_nodes", []) +
               policy.get("blocked_manual_required_nodes", []) +
               policy.get("blocked_unknown_nodes", []) +
               policy.get("blocked_uncataloged_nodes", []))
    if blocked:
        warnings.append(f"Plan contains {len(blocked)} blocked node(s): {', '.join(blocked)}")

    # Convert
    try:
        pipeline = reviewed_plan_to_pipeline_dict(
            plan, name=name, description=description,
        )
    except ValueError as exc:
        errors.append(str(exc))

    return PlanAdapterResult(
        ok=len(errors) == 0,
        pipeline=pipeline,
        errors=errors,
        warnings=warnings,
        policy=policy,
    )
