"""LLM Planner — rule-based pipeline plan generation (MVP).

The Planner converts a natural-language goal into a candidate pipeline
plan dict.  In this MVP the "LLM" is a mock / rule-based engine that
maps keywords to pre-defined node sequences.  Every generated plan is
validated through Plan Validator before being returned.

Future providers (openai, claude) will replace the mock engine while
keeping the same Planner → Validator → Response pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.backend.app.planner.plan_validator import validate_plan


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlannerRequest:
    """Input to the LLM Planner."""

    goal: str
    provider: str = "mock"
    project_config_path: str | None = None
    constraints: dict[str, Any] | None = None


@dataclass(frozen=True)
class PlannerResponse:
    """Output from the LLM Planner."""

    ok: bool
    provider: str
    goal: str
    plan: dict[str, Any]
    validation: dict[str, Any]
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "goal": self.goal,
            "plan": self.plan,
            "validation": self.validation,
            "messages": self.messages,
            "warnings": self.warnings,
            "errors": self.errors,
        }


# ── Rule-based goal → node sequence ──────────────────────────────────────────

# Each entry: set of trigger keywords → (pipeline_id, list of node ids)
_RULES: list[tuple[set[str], str, list[str]]] = [
    (
        {"motion", "realign", "头动", "运动校正", "motion correction"},
        "planned_motion_qc",
        [
            "data_inspection",
            "spm_realign_subject",
            "motion_qc_subject",
            "motion_qc_dataset_report",
        ],
    ),
    (
        {"alff", "falff", "amplitude"},
        "planned_alff",
        [
            "data_inspection",
            "nuisance_regression_subject",
            "alff_falff_subject",
            "alff_falff_qc_dataset_report",
        ],
    ),
    (
        {"reho", "regional homogeneity"},
        "planned_reho",
        [
            "data_inspection",
            "nuisance_regression_subject",
            "reho_subject",
            "reho_qc_dataset_report",
        ],
    ),
    (
        {"smooth", "smoothing", "平滑", "spatial smoothing"},
        "planned_smooth",
        [
            "data_inspection",
            "spm_smooth_subject",
            "smoothing_qc_dataset_report",
        ],
    ),
    (
        {"full pipeline", "全流程", "complete preprocessing", "完整预处理", "full preprocessing"},
        "planned_full_preprocessing",
        [
            "data_inspection",
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "motion_qc_subject",
            "spm_smooth_subject",
            "smoothing_qc_dataset_report",
        ],
    ),
]


def _infer_backend(node_id: str) -> str:
    """Infer a backend string for a node; falls back to 'python'."""
    if node_id.startswith("spm_"):
        return "matlab-spm"
    if node_id.startswith("dpabi_"):
        return "dpabi"
    if node_id.startswith("gpu_"):
        return "gpu"
    return "python"


def _build_plan(pipeline_id: str, node_ids: list[str]) -> dict[str, Any]:
    """Build a minimal pipeline plan dict from a node sequence."""
    nodes: list[dict[str, Any]] = []
    for nid in node_ids:
        node: dict[str, Any] = {
            "id": nid,
            "backend": _infer_backend(nid),
            "depends_on": [],
            "params": {},
        }
        if nid.startswith("spm_") or nid.startswith("dpabi_"):
            node["params"]["approved"] = False
        nodes.append(node)

    # Chain dependencies sequentially
    for i in range(1, len(nodes)):
        nodes[i]["depends_on"] = [nodes[i - 1]["id"]]

    return {
        "pipeline_id": pipeline_id,
        "nodes": nodes,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def generate_plan_from_goal(
    goal: str,
    provider: str = "mock",
    constraints: dict[str, Any] | None = None,
    project_config_path: str | None = None,
) -> PlannerResponse:
    """Generate a candidate pipeline plan from a natural-language goal.

    Currently supports only 'mock' and 'rule_based' providers.
    """
    errors: list[str] = []
    warnings: list[str] = []
    messages: list[str] = []

    # ── Provider check ──
    supported = {"mock", "rule_based", "openai_compatible"}
    if provider not in supported:
        return PlannerResponse(
            ok=False,
            provider=provider,
            goal=goal,
            plan={},
            validation={},
            errors=[f"UNSUPPORTED_PROVIDER: '{provider}' not supported. Use: {sorted(supported)}"],
        )

    # ── Goal check ──
    stripped = goal.strip()
    if not stripped:
        return PlannerResponse(
            ok=False,
            provider=provider,
            goal=goal,
            plan={},
            validation={},
            errors=["EMPTY_GOAL: goal must be a non-empty string."],
        )

    # ── OpenAI-compatible provider ──
    if provider == "openai_compatible":
        from src.backend.app.planner.llm_provider import (  # noqa: E402
            call_openai_compatible_provider,
            parse_llm_plan_json,
        )

        pr = call_openai_compatible_provider(goal, constraints=constraints)
        if not pr.ok:
            return PlannerResponse(
                ok=False,
                provider=provider,
                goal=goal,
                plan={},
                validation={},
                errors=pr.errors,
            )

        try:
            plan = parse_llm_plan_json(pr.content)
        except ValueError as exc:
            return PlannerResponse(
                ok=False,
                provider=provider,
                goal=goal,
                plan={},
                validation={},
                errors=[str(exc)],
            )

        validation = validate_plan(plan)
        return PlannerResponse(
            ok=validation.ok,
            provider=provider,
            goal=goal,
            plan=plan,
            validation=validation.to_dict(),
            messages=[f"Generated plan via {provider} ({len(plan.get('nodes', []))} nodes)."],
        )

    # ── Rule matching ──
    goal_lower = stripped.lower()
    best_match: tuple[int, str, list[str]] | None = None

    for keywords, pipeline_id, node_ids in _RULES:
        score = sum(1 for kw in keywords if kw.lower() in goal_lower)
        if score > 0 and (best_match is None or score > best_match[0]):
            best_match = (score, pipeline_id, node_ids)

    if best_match is None:
        return PlannerResponse(
            ok=False,
            provider=provider,
            goal=goal,
            plan={},
            validation={},
            errors=[f"UNSUPPORTED_GOAL: could not match goal '{goal}' to any known pipeline."],
            messages=[f"Supported keywords: motion/realign, alff/falff, reho, smooth, full pipeline"],
        )

    _, pipeline_id, node_ids = best_match
    plan = _build_plan(pipeline_id, node_ids)
    validation = validate_plan(plan)

    # ── Build response ──
    messages.append(f"Matched goal to pipeline '{pipeline_id}' ({len(node_ids)} nodes).")
    if validation.warnings:
        for w in validation.warnings:
            warnings.append(f"[{w.code}] {w.message}")

    return PlannerResponse(
        ok=validation.ok and len(errors) == 0,
        provider=provider,
        goal=goal,
        plan=plan,
        validation=validation.to_dict(),
        messages=messages,
        warnings=warnings,
        errors=errors,
    )


def plan_from_request(request: PlannerRequest) -> PlannerResponse:
    """Convenience wrapper around generate_plan_from_goal."""
    return generate_plan_from_goal(
        goal=request.goal,
        provider=request.provider,
        constraints=request.constraints,
        project_config_path=request.project_config_path,
    )
