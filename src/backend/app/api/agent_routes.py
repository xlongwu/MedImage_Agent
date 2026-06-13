"""Domain route handlers extracted from src.backend.app.api.routes.

Endpoint paths and handler bodies are preserved for compatibility.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.backend.app.api._errors import raise_api_error
from src.backend.app.api.models import (
    AgentExecuteRequest,
    AgentPlanRequest,
    RetryDryRunRequest,
    RetryExecuteRequest,
    SchedulerPlanRequest,
    GpuBenchmarkRequest,
    DpabiCapabilityRequest,
    DpabiPreflightRequest,
    DpabiRunPlanRequest,
    DpabiSandboxSmokeRequest,
    DpabiSignatureProbeRequest,
    DpabiSingleFunctionRequest,
    DpabiSubjectSmoothRequest,
    DpabiSubjectWrapperReportRequest,
    DpabiWrapperValidationRequest,
    DpabiTemplateInstantiateRequest,
    DpabiTemplateExecuteRequest,
    DpabiTemplateWizardRequest,
    ArtifactPreviewRequest,
    BundleCreateRequest,
    RsfmriSpmRealignMotionQcRequest,
    RsfmriSpmSliceTimingRequest,
    RsfmriStRealignMotionQcRequest,
    RsfmriCoregistrationQcRequest,
    RsfmriSegmentationTissueQcRequest,
    RsfmriNormalizationQcRequest,
    RsfmriSmoothingQcRequest,
    RsfmriNuisanceRegressionRequest,
    RsfmriTemporalFilteringRequest,
    RsfmriAlffFalffRequest,
    RsfmriRehoRequest,
    RsfmriFunctionalConnectivityRequest,
    RsfmriGroupSummaryRequest,
    RsfmriReportExportRequest,
    RsfmriReportValidationRequest,
    ReleaseReadinessRequest,
)
from src.backend.app.core.exceptions import ConfigError
from src.backend.app.runtime.pipeline_executor import run_pipeline
from src.backend.app.tools.report_exporter import get_latest_rsfmri_report_export, list_rsfmri_report_exports
from src.backend.app.tools.report_package_validator import get_latest_rsfmri_report_validation, list_rsfmri_report_validations
from src.backend.app.runtime.agent_runtime import (
    run_orchestrator_execute,
    run_orchestrator_plan,
)
from src.backend.app.runtime.path_safety import PathSafetyError, read_safe_text_file
from src.backend.app.runtime.run_inspector import (
    inspect_run,
    list_available_runs,
    read_state_detail,
)
from src.backend.app.runtime.error_diagnoser import diagnose_run
from src.backend.app.runtime.retry_runtime import (
    dry_run_retry_plan,
    execute_retry_plan,
)
from src.backend.app.runtime.scheduler import create_scheduler_plan
from src.backend.app.schemas.pipeline_schema import load_pipeline_yaml
from src.backend.app.tools.gpu_utils import detect_gpu
from src.backend.app.tools.gpu_alff_runner import run_alff_subject
from src.backend.app.tools.dpabi_runner import run_dpabi_capability_inspection
from src.backend.app.tools.dpabi_config import write_dpabi_wrapper_scaffold
from src.backend.app.tools.dpabi_adapter import build_dpabi_input_manifest
from src.backend.app.tools.dpabi_preflight import run_dpabi_preflight
from src.backend.app.tools.dpabi_run_plan import create_dpabi_run_plan
from src.backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke
from src.backend.app.tools.dpabi_signature_runner import run_dpabi_signature_probe
from src.backend.app.tools.dpabi_contract_registry import write_dpabi_wrapper_contracts
from src.backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox
from src.backend.app.tools.dpabi_subject_wrapper import run_dpabi_subject_smooth
from src.backend.app.tools.dpabi_subject_wrapper_report import write_dpabi_subject_wrapper_report
from src.backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix
from src.backend.app.tools.dpabi_template_library import write_dpabi_template_library
from src.backend.app.tools.dpabi_template_instantiator import (
    instantiate_dpabi_template,
    execute_dpabi_template_instance,
    list_dpabi_templates,
)
from src.backend.app.tools.dpabi_template_wizard import (
    get_dpabi_template_wizard_options,
    preview_dpabi_template_instance,
    create_dpabi_template_instance_from_wizard,
)
from src.backend.app.tools.rsfmri_plan_tool import write_rsfmri_preprocessing_plan
from src.backend.app.version import APP_VERSION

router = APIRouter()


def _read_json_if_exists(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _read_text_if_exists(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

def _load_project_config(path: str) -> dict[str, Any]:
    """Load and validate a project config YAML file.

    Uses ProjectSettings.from_yaml() to validate critical fields (work_dir,
    log_dir, spm_dir, dpabi_dir) before returning the raw dict.  Validation
    errors are wrapped as ConfigError(400) to match the structured API model.
    """
    # ── structural validation (M1-T003 / M1-T005c) ──
    from src.backend.app.config import ProjectSettings  # noqa: E402

    try:
        ProjectSettings.from_yaml(path)
    except FileNotFoundError as exc:
        raise ConfigError(str(exc)) from exc
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

    # ── return raw dict for backward compat ──
    import yaml
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Project config not found: {path}")
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ConfigError(f"Failed to parse project config: {exc}") from exc

@router.post("/api/agent/plan")
def agent_plan(request: AgentPlanRequest) -> dict[str, Any]:
    result = run_orchestrator_plan(
        agent_run_id=request.agent_run_id,
        project_config_path=request.project_config_path,
        pipeline_path=request.pipeline_path,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result

@router.post("/api/agent/execute")
def agent_execute(request: AgentExecuteRequest) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="Execution requires approved=true.",
        )

    plan_path = Path("outputs/work") / "agent_runs" / request.agent_run_id / "plan.json"

    result = run_orchestrator_execute(
        agent_run_id=request.agent_run_id,
        project_config_path=request.project_config_path,
        pipeline_path=request.pipeline_path,
        plan_path=str(plan_path),
        approved=request.approved,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result

@router.get("/api/agent-runs/{agent_run_id}")
def get_agent_run(agent_run_id: str) -> dict[str, Any]:
    if "/" in agent_run_id or "\\" in agent_run_id or ".." in agent_run_id:
        raise HTTPException(status_code=400, detail="Invalid agent_run_id.")

    base = Path("outputs/work") / "agent_runs" / agent_run_id

    plan = _read_json_if_exists(base / "plan.json")
    agent_summary = _read_json_if_exists(base / "agent_summary.json")
    review_summary = _read_text_if_exists(base / "review_summary.md")
    proposed_memory_patch = _read_text_if_exists(base / "proposed_memory_patch.md")

    return {
        "ok": True,
        "agent_run_id": agent_run_id,
        "plan": plan,
        "agent_summary": agent_summary,
        "review_summary": review_summary,
        "proposed_memory_patch": proposed_memory_patch,
    }

@router.get("/api/runs")
def api_list_runs() -> dict[str, Any]:
    return list_available_runs("./work")

@router.get("/api/runs/{run_id}")
def api_inspect_run(run_id: str) -> dict[str, Any]:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")
    return inspect_run(run_id, "./work")

@router.get("/api/runs/{run_id}/state-detail")
def api_state_detail(run_id: str, path: str = Query(...)) -> dict[str, Any]:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")

    result = read_state_detail(run_id=run_id, state_path=path, work_dir="./work")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/api/runs/{run_id}/diagnosis")
def api_diagnose_run(run_id: str) -> dict[str, Any]:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")

    result = diagnose_run(run_id=run_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result

@router.post("/api/retry/dry-run")
def api_retry_dry_run(payload: RetryDryRunRequest) -> dict[str, Any]:
    run_id = payload.run_id
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")

    result = dry_run_retry_plan(
        run_id=run_id,
        retry_run_id=payload.retry_run_id,
    )
    return result

@router.post("/api/retry/execute")
def api_retry_execute(payload: RetryExecuteRequest) -> dict[str, Any]:
    run_id = payload.run_id
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")

    if not payload.approved:
        raise HTTPException(status_code=403, detail="Retry execution requires approved=true.")

    result = execute_retry_plan(
        run_id=run_id,
        project_config_path=payload.project_config_path,
        retry_run_id=payload.retry_run_id,
        approved=payload.approved,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result

@router.get("/api/retry-runs/{retry_run_id}")
def api_get_retry_run(retry_run_id: str) -> dict[str, Any]:
    if "/" in retry_run_id or "\\" in retry_run_id or ".." in retry_run_id:
        raise HTTPException(status_code=400, detail="Invalid retry_run_id.")

    base = Path("outputs/work") / "retry_runs" / retry_run_id

    dry_run_summary = _read_json_if_exists(base / "dry_run_summary.json")
    retry_execution_summary = _read_json_if_exists(base / "retry_execution_summary.json")

    return {
        "ok": True,
        "retry_run_id": retry_run_id,
        "dry_run_summary": dry_run_summary,
        "retry_execution_summary": retry_execution_summary,
    }

@router.post("/api/scheduler/plan")
def api_scheduler_plan(request: SchedulerPlanRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        pipeline = load_pipeline_yaml(request.pipeline_path)
        result = create_scheduler_plan(pipeline, project_config)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise_api_error(exc)
