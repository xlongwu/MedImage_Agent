from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.planner.llm_provider import PlannerProviderError, get_planner_provider_from_env
from src.backend.app.runtime.node_registry import get_node_runner
from src.backend.app.runtime.pipeline_executor import run_pipeline
from src.backend.app.schemas.pipeline_schema import PipelineValidationError, load_pipeline_yaml


PLANNER_ROOT = Path("outputs/work/planner")
EXTERNAL_BACKEND_TOKENS = ("matlab", "spm", "dpabi", "gui")
CANDIDATE_PIPELINES = [
    "examples/pipeline_mvp.yaml",
    "examples/pipeline_rsfmri_core_plan.yaml",
    "examples/pipeline_rsfmri_functional_connectivity.yaml",
    "examples/pipeline_rsfmri_reho.yaml",
    "examples/pipeline_rsfmri_alff_falff.yaml",
    "examples/pipeline_gpu_alff.yaml",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:12]}"


def _normalize_tokens(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item).lower() for item in value)
    return str(value or "").lower()


def _choose_pipeline_path(request: dict[str, Any]) -> str:
    task = _normalize_tokens(request.get("downstream_task"))
    constraints = _normalize_tokens(request.get("constraints"))
    available = _normalize_tokens(request.get("available_data"))

    if "no matlab" in constraints or "python only" in constraints:
        return "examples/pipeline_mvp.yaml"
    if "functional connectivity" in task or "connectivity" in task or " fc" in f" {task}":
        return "examples/pipeline_rsfmri_functional_connectivity.yaml"
    if "reho" in task or "regional homogeneity" in task:
        return "examples/pipeline_rsfmri_reho.yaml"
    if "alff" in task or "falff" in task:
        return "examples/pipeline_rsfmri_alff_falff.yaml"
    if "gpu" in constraints or "gpu" in available:
        return "examples/pipeline_gpu_alff.yaml"
    return "examples/pipeline_rsfmri_core_plan.yaml"


def _validate_pipeline_path(path: str | None) -> tuple[bool, str | None]:
    if not path:
        return False, "Missing recommended_pipeline_path."
    target = Path(path)
    normalized = str(target).replace("\\", "/")
    if target.suffix.lower() not in {".yaml", ".yml"}:
        return False, f"Planner pipeline must be a YAML file: {path}"
    if normalized.startswith("../") or "/../" in normalized:
        return False, f"Planner pipeline path cannot traverse directories: {path}"
    if not normalized.startswith("examples/"):
        return False, f"Planner pipeline path must stay under examples/: {path}"
    return True, None


def _pipeline_nodes(pipeline_path: str) -> list[dict[str, Any]]:
    pipeline = load_pipeline_yaml(pipeline_path)
    return [
        {
            "id": node.id,
            "name": node.name,
            "backend": node.backend,
            "parallel_level": node.parallel_level,
            "depends_on": node.depends_on,
            "gpu_supported": node.gpu_supported,
        }
        for node in pipeline.nodes
    ]


def _is_external_backend(backend: str, node_id: str = "") -> bool:
    haystack = f"{backend} {node_id}".lower()
    return any(token in haystack for token in EXTERNAL_BACKEND_TOKENS)


