"""Plan Validator — static safety & correctness checks for pipeline plans.

The Plan Validator sits between the LLM Planner and the Pipeline Executor.
It validates that a candidate plan (dict) references only known nodes,
has legal dependencies, is acyclic, and surfaces risk information from
the Tool Catalog so that the Human Approval Gate can make informed decisions.

This module is read-only: it never executes any node runner, never calls
MATLAB/SPM/DPABI, and never writes files.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


# ── Output dataclasses ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlanValidationIssue:
    """A single issue found during plan validation."""

    code: str
    message: str
    node_id: str | None = None
    severity: str = "error"  # "error" | "warning"


@dataclass(frozen=True)
class PlanValidationResult:
    """Full result of validating a pipeline plan."""

    ok: bool
    errors: list[PlanValidationIssue] = field(default_factory=list)
    warnings: list[PlanValidationIssue] = field(default_factory=list)
    nodes_total: int = 0
    approval_required_nodes: list[str] = field(default_factory=list)
    manual_required_nodes: list[str] = field(default_factory=list)
    high_risk_nodes: list[str] = field(default_factory=list)
    unknown_nodes: list[str] = field(default_factory=list)
    topological_order: list[str] = field(default_factory=list)
    risk_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "ok": self.ok,
            "errors": [
                {"code": e.code, "message": e.message,
                 "node_id": e.node_id, "severity": e.severity}
                for e in self.errors
            ],
            "warnings": [
                {"code": w.code, "message": w.message,
                 "node_id": w.node_id, "severity": w.severity}
                for w in self.warnings
            ],
            "nodes_total": self.nodes_total,
            "approval_required_nodes": self.approval_required_nodes,
            "manual_required_nodes": self.manual_required_nodes,
            "high_risk_nodes": self.high_risk_nodes,
            "unknown_nodes": self.unknown_nodes,
            "topological_order": self.topological_order,
            "risk_summary": self.risk_summary,
        }


# ── Public entry point ────────────────────────────────────────────────────────

def validate_plan(plan: dict[str, Any]) -> PlanValidationResult:
    """Validate a pipeline plan dict and return a structured result.

    The plan dict should have:
      - pipeline_id: str
      - nodes: list[dict] (each with at least "id")

    Returns a PlanValidationResult.  ok=True means no errors (warnings
    are advisory and do not block ok).
    """
    errors: list[PlanValidationIssue] = []
    warnings: list[PlanValidationIssue] = []

    # ── 1. Structural checks ──
    if not isinstance(plan, dict):
        return PlanValidationResult(
            ok=False,
            errors=[PlanValidationIssue(
                code="INVALID_PLAN_TYPE",
                message="Plan must be a dictionary.",
            )],
        )

    pipeline_id = plan.get("pipeline_id")
    if not pipeline_id or not isinstance(pipeline_id, str):
        errors.append(PlanValidationIssue(
            code="MISSING_PIPELINE_ID",
            message="Plan must have a non-empty 'pipeline_id' string.",
        ))

    nodes = plan.get("nodes")
    if not isinstance(nodes, list) or len(nodes) == 0:
        errors.append(PlanValidationIssue(
            code="MISSING_OR_EMPTY_NODES",
            message="Plan must have a non-empty 'nodes' list.",
        ))
        return _build_result(plan, errors, warnings)

    # ── Per-node structural checks ──
    node_ids: list[str] = []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(PlanValidationIssue(
                code="INVALID_NODE_TYPE",
                message=f"Node at index {i} must be a dictionary.",
            ))
            continue
        nid = node.get("id")
        if not nid or not isinstance(nid, str):
            errors.append(PlanValidationIssue(
                code="MISSING_NODE_ID",
                message=f"Node at index {i} is missing a valid 'id'.",
            ))
            continue
        node_ids.append(nid)
        deps = node.get("depends_on")
        if deps is not None and not isinstance(deps, list):
            errors.append(PlanValidationIssue(
                code="INVALID_DEPENDS_ON",
                message=f"Node '{nid}' has non-list 'depends_on'.",
                node_id=nid,
            ))
        params = node.get("params")
        if params is not None and not isinstance(params, dict):
            errors.append(PlanValidationIssue(
                code="INVALID_PARAMS",
                message=f"Node '{nid}' has non-dict 'params'.",
                node_id=nid,
            ))

    if not node_ids:
        return _build_result(plan, errors, warnings)

    # ── 2. Duplicate node ids ──
    seen: set[str] = set()
    for nid in node_ids:
        if nid in seen:
            errors.append(PlanValidationIssue(
                code="DUPLICATE_NODE_ID",
                message=f"Duplicate node id: '{nid}'.",
                node_id=nid,
            ))
        seen.add(nid)

    # ── 3. Tool Catalog validation ──
    catalog = _build_catalog_map()
    catalog_ids = set(catalog.keys())

    unknown_nodes: list[str] = []
    for nid in node_ids:
        if nid not in catalog_ids:
            unknown_nodes.append(nid)
            errors.append(PlanValidationIssue(
                code="UNKNOWN_NODE_ID",
                message=f"Node id '{nid}' is not in the Tool Catalog.",
                node_id=nid,
            ))

    # ── 4. Dependency checks ──
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if not nid or nid in unknown_nodes:
            continue
        deps = node.get("depends_on", []) or []
        for dep in deps:
            if dep not in node_ids:
                errors.append(PlanValidationIssue(
                    code="UNKNOWN_DEPENDENCY",
                    message=f"Node '{nid}' depends on '{dep}' which is not in the plan.",
                    node_id=nid,
                ))
            if dep == nid:
                errors.append(PlanValidationIssue(
                    code="SELF_DEPENDENCY",
                    message=f"Node '{nid}' depends on itself.",
                    node_id=nid,
                ))

    # ── 5. Cycle detection (Kahn's algorithm) ──
    topo_order: list[str] = []
    has_dep_error = any(e.code in ("UNKNOWN_DEPENDENCY", "SELF_DEPENDENCY") for e in errors)
    if not has_dep_error:
        topo_order = _topological_sort(node_ids, nodes)
        if len(topo_order) < len(node_ids):
            errors.append(PlanValidationIssue(
                code="DEPENDENCY_CYCLE",
                message="The plan contains a dependency cycle.",
            ))

    # ── 6. Approval / risk from Tool Catalog ──
    approval_required: list[str] = []
    manual_required: list[str] = []
    high_risk: list[str] = []
    uncataloged_count = 0

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if not nid or nid in unknown_nodes:
            continue
        item = catalog.get(nid)
        if item is None:
            continue

        if item.requires_approval:
            approval_required.append(nid)
            node_params = node.get("params", {}) or {}
            if "approved" not in node_params:
                warnings.append(PlanValidationIssue(
                    code="APPROVAL_REQUIRED",
                    message=f"Node '{nid}' requires approval but 'approved' is not set in params.",
                    node_id=nid,
                    severity="warning",
                ))

        if item.manual_required:
            manual_required.append(nid)

        if item.risk_level == "high":
            high_risk.append(nid)

        if "uncataloged" in item.tags or item.description.startswith("No catalog metadata yet"):
            uncataloged_count += 1
            warnings.append(PlanValidationIssue(
                code="UNCATALOGED_METADATA",
                message=f"Node '{nid}' uses fallback metadata — consider adding explicit catalog entry.",
                node_id=nid,
                severity="warning",
            ))

        # Backend mismatch
        node_backend = node.get("backend")
        if node_backend and node_backend != item.backend and item.backend != "unknown":
            warnings.append(PlanValidationIssue(
                code="BACKEND_MISMATCH",
                message=f"Node '{nid}' declares backend '{node_backend}' but catalog says '{item.backend}'.",
                node_id=nid,
                severity="warning",
            ))

    # ── 7. Build result ──
    risk_summary = {
        "nodes_total": len(node_ids),
        "requires_approval": len(approval_required) > 0,
        "approval_required_count": len(approval_required),
        "manual_required": len(manual_required) > 0,
        "manual_required_count": len(manual_required),
        "high_risk_count": len(high_risk),
        "unknown_nodes_count": len(unknown_nodes),
        "has_uncataloged_metadata": uncataloged_count > 0,
    }

    return PlanValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        nodes_total=len(node_ids),
        approval_required_nodes=approval_required,
        manual_required_nodes=manual_required,
        high_risk_nodes=high_risk,
        unknown_nodes=unknown_nodes,
        topological_order=topo_order if len(topo_order) == len(node_ids) else [],
        risk_summary=risk_summary,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_catalog_map() -> dict[str, Any]:
    """Build {node_id: ToolCatalogItem} lookup."""
    from src.backend.app.runtime.tool_catalog import build_tool_catalog  # noqa: E402
    return {item.id: item for item in build_tool_catalog()}


def _topological_sort(node_ids: list[str], nodes: list[dict[str, Any]]) -> list[str]:
    """Kahn's algorithm. Returns topological order or partial on cycle."""
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if not nid:
            continue
        for dep in node.get("depends_on", []) or []:
            if dep in adj:
                adj[dep].append(nid)
                in_degree[nid] += 1

    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbor in adj.get(nid, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


def _build_result(
    plan: dict[str, Any],
    errors: list[PlanValidationIssue],
    warnings: list[PlanValidationIssue],
) -> PlanValidationResult:
    """Build result when structural checks block further validation."""
    return PlanValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
