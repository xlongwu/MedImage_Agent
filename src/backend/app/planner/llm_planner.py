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

# Native full preprocessing is only selected when a real project context already
# exposes registered NIfTI/BIDS evidence. Generic motion-planning behavior stays
# backward compatible.
_NATIVE_FULL_GOAL_TERMS = (
    "rs-fmri",
    "preprocessing",
    "preprocess",
    "slice timing",
    "realignment",
    "realign",
    "motion qc",
    "nuisance regression",
    "detrending",
    "temporal filtering",
    "roi time series",
    "functional connectivity",
    "预处理",
    "全流程",
)

_NATIVE_FULL_CONFIRMATIONS: dict[str, bool] = {
    "confirm_reviewed_native_execution": True,
    "confirm_rawdata_readonly": True,
    "confirm_no_external_tools": True,
    "confirm_research_use_only": True,
    "confirm_no_clinical_use": True,
}

# Each entry: set of trigger keywords → (pipeline_id, list of node ids)
_RULES: list[tuple[set[str], str, list[str]]] = [
    (
        {"realign", "头动", "运动校正", "motion correction"},
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
        {"rs-fmri preprocessing", "resting-state preprocessing", "fMRI preprocessing", "motion QC", "静息态预处理"},
        "rsfmri_preproc_mvp",
        [
            "data_readiness_check",
            "bids_validation_check",
            "rsfmri_bold_reference_check",
            "rsfmri_motion_qc_plan",
            "rsfmri_preprocessing_plan_stub",
            "rsfmri_report_plan_stub",
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
    if node_id.startswith("native_preproc_"):
        return "native_python"
    if node_id.startswith("spm_"):
        return "matlab-spm"
    if node_id.startswith("dpabi_"):
        return "dpabi"
    if node_id.startswith("gpu_"):
        return "gpu"
    return "python"


def _build_plan(
    pipeline_id: str,
    node_ids: list[str],
    *,
    goal: str,
    provider: str,
) -> dict[str, Any]:
    """Build a minimal reviewed-plan-shaped dict from a node sequence."""
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
        "project_context": {
            "project_id": None,
            "project_config_path": None,
            "rawdata_dir": None,
            "dataset_index_path": None,
            "source": "planner_minimal_mock",
            "diagnostics": {},
        },
        "goal": goal,
        "nodes": nodes,
        "metadata": {
            "planner": "deterministic_keyword_mock",
            "provider": provider,
            "capability_level": "metadata_only",
            "external_api_used": False,
            "execution_enabled": False,
        },
    }


# ── Public API ────────────────────────────────────────────────────────────────

def _project_context_from_constraints(
    constraints: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(constraints, dict):
        return {}
    context = constraints.get("project_context")
    return dict(context) if isinstance(context, dict) else {}


def _diagnostics_from_context(context: dict[str, Any]) -> dict[str, Any]:
    diagnostics = context.get("diagnostics")
    return dict(diagnostics) if isinstance(diagnostics, dict) else {}


def _has_registered_nifti_evidence(context: dict[str, Any]) -> bool:
    diagnostics = _diagnostics_from_context(context)
    status = str(diagnostics.get("status") or "").upper()
    if status in {"CONVERTED_BIDS", "MIXED", "NIFTI", "BIDS"}:
        return True
    if diagnostics.get("converted_bids_available") is True:
        return True
    count = diagnostics.get("nifti_file_count") or diagnostics.get("nifti_files")
    try:
        return int(count) > 0
    except (TypeError, ValueError):
        return False


def _matches_native_full_goal(goal_lower: str) -> bool:
    score = sum(1 for term in _NATIVE_FULL_GOAL_TERMS if term.lower() in goal_lower)
    has_preproc_intent = (
        "preprocessing" in goal_lower
        or "preprocess" in goal_lower
        or "预处理" in goal_lower
        or "全流程" in goal_lower
    )
    has_downstream_intent = any(
        term in goal_lower
        for term in (
            "functional connectivity",
            "roi time series",
            "temporal filtering",
            "nuisance regression",
            "detrending",
        )
    )
    return score >= 2 and (has_preproc_intent or has_downstream_intent)


def _build_native_full_preprocessing_plan(
    *,
    goal: str,
    provider: str,
    project_context: dict[str, Any],
) -> dict[str, Any]:
    diagnostics = _diagnostics_from_context(project_context)
    conversion_run_id = str(
        diagnostics.get("preprocessing_conversion_run_id")
        or diagnostics.get("conversion_run_id")
        or ""
    )
    native_params: dict[str, Any] = {
        "project_id": str(project_context.get("project_id") or ""),
        "project_dir": str(diagnostics.get("project_dir") or ""),
        "conversion_run_id": conversion_run_id,
        "confirmations": dict(_NATIVE_FULL_CONFIRMATIONS),
        "stage_overrides": {},
    }
    return {
        "pipeline_id": "native_full_preprocessing",
        "project_context": {
            "project_id": None,
            "project_config_path": None,
            "rawdata_dir": None,
            "dataset_index_path": None,
            "source": "planner_minimal_mock",
            "diagnostics": {},
        },
        "goal": goal,
        "nodes": [
            {
                "id": "native_preproc_full_execute",
                "backend": "native_python",
                "depends_on": [],
                "params": native_params,
            }
        ],
        "metadata": {
            "planner": "deterministic_keyword_mock",
            "provider": provider,
            "capability_level": "computed",
            "external_api_used": False,
            "execution_enabled": False,
            "execution_requires_approval_gate": True,
            "native_preprocessing": True,
        },
    }


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
    project_context = _project_context_from_constraints(constraints)
    if (
        _has_registered_nifti_evidence(project_context)
        and _matches_native_full_goal(goal_lower)
    ):
        plan = _build_native_full_preprocessing_plan(
            goal=stripped,
            provider=provider,
            project_context=project_context,
        )
        validation = validate_plan(plan)
        messages.append(
            "Matched goal to native full preprocessing using registered NIfTI/BIDS evidence."
        )
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
    plan = _build_plan(
        pipeline_id,
        node_ids,
        goal=stripped,
        provider=provider,
    )
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