def _try_llm_pipeline(request: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    provider = get_planner_provider_from_env()
    if provider is None:
        return None, {
            "llm_used": False,
            "planner_mode": "deterministic_fallback",
            "llm_note": "LLM planner disabled; deterministic disease/task mapping was used.",
            "llm_errors": [],
        }

    try:
        response = provider.draft_plan(request, CANDIDATE_PIPELINES)
    except PlannerProviderError as exc:
        return None, {
            "llm_used": True,
            "planner_mode": "llm_provider_error",
            "llm_note": "LLM planner failed; draft is marked invalid until corrected.",
            "llm_errors": [str(exc)],
        }

    pipeline_path = response.payload.get("recommended_pipeline_path")
    ok, error = _validate_pipeline_path(str(pipeline_path) if pipeline_path else None)
    provider_note = {
        "llm_used": True,
        "planner_mode": "llm_structured_draft",
        "llm_provider": response.provider,
        "llm_model": response.model,
        "llm_payload": response.payload,
        "llm_errors": [] if ok else [error],
        "llm_note": "LLM produced a structured draft; deterministic validation still controls execution.",
    }
    return (str(pipeline_path) if ok else None), provider_note


def draft_pipeline_plan(payload: dict[str, Any]) -> dict[str, Any]:
    request = {
        "disease_type": payload.get("disease_type", "unspecified"),
        "modality": payload.get("modality", "rs-fMRI"),
        "downstream_task": payload.get("downstream_task", "standard preprocessing"),
        "available_data": payload.get("available_data", ["T1w", "BOLD"]),
        "constraints": payload.get("constraints", []),
        "project_config_path": payload.get("project_config_path", "examples/project_config_dataset.yaml"),
    }
    llm_pipeline_path, llm_note = _try_llm_pipeline(request)
    pipeline_path = payload.get("pipeline_path") or llm_pipeline_path or _choose_pipeline_path(request)
    plan_id = payload.get("plan_id") or _stable_id("planner", request | {"pipeline_path": pipeline_path})
    path_ok, path_error = _validate_pipeline_path(pipeline_path)
    errors = [] if path_ok else [str(path_error)]
    errors.extend(llm_note.get("llm_errors", []))
    candidate_nodes: list[dict[str, Any]] = []
    if path_ok:
        try:
            candidate_nodes = _pipeline_nodes(pipeline_path)
        except Exception as exc:
            errors.append(str(exc))

    draft = {
        "ok": not errors,
        "plan_id": plan_id,
        "created_at": _now_iso(),
        "advice_only": True,
        "requires_human_confirmation": True,
        "will_execute_pipeline": False,
        "will_modify_data": False,
        "clinical_conclusion": False,
        "request": request,
        "recommended_pipeline_path": pipeline_path,
        "rationale": [
            "Disease/task metadata is used to select a preprocessing template.",
            "Execution remains delegated to the deterministic pipeline runtime.",
            "SPM/DPABI/GUI steps require explicit approval before execution.",
        ],
        "candidate_nodes": candidate_nodes,
        "safety_policy": {
            "rawdata_readonly": True,
            "llm_can_execute_tools": False,
            "requires_approval_for_real_backends": True,
            "blocked_dpabi_functions": ["DPARSF_run", "DPARSFA_run", "DPABI GUI batch execution"],
        },
        "errors": errors,
    }
    draft.update(llm_note)

    out_dir = PLANNER_ROOT / "drafts"
    out_dir.mkdir(parents=True, exist_ok=True)
    draft_path = out_dir / f"{plan_id}.json"
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    draft["draft_path"] = str(draft_path)
    return draft


def _load_draft(plan_id: str) -> dict[str, Any]:
    path = PLANNER_ROOT / "drafts" / f"{plan_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Planner draft not found: {plan_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pipeline_plan(payload: dict[str, Any]) -> dict[str, Any]:
    draft = payload.get("draft")
    if not draft and payload.get("plan_id"):
        draft = _load_draft(str(payload["plan_id"]))
    if not draft:
        draft = draft_pipeline_plan(payload)

    errors: list[str] = []
    warnings: list[str] = []
    pipeline_path = draft.get("recommended_pipeline_path") or payload.get("pipeline_path")

    try:
        pipeline = load_pipeline_yaml(pipeline_path)
    except (PipelineValidationError, FileNotFoundError) as exc:
        return {
            "ok": False,
            "plan_id": draft.get("plan_id"),
            "pipeline_path": pipeline_path,
            "errors": [str(exc)],
            "warnings": warnings,
        }

    for node in pipeline.nodes:
        try:
            get_node_runner(node.id)
        except KeyError:
            errors.append(f"No registered node runner for: {node.id}")
        if _is_external_backend(node.backend, node.id):
            warnings.append(f"Node '{node.id}' uses external backend '{node.backend}' and needs approval.")

    result = {
        "ok": len(errors) == 0,
        "plan_id": draft.get("plan_id"),
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_path": pipeline_path,
        "nodes_total": len(pipeline.nodes),
        "registered_nodes": len(pipeline.nodes) - len(errors),
        "requires_approval": bool(warnings),
        "execution_allowed": len(errors) == 0,
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "safety_policy": draft.get("safety_policy", {}),
    }

    out_dir = PLANNER_ROOT / "validations"
    out_dir.mkdir(parents=True, exist_ok=True)
    validation_path = out_dir / f"{draft.get('plan_id', 'adhoc')}.json"
    validation_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["validation_path"] = str(validation_path)
    return result


def execute_pipeline_plan(payload: dict[str, Any]) -> dict[str, Any]:
    approved = bool(payload.get("approved", False))
    draft = payload.get("draft")
    if not draft and payload.get("plan_id"):
        draft = _load_draft(str(payload["plan_id"]))
    if not draft:
        draft = draft_pipeline_plan(payload)

    validation = validate_pipeline_plan({"draft": draft})
    if not validation.get("ok"):
        return {"ok": False, "status": "INVALID", "validation": validation}

    if validation.get("requires_approval") and not approved:
        return {
            "ok": False,
            "status": "APPROVAL_REQUIRED",
            "plan_id": draft.get("plan_id"),
            "errors": ["Planner execution requires approved=true for external-backend plans."],
            "validation": validation,
        }

    project_config_path = payload.get("project_config_path") or draft.get("request", {}).get(
        "project_config_path",
        "examples/project_config_dataset.yaml",
    )
    pipeline_path = validation["pipeline_path"]
    summary = run_pipeline(project_config_path, pipeline_path)

    execution = {
        "ok": summary.get("status") in {"SUCCESS", "PARTIAL"},
        "plan_id": draft.get("plan_id"),
        "approved": approved,
        "requires_approval": validation.get("requires_approval", False),
        "approval": {
            "approved": approved,
            "required": validation.get("requires_approval", False),
            "reason": "external backend nodes present" if validation.get("requires_approval") else "python-only plan",
        },
        "project_config_path": project_config_path,
        "pipeline_path": pipeline_path,
        "summary": summary,
        "validation": validation,
        "executed_at": _now_iso(),
    }
    out_dir = PLANNER_ROOT / "executions"
    out_dir.mkdir(parents=True, exist_ok=True)
    execution_path = out_dir / f"{draft.get('plan_id', 'adhoc')}.json"
    execution_path.write_text(json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8")
    execution["execution_path"] = str(execution_path)
    return execution


def get_planner_history(limit: int = 20) -> dict[str, Any]:
    drafts = []
    for path in sorted((PLANNER_ROOT / "drafts").glob("*.json"), reverse=True):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            drafts.append({
                "plan_id": item.get("plan_id"),
                "created_at": item.get("created_at"),
                "recommended_pipeline_path": item.get("recommended_pipeline_path"),
                "request": item.get("request", {}),
                "draft_path": str(path),
            })
        except Exception:
            continue
        if len(drafts) >= limit:
            break
    executions = []
    for path in sorted((PLANNER_ROOT / "executions").glob("*.json"), reverse=True):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            executions.append({
                "plan_id": item.get("plan_id"),
                "executed_at": item.get("executed_at"),
                "ok": item.get("ok"),
                "pipeline_path": item.get("pipeline_path"),
                "execution_path": str(path),
            })
        except Exception:
            continue
        if len(executions) >= limit:
            break
    return {"ok": True, "drafts": drafts, "executions": executions, "limit": limit}
