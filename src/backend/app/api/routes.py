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


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "medimage-agent-api",
        "status": "healthy",
        "version": APP_VERSION,
    }


@router.get("/api/project-config")
def get_project_config(
    path: str = Query(default="examples/project_config_dataset.yaml"),
) -> dict[str, Any]:
    try:
        data = read_safe_text_file(path)
        import yaml
        parsed = yaml.safe_load(data["content"]) or {}
        return {
            "ok": True,
            "path": data["relative_path"],
            "config": parsed,
        }
    except Exception as exc:
        raise_api_error(exc, error_cls=ConfigError)


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


@router.post("/api/dpabi/capability")
def api_dpabi_capability(payload: DpabiCapabilityRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(payload.project_config_path)
        runtime = project_config.get("runtime", {})
        third_party = project_config.get("third_party", {})

        result = run_dpabi_capability_inspection(
            matlab_command=runtime.get("matlab_command", "matlab"),
            dpabi_dir=third_party.get("dpabi_dir", "./third_party/DPABI"),
            work_dir=payload.work_dir,
            log_dir=payload.log_dir,
            matlab_script_dir="./matlab",
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/scaffold")
def api_dpabi_scaffold(payload: DpabiCapabilityRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(payload.project_config_path)
        report_dir = project_config.get("runtime", {}).get("report_dir", "./reports")

        result = write_dpabi_wrapper_scaffold(
            capabilities_path=f"{payload.work_dir}/dpabi/dpabi_capabilities.json",
            work_dir=payload.work_dir,
            report_dir=report_dir,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/input-manifest")
def api_dpabi_input_manifest(payload: DpabiPreflightRequest) -> dict[str, Any]:
    try:
        result = build_dpabi_input_manifest(
            dataset_index_path=payload.dataset_index,
            work_dir=payload.work_dir,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/preflight")
def api_dpabi_preflight(payload: DpabiPreflightRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(payload.project_config_path)
        report_dir = project_config.get("runtime", {}).get("report_dir", "./reports")

        result = run_dpabi_preflight(
            work_dir=payload.work_dir,
            report_dir=report_dir,
            capabilities_path=payload.capabilities_path,
            manifest_path=payload.manifest_path,
            wrapper_config_template_path=payload.wrapper_config_template_path,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise_api_error(exc)


@router.get("/api/gpu/detect")
def api_gpu_detect() -> dict[str, Any]:
    return detect_gpu()


@router.post("/api/gpu/benchmark")
def api_gpu_benchmark(payload: GpuBenchmarkRequest) -> dict[str, Any]:
    result = run_alff_subject(
        subject_id=payload.subject_id,
        input_nii=payload.input_nii,
        derivatives_dir=payload.derivatives_dir,
        tr=payload.tr,
        freq_band=payload.freq_band,
        prefer_gpu=payload.prefer_gpu,
        require_gpu=payload.require_gpu,
        benchmark_compare_cpu_gpu=payload.benchmark_compare_cpu_gpu,
    )
    return result


@router.get("/api/pipelines")
def list_pipelines() -> dict[str, Any]:
    examples = Path("examples")
    pipelines = []
    for path in sorted(examples.glob("*.yaml")):
        pipelines.append(str(path))
    for path in sorted(examples.glob("*.yml")):
        pipelines.append(str(path))
    return {
        "ok": True,
        "pipelines": pipelines,
    }


@router.get("/api/pipelines/{pipeline_name}")
def get_pipeline(pipeline_name: str) -> dict[str, Any]:
    try:
        if "/" in pipeline_name or "\\" in pipeline_name or ".." in pipeline_name:
            raise ValueError("Invalid pipeline name.")

        path = Path("examples") / pipeline_name
        if path.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError("Pipeline must be a YAML file.")

        data = read_safe_text_file(path)
        pipeline = load_pipeline_yaml(path)

        return {
            "ok": True,
            "path": data["relative_path"],
            "pipeline": {
                "pipeline_id": pipeline.pipeline_id,
                "version": pipeline.version,
                "modality": pipeline.modality,
                "description": pipeline.description,
                "nodes_total": len(pipeline.nodes),
                "nodes": [
                    {
                        "id": node.id,
                        "name": node.name,
                        "backend": node.backend,
                        "parallel_level": node.parallel_level,
                        "depends_on": node.depends_on,
                    }
                    for node in pipeline.nodes
                ],
            },
            "raw": data["content"],
        }
    except Exception as exc:
        raise_api_error(exc)


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


@router.get("/api/reports/dataset-evaluation")
def get_dataset_evaluation_report() -> dict[str, Any]:
    base = Path("outputs/reports") / "dataset_evaluation"

    return {
        "ok": True,
        "dataset_summary": _read_json_if_exists(base / "dataset_summary.json"),
        "subject_qc_table": _read_text_if_exists(base / "subject_qc_table.csv"),
        "exclusion_recommendations": _read_text_if_exists(base / "exclusion_recommendations.csv"),
        "report_markdown": _read_text_if_exists(base / "dataset_evaluation_report.md"),
        "report_html": _read_text_if_exists(base / "dataset_evaluation_report.html"),
    }


@router.get("/api/files/read")
def read_file(path: str = Query(...)) -> dict[str, Any]:
    try:
        return read_safe_text_file(path)
    except PathSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise_api_error(exc)


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


@router.get("/api/logs/read")
def api_read_log(path: str = Query(...)) -> dict[str, Any]:
    normalized = path.replace("\\", "/")
    if not normalized.startswith("outputs/logs/") and "/logs/" not in normalized:
        raise HTTPException(status_code=403, detail="Only logs/ files can be read here.")

    if not normalized.endswith(".log"):
        raise HTTPException(status_code=403, detail="Only .log files can be read here.")

    try:
        return read_safe_text_file(path)
    except PathSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise_api_error(exc)


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


@router.post("/api/dpabi/run-plan")
def api_dpabi_run_plan(request: DpabiRunPlanRequest) -> dict[str, Any]:
    try:
        result = create_dpabi_run_plan(
            work_dir=request.work_dir,
            report_dir="./reports",
            capabilities_path=request.capabilities_path,
            manifest_path=request.manifest_path,
            preflight_path=request.preflight_path,
            params_path=request.params_path,
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/sandbox-smoke")
def api_dpabi_sandbox_smoke(request: DpabiSandboxSmokeRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = run_dpabi_sandbox_smoke(
            matlab_command=project_config.get("matlab_command", "matlab"),
            dpabi_dir=project_config.get("dpabi_dir", "./third_party/DPABI"),
            work_dir=request.work_dir,
            log_dir=request.log_dir,
            approved=request.approved,
            approved_by=request.approved_by,
            matlab_script_dir="./matlab",
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/subject-smooth")
def api_dpabi_subject_smooth(request: DpabiSubjectSmoothRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = run_dpabi_subject_smooth(
            matlab_command=project_config.get("matlab_command", "matlab"),
            dpabi_dir=project_config.get("dpabi_dir", "./third_party/DPABI"),
            subject_id=request.subject_id,
            input_bold=request.input_bold,
            derivatives_dir=project_config.get("derivatives_dir", "./derivatives"),
            work_dir=request.work_dir,
            log_dir=request.log_dir,
            function_name=request.function_name,
            fwhm=request.fwhm,
            approved=request.approved,
            matlab_script_dir="./matlab",
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/subject-wrapper-report")
def api_dpabi_subject_wrapper_report(request: DpabiSubjectWrapperReportRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = write_dpabi_subject_wrapper_report(
            derivatives_dir=project_config.get("derivatives_dir", "./derivatives"),
            report_dir=project_config.get("runtime", {}).get("report_dir", "./reports"),
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/signature-probe")
def api_dpabi_signature_probe(request: DpabiSignatureProbeRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = run_dpabi_signature_probe(
            matlab_command=project_config.get("matlab_command", "matlab"),
            dpabi_dir=project_config.get("dpabi_dir", "./third_party/DPABI"),
            work_dir=request.work_dir,
            log_dir=request.log_dir,
            matlab_script_dir="./matlab",
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/wrapper-contracts")
def api_dpabi_wrapper_contracts(request: DpabiSignatureProbeRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = write_dpabi_wrapper_contracts(
            signatures_path=f"{request.work_dir}/dpabi/dpabi_function_signatures.json",
            work_dir=request.work_dir,
            report_dir=project_config.get("runtime", {}).get("report_dir", "./reports"),
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/single-function-sandbox")
def api_dpabi_single_function_sandbox(request: DpabiSingleFunctionRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = run_dpabi_single_function_sandbox(
            matlab_command=project_config.get("matlab_command", "matlab"),
            dpabi_dir=project_config.get("dpabi_dir", "./third_party/DPABI"),
            work_dir=request.work_dir,
            log_dir=request.log_dir,
            function_name=request.function_name,
            approved=request.approved,
            approved_by=request.approved_by,
            matlab_script_dir="./matlab",
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/wrapper-validation-matrix")
def api_dpabi_wrapper_validation_matrix(request: DpabiWrapperValidationRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = write_dpabi_wrapper_validation_matrix(
            work_dir=request.work_dir,
            report_dir=project_config.get("runtime", {}).get("report_dir", "./reports"),
            signatures_path=request.signatures_path,
            contracts_path=request.contracts_path,
            sandbox_result_path=request.sandbox_result_path,
            subject_wrapper_summary_path=request.subject_wrapper_summary_path,
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/template-library")
def api_dpabi_template_library(request: DpabiWrapperValidationRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        result = write_dpabi_template_library(
            work_dir=request.work_dir,
            report_dir=project_config.get("runtime", {}).get("report_dir", "./reports"),
            matrix_path=request.signatures_path.replace("dpabi_function_signatures.json", "dpabi_wrapper_compatibility_matrix.json"),
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.get("/api/dpabi/templates")
def api_dpabi_list_templates(work_dir: str = "./work") -> dict[str, Any]:
    try:
        result = list_dpabi_templates(work_dir=work_dir)
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/template-instantiate")
def api_dpabi_template_instantiate(request: DpabiTemplateInstantiateRequest) -> dict[str, Any]:
    try:
        result = instantiate_dpabi_template(
            template_id=request.template_id,
            instance_id=request.instance_id,
            run_id=request.run_id,
            function_name=request.function_name,
            fwhm=request.fwhm,
            subjects=request.subjects,
            work_dir=request.work_dir,
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/dpabi/template-execute")
def api_dpabi_template_execute(request: DpabiTemplateExecuteRequest) -> dict[str, Any]:
    try:
        result = execute_dpabi_template_instance(
            instance_id=request.instance_id,
            project_config_path=request.project_config_path,
            approved=request.approved,
            approved_by=request.approved_by,
            work_dir=request.work_dir,
        )
        return result
    except Exception as exc:
        raise_api_error(exc)


@router.get("/api/dpabi/template-wizard/options")
def api_dpabi_template_wizard_options() -> dict[str, Any]:
    result = get_dpabi_template_wizard_options("./work")
    if not result.get("ok"):
        return result
    return result


@router.post("/api/dpabi/template-wizard/preview")
def api_dpabi_template_wizard_preview(
    request: DpabiTemplateWizardRequest,
) -> dict[str, Any]:
    result = preview_dpabi_template_instance(
        payload=request.model_dump(),
        work_dir="./work",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/dpabi/template-wizard/create")
def api_dpabi_template_wizard_create(
    request: DpabiTemplateWizardRequest,
) -> dict[str, Any]:
    result = create_dpabi_template_instance_from_wizard(
        payload=request.model_dump(),
        work_dir="./work",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/dpabi/template-wizard/latest")
def api_dpabi_template_wizard_latest() -> dict[str, Any]:
    base = Path("outputs/work") / "dpabi" / "template_wizard"

    return {
        "ok": True,
        "latest_preview": _read_json_if_exists(base / "latest_preview.json"),
        "latest_preview_markdown": _read_text_if_exists(base / "latest_preview.md"),
    }


@router.get("/api/experiments/run-index")
def api_experiments_run_index() -> dict[str, Any]:
    from src.backend.app.tools.experiment_tracker import build_run_index

    result = build_run_index("./work", "./reports")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/experiments/record")
def api_experiments_create_record(
    request: ExperimentTrackingRequest,
) -> dict[str, Any]:
    from src.backend.app.tools.experiment_tracker import create_experiment_record

    result = create_experiment_record(
        experiment_id=request.experiment_id,
        name=request.name,
        run_ids=request.run_ids,
        tags=request.tags,
        notes=request.notes,
        work_dir="./work",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/experiments/compare")
def api_experiments_compare(
    request: ExperimentCompareRequest,
) -> dict[str, Any]:
    from src.backend.app.tools.experiment_tracker import compare_experiment_runs

    result = compare_experiment_runs(
        experiment_id=request.experiment_id,
        run_ids=request.run_ids,
        work_dir="./work",
        report_dir="./reports",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/experiments/record/{experiment_id}")
def api_experiments_get_record(experiment_id: str) -> dict[str, Any]:
    path = Path("outputs/work") / "experiments" / "records" / f"{experiment_id}.json"
    data = _read_json_if_exists(path)
    if data is None:
        raise HTTPException(status_code=404, detail="Experiment record not found")
    return {"ok": True, "record": data}


@router.get("/api/experiments/comparison/{experiment_id}")
def api_experiments_get_comparison(experiment_id: str) -> dict[str, Any]:
    json_path = Path("outputs/reports") / "experiments" / f"{experiment_id}_comparison.json"
    md_path = Path("outputs/reports") / "experiments" / f"{experiment_id}_comparison_report.md"

    data = _read_json_if_exists(json_path)
    markdown = _read_text_if_exists(md_path)

    if data is None:
        raise HTTPException(status_code=404, detail="Comparison not found")

    return {
        "ok": True,
        "comparison": data,
        "markdown": markdown,
    }


@router.get("/api/experiments/dashboard")
def api_get_experiment_dashboard() -> dict[str, Any]:
    from src.backend.app.tools.experiment_dashboard import build_experiment_dashboard

    base = Path("outputs/work") / "experiments"
    report_base = Path("outputs/reports") / "experiments"

    dashboard = _read_json_if_exists(base / "dashboard_data.json")
    dashboard_csv = _read_text_if_exists(base / "dashboard_data.csv")
    dashboard_report = _read_text_if_exists(report_base / "dashboard_report.md")

    if dashboard is None:
        dashboard = build_experiment_dashboard(
            work_dir="./work",
            report_dir="./reports",
            refresh_index=True,
        )

    return {
        "ok": True,
        "dashboard": dashboard,
        "dashboard_csv": dashboard_csv,
        "dashboard_report": dashboard_report,
    }


@router.post("/api/experiments/dashboard/refresh")
def api_refresh_experiment_dashboard() -> dict[str, Any]:
    from src.backend.app.tools.experiment_dashboard import build_experiment_dashboard

    result = build_experiment_dashboard(
        work_dir="./work",
        report_dir="./reports",
        refresh_index=True,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/api/artifacts")
def api_get_artifacts() -> dict[str, Any]:
    from src.backend.app.tools.artifact_browser import build_artifact_index

    index_path = Path("outputs/work") / "artifacts" / "artifact_index.json"

    index = _read_json_if_exists(index_path)
    if index is None:
        index = build_artifact_index()

    return {
        "ok": True,
        "index": index,
        "markdown": _read_text_if_exists(
            Path("outputs/reports") / "artifacts" / "artifact_index.md"
        ),
    }


@router.get("/api/artifacts/preview")
def api_get_artifact_preview(path: str = Query(...), max_lines: int = Query(80)) -> dict[str, Any]:
    from src.backend.app.tools.artifact_browser import preview_artifact

    result = preview_artifact(path=path, max_lines=max_lines)

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/api/insights")
def api_get_insights() -> dict[str, Any]:
    from src.backend.app.tools.artifact_browser import build_artifact_index
    from src.backend.app.tools.insights import generate_insights_from_index

    base = Path("outputs/reports") / "insights"
    insights_json = _read_json_if_exists(base / "insights_summary.json")
    insights_md = _read_text_if_exists(base / "insights_report.md")

    # Always regenerate for freshness
    index_path = Path("outputs/work") / "artifacts" / "artifact_index.json"
    index = _read_json_if_exists(index_path)
    if index is None:
        index = build_artifact_index()

    insights = generate_insights_from_index(
        artifact_index=index,
        report_dir="./reports",
    )

    return {
        "ok": True,
        "insights": insights,
        "insights_json": insights_json,
        "insights_md": insights_md,
    }


@router.get("/api/deployment/profile")
def api_get_deployment_profile() -> dict[str, Any]:
    from src.backend.app.tools.deployment_profile import build_deployment_profile

    result = build_deployment_profile()
    return result


# ── rs-fMRI chain validation ──────────────────────────────────────────────

@router.post("/api/rsfmri/spm-chain-validate")
def api_spm_chain_validate() -> dict[str, Any]:
    from src.backend.app.tools.spm_chain_validator import validate_spm_chain_contracts

    result = validate_spm_chain_contracts()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/rsfmri/chain-report")
def api_rsfmri_chain_report() -> dict[str, Any]:
    from src.backend.app.tools.rsfmri_chain_report import build_rsfmri_chain_report

    result = build_rsfmri_chain_report("./work", "./reports")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/rsfmri/chain-report/latest")
def api_rsfmri_chain_report_latest() -> dict[str, Any]:
    path = Path("outputs/reports") / "rsfmri" / "rsfmri_chain_report.md"
    content = _read_text_if_exists(path)
    if content is None:
        raise HTTPException(status_code=404, detail="No chain report found. POST /api/rsfmri/chain-report first.")
    return {"ok": True, "report": content}


# ── rs-fMRI preprocessing plan ────────────────────────────────────────────

@router.post("/api/rsfmri/preprocessing-plan")
def api_rsfmri_preprocessing_plan(work_dir: str = "./work") -> dict[str, Any]:
    from src.backend.app.tools.rsfmri_plan_tool import write_rsfmri_preprocessing_plan

    result = write_rsfmri_preprocessing_plan(work_dir=work_dir, report_dir="./reports")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/rsfmri/preprocessing-plan/latest")
def api_rsfmri_preprocessing_plan_latest() -> dict[str, Any]:
    path = Path("outputs/reports") / "rsfmri" / "rsfmri_preprocessing_plan.md"
    content = _read_text_if_exists(path)
    if content is None:
        raise HTTPException(status_code=404, detail="No plan found.")
    return {"ok": True, "plan": content}


# ── rs-fMRI SPM pipeline endpoints ────────────────────────────────────────

@router.post("/api/rsfmri/spm/realign-motion-qc")
def api_rsfmri_spm_realign_motion_qc(payload: RsfmriSpmRealignMotionQcRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/spm/slice-timing")
def api_rsfmri_spm_slice_timing(payload: RsfmriSpmSliceTimingRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/st/realign-motion-qc")
def api_rsfmri_st_realign_motion_qc(payload: RsfmriStRealignMotionQcRequest) -> dict[str, Any]:
    import yaml, copy
    from pathlib import Path

    project_config = _load_project_config(payload.project_config_path)
    pipeline = load_pipeline_yaml(payload.pipeline_path)

    # Inject approved=true into the SPM realign node for chain execution
    approved_pipeline_path = None
    if payload.approved:
        for node in pipeline.nodes:
            if node.id == "spm_realign_subject":
                node.params["approved"] = True

        # Write a temporary pipeline YAML with approved set
        approved_pipeline_path = Path(payload.pipeline_path).with_suffix(".approved.yaml")
        pipeline_data = yaml.safe_load(Path(payload.pipeline_path).read_text(encoding="utf-8")) or {}
        for node in pipeline_data.get("nodes", []):
            if node.get("id") == "spm_realign_subject":
                node.setdefault("params", {})
                node["params"]["approved"] = True
        approved_pipeline_path.write_text(yaml.safe_dump(pipeline_data, sort_keys=False), encoding="utf-8")

    pipeline_to_run = str(approved_pipeline_path) if approved_pipeline_path else payload.pipeline_path
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=pipeline_to_run,
    )

    if approved_pipeline_path and approved_pipeline_path.exists():
        try:
            approved_pipeline_path.unlink()
        except OSError:
            pass

    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/coregistration-qc")
def api_rsfmri_coregistration_qc(payload: RsfmriCoregistrationQcRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/segmentation-tissue-qc")
def api_rsfmri_segmentation_tissue_qc(payload: RsfmriSegmentationTissueQcRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/normalization-qc")
def api_rsfmri_normalization_qc(payload: RsfmriNormalizationQcRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/smoothing-qc")
def api_rsfmri_smoothing_qc(payload: RsfmriSmoothingQcRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/nuisance-regression")
def api_rsfmri_nuisance_regression(payload: RsfmriNuisanceRegressionRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/temporal-filtering")
def api_rsfmri_temporal_filtering(payload: RsfmriTemporalFilteringRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/alff-falff")
def api_rsfmri_alff_falff(payload: RsfmriAlffFalffRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/reho")
def api_rsfmri_reho(payload: RsfmriRehoRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/functional-connectivity")
def api_rsfmri_functional_connectivity(payload: RsfmriFunctionalConnectivityRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/group-summary")
def api_rsfmri_group_summary(payload: RsfmriGroupSummaryRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/report-export")
def api_rsfmri_report_export(payload: RsfmriReportExportRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/rsfmri/report-validation")
def api_rsfmri_report_validation(payload: RsfmriReportValidationRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


@router.post("/api/release-readiness")
def api_release_readiness(payload: ReleaseReadinessRequest) -> dict[str, Any]:
    result = run_pipeline(
        project_config_path=payload.project_config_path,
        pipeline_path=payload.pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


# ── Report export / validation listing endpoints ──────────────────────────

@router.get("/api/rsfmri/report-exports")
def api_rsfmri_list_report_exports() -> dict[str, Any]:
    export_map = list_rsfmri_report_exports("./exports")
    return {"ok": True, "exports": export_map}


@router.get("/api/rsfmri/report-exports/latest")
def api_rsfmri_get_latest_report_export() -> dict[str, Any]:
    result = get_latest_rsfmri_report_export("./exports")
    if result is None:
        raise HTTPException(status_code=404, detail="No report exports found")
    return {"ok": True, **result}


@router.get("/api/rsfmri/report-validations")
def api_rsfmri_list_report_validations() -> dict[str, Any]:
    validation_map = list_rsfmri_report_validations("./exports")
    return {"ok": True, "validations": validation_map}


@router.get("/api/rsfmri/report-validations/latest")
def api_rsfmri_get_latest_report_validation() -> dict[str, Any]:
    result = get_latest_rsfmri_report_validation("./exports")
    if result is None:
        raise HTTPException(status_code=404, detail="No report validations found")
    return {"ok": True, **result}


# ── Reproducibility bundle ────────────────────────────────────────────────

@router.post("/api/bundle/create")
def api_bundle_create(request: BundleCreateRequest) -> dict[str, Any]:
    from src.backend.app.tools.reproducibility_bundle import create_bundle

    result = create_bundle(
        bundle_id=request.bundle_id,
        include_logs=request.include_logs,
        include_reports=request.include_reports,
        include_artifact_index=request.include_artifact_index,
        max_file_size_bytes=request.max_file_size_bytes,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/bundle/preview")
def api_bundle_preview() -> dict[str, Any]:
    from src.backend.app.tools.reproducibility_bundle import preview_bundle

    result = preview_bundle("./work")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/bundle/download-info")
def api_bundle_download_info() -> dict[str, Any]:
    bundle_dir = Path("outputs/exports") / "bundles"
    bundles = []
    for path in sorted(bundle_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        bundles.append({
            "name": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "created": path.stat().st_mtime,
        })

    return {
        "ok": True,
        "total": len(bundles),
        "bundles": bundles,
    }


# ── Docs inventory ────────────────────────────────────────────────────────

@router.get("/api/docs/inventory")
def api_docs_inventory() -> dict[str, Any]:
    from src.backend.app.tools.docs_inventory import build_docs_inventory

    result = build_docs_inventory()
    return result


# ── Advisor endpoints ─────────────────────────────────────────────────────

@router.post("/api/advisor/protocol")
def api_advisor_protocol(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("protocol", request)


@router.post("/api/advisor/error")
def api_advisor_error(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("error", request)


@router.post("/api/advisor/qc-report")
def api_advisor_qc_report(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("qc-report", request)


@router.post("/api/advisor/parameters")
def api_advisor_parameters(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("parameters", request)


@router.post("/api/advisor/docs-qa")
def api_advisor_docs_qa(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("docs-qa", request)


# ── Error KB endpoints ────────────────────────────────────────────────────

@router.get("/api/kb/errors")
def api_kb_errors() -> dict[str, Any]:
    from src.backend.app.tools.error_kb_validator import list_error_kb_entries

    return list_error_kb_entries()


@router.post("/api/kb/errors/validate")
def api_kb_errors_validate() -> dict[str, Any]:
    from src.backend.app.tools.error_kb_validator import validate_error_kb

    return validate_error_kb()


# ── SessionDB endpoints ───────────────────────────────────────────────────

@router.post("/api/sessions/index")
async def sessions_index():
    """Index all existing run histories into SessionDB."""
    from src.backend.app.tools.session_indexer import index_pipeline_runs, index_demo_runs

    pipe_result = index_pipeline_runs()
    demo_result = index_demo_runs()
    return {
        "ok": True,
        "pipeline_runs": pipe_result,
        "demo_runs": demo_result,
    }


@router.get("/api/sessions/query")
async def sessions_query(
    q: str | None = Query(None),
    status: str | None = Query(None),
    subject_id: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
):
    """Query SessionDB with optional filters or FTS search."""
    from src.backend.app.tools.session_query import query_sessions

    return query_sessions(q=q, status=status, subject_id=subject_id,
                          category=category, limit=limit, offset=offset)


@router.get("/api/sessions/runs")
async def sessions_runs(status: str | None = None, limit: int = 50):
    """List runs from SessionDB."""
    from src.backend.app.memory.session_db import SessionDB

    db = SessionDB()
    runs = db.query_runs(status=status, limit=limit)
    db.close()
    return {"ok": True, "runs": runs, "total": len(runs)}


@router.get("/api/sessions/nodes")
async def sessions_nodes(run_id: str = Query(...)):
    """List nodes for a run from SessionDB."""
    from src.backend.app.memory.session_db import SessionDB

    db = SessionDB()
    nodes = db.query_nodes(run_id=run_id)
    db.close()
    return {"ok": True, "nodes": nodes, "total": len(nodes)}


@router.get("/api/sessions/search")
async def sessions_search(q: str = Query(...), limit: int = 30):
    """Full-text search across indexed documents."""
    from src.backend.app.memory.session_db import SessionDB

    db = SessionDB()
    results = db.fts_search(query=q, limit=limit)
    db.close()
    return {"ok": True, "results": results, "total": len(results)}


# ── Run history endpoints ─────────────────────────────────────────────────

@router.get("/api/history/runs")
def api_history_runs(limit: int = Query(20)) -> dict[str, Any]:
    from src.backend.app.tools.run_history_cli import get_recent_run_history

    return {"ok": True, "runs": get_recent_run_history(limit)}


# ── DPABI template library endpoints ──────────────────────────────────────

@router.get("/api/dpabi/template-library")
async def dpabi_template_library_view():
    """View the DPABI template library report."""
    path = Path("outputs/reports") / "dpabi" / "dpabi_template_library.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template library not found. POST /api/dpabi/template-library to generate.")
    return {"ok": True, "report": path.read_text(encoding="utf-8")}


# ── DPABI smoke test / validation endpoints ───────────────────────────────

@router.post("/api/dpabi/smoke-test")
async def dpabi_smoke_test(request: dict[str, Any]):
    """Run DPABI environment smoke test."""
    from src.backend.app.tools.dpabi_wrapper import run_dpabi_smoke_test

    return run_dpabi_smoke_test(
        dpabi_dir=request.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
        matlab_command=request.get("matlab_command", "matlab"),
        work_dir=request.get("work_dir", "./work"),
        log_dir=request.get("log_dir", "./logs"),
        approved=request.get("approved", False),
    )


@router.post("/api/dpabi/run-single-function")
async def dpabi_run_single_function(request: dict[str, Any]):
    """Run a single DPABI function."""
    from src.backend.app.tools.dpabi_wrapper import run_dpabi_single_function

    return run_dpabi_single_function(
        function_name=request.get("function_name", "y_Smooth"),
        input_bold=request.get("input_bold", ""),
        subject_id=request.get("subject_id", "sub-001"),
        derivatives_dir=request.get("derivatives_dir", "./derivatives"),
        work_dir=request.get("work_dir", "./work"),
        log_dir=request.get("log_dir", "./logs"),
        dpabi_dir=request.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
        matlab_command=request.get("matlab_command", "matlab"),
        mode=request.get("mode", "contract_only"),
        approved=request.get("approved", False),
        params=request.get("params"),
    )


@router.get("/api/dpabi/function-list")
async def dpabi_function_list():
    """List allowed DPABI functions."""
    from src.backend.app.tools.dpabi_safety import list_allowed_functions

    return {"ok": True, "functions": list_allowed_functions()}


# ── GPU endpoints ─────────────────────────────────────────────────────────

@router.get("/api/gpu/capability")
async def gpu_capability():
    """Detect GPU capability (CuPy, PyTorch CUDA, device info)."""
    from src.backend.app.tools.gpu_capability import detect_gpu_capability

    return detect_gpu_capability()


@router.post("/api/gpu/synthetic-benchmark")
async def gpu_synthetic_benchmark(request: dict[str, Any]):
    """Run CPU vs GPU benchmark for ALFF computation."""
    from src.backend.app.tools.alff_compute import compute_alff_backend, compute_alff_numpy
    import numpy as np
    import time

    shape = tuple(request.get("shape", [32, 32, 32, 128]))
    filter_type = request.get("filter_type", "bandpass")
    low_hz = float(request.get("low_hz", 0.01))
    high_hz = float(request.get("high_hz", 0.08))
    tr = float(request.get("tr", 2.0))

    data = np.random.default_rng(42).normal(size=shape).astype(np.float32)

    t0 = time.time()
    _cpu = compute_alff_numpy(data, low_hz=low_hz, high_hz=high_hz, tr=tr)
    cpu_time = round(time.time() - t0, 3)

    gpu_time = None
    gpu_error = None
    try:
        t0 = time.time()
        _gpu = compute_alff_backend(data, low_hz=low_hz, high_hz=high_hz, tr=tr, prefer_gpu=True)
        gpu_time = round(time.time() - t0, 3)
    except Exception as exc:
        gpu_error = str(exc)

    return {
        "ok": True,
        "shape": list(shape),
        "cpu_time_s": cpu_time,
        "gpu_time_s": gpu_time,
        "gpu_error": gpu_error,
        "speedup": round(cpu_time / gpu_time, 2) if gpu_time else None,
    }


# ── Real data sandbox ─────────────────────────────────────────────────────

@router.post("/api/real-data/inspect")
async def real_data_inspect(request: dict[str, Any]):
    """Inspect a real dataset directory and generate data inventory."""
    from src.backend.app.tools.real_data_inspector import inspect_real_data_directory

    return inspect_real_data_directory(
        root_dir=request.get("root_dir", "./data/DemoData"),
        work_dir=request.get("work_dir", "./work"),
        report_dir=request.get("report_dir", "outputs/reports"),
        max_subjects=int(request.get("max_subjects", 500)),
    )


@router.get("/api/real-data/inventory/latest")
async def real_data_inventory_latest():
    """Get latest data inventory."""
    path = Path("outputs/reports") / "real_data_sandbox" / "data_inventory.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No inventory found. POST /api/real-data/inspect first.")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/api/real-data/risk-report")
async def real_data_risk_report():
    """Generate risk report from latest data inventory."""
    from src.backend.app.tools.real_data_risk_reporter import build_risk_report

    return build_risk_report(
        inventory_path="outputs/reports/real_data_sandbox/data_inventory.json",
        output_dir="outputs/reports/real_data_sandbox",
    )


@router.get("/api/real-data/risk-report/latest")
async def real_data_risk_report_latest():
    """Get latest risk report."""
    path = Path("outputs/reports/real_data_sandbox/risk_report.json")
    if not path.exists():
        raise HTTPException(status_code=404, detail="No risk report found. POST /api/real-data/risk-report first.")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/api/real-data/protocol-recommend")
async def real_data_protocol_recommend():
    """Generate protocol recommendation from latest data inventory."""
    from src.backend.app.tools.real_data_protocol_advisor import recommend_protocol_from_inventory

    return recommend_protocol_from_inventory(
        inventory_path="outputs/reports/real_data_sandbox/data_inventory.json",
        output_dir="outputs/reports/real_data_sandbox",
    )


@router.get("/api/sandbox/status")
async def sandbox_status():
    """Get sandbox mode status."""
    import os
    return {
        "ok": True,
        "mode": os.environ.get("MEDIMAGE_REAL_DATA_MODE", "readonly_sandbox"),
        "rawdata_readonly": True,
        "preprocessing_enabled": False,
        "auto_upload_enabled": False,
    }


@router.post("/api/workflow/run")
async def workflow_run(request: dict[str, Any]):
    """Run quickstart demo or real-data mini pipeline.

    Delegates heavy computation to workflow_runner module.
    """
    from src.backend.app.tools.workflow_runner import (
        run_quickstart_demo_workflow,
        run_real_data_workflow,
    )

    data_source = request.get("data_source", "demo")
    dataset_path = request.get("dataset_path", "")

    if data_source == "demo" or not dataset_path or "synthetic" in str(dataset_path).lower():
        return run_quickstart_demo_workflow()

    return run_real_data_workflow(dataset_path)


@router.get("/api/deployment/profile")
def api_get_deployment_profile() -> dict[str, Any]:
    from src.backend.app.tools.deployment_profile import build_deployment_profile

    result = build_deployment_profile()
    return result
