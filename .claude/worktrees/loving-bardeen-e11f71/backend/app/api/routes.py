from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.api.models import (
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
from backend.app.runtime.pipeline_executor import run_pipeline
from backend.app.tools.report_exporter import get_latest_rsfmri_report_export, list_rsfmri_report_exports
from backend.app.tools.report_package_validator import get_latest_rsfmri_report_validation, list_rsfmri_report_validations
from backend.app.runtime.agent_runtime import (
    run_orchestrator_execute,
    run_orchestrator_plan,
)
from backend.app.runtime.path_safety import PathSafetyError, read_safe_text_file
from backend.app.runtime.run_inspector import (
    inspect_run,
    list_available_runs,
    read_state_detail,
)
from backend.app.runtime.error_diagnoser import diagnose_run
from backend.app.runtime.retry_runtime import (
    dry_run_retry_plan,
    execute_retry_plan,
)
from backend.app.runtime.scheduler import create_scheduler_plan
from backend.app.schemas.pipeline_schema import load_pipeline_yaml
from backend.app.tools.gpu_utils import detect_gpu
from backend.app.tools.gpu_alff_runner import run_alff_subject
from backend.app.tools.dpabi_runner import run_dpabi_capability_inspection
from backend.app.tools.dpabi_config import write_dpabi_wrapper_scaffold
from backend.app.tools.dpabi_adapter import build_dpabi_input_manifest
from backend.app.tools.dpabi_preflight import run_dpabi_preflight
from backend.app.tools.dpabi_run_plan import create_dpabi_run_plan
from backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke
from backend.app.tools.dpabi_signature_runner import run_dpabi_signature_probe
from backend.app.tools.dpabi_contract_registry import write_dpabi_wrapper_contracts
from backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox
from backend.app.tools.dpabi_subject_wrapper import run_dpabi_subject_smooth
from backend.app.tools.dpabi_subject_wrapper_report import write_dpabi_subject_wrapper_report
from backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix
from backend.app.tools.dpabi_template_library import write_dpabi_template_library
from backend.app.tools.dpabi_template_instantiator import (
    instantiate_dpabi_template,
    execute_dpabi_template_instance,
    list_dpabi_templates,
)
from backend.app.tools.dpabi_template_wizard import (
    get_dpabi_template_wizard_options,
    preview_dpabi_template_instance,
    create_dpabi_template_instance_from_wizard,
)
from backend.app.tools.rsfmri_plan_tool import write_rsfmri_preprocessing_plan

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
        raise HTTPException(status_code=400, detail=str(exc))


def _load_project_config(path: str) -> dict[str, Any]:
    import yaml
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"Project config not found: {path}")
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse project config: {exc}")


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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

    plan_path = Path("work") / "agent_runs" / request.agent_run_id / "plan.json"

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

    base = Path("work") / "agent_runs" / agent_run_id

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
    base = Path("reports") / "dataset_evaluation"

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
        raise HTTPException(status_code=400, detail=str(exc))


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
    if not normalized.startswith("logs/") and "/logs/" not in normalized:
        raise HTTPException(status_code=403, detail="Only logs/ files can be read here.")

    if not normalized.endswith(".log"):
        raise HTTPException(status_code=403, detail="Only .log files can be read here.")

    try:
        return read_safe_text_file(path)
    except PathSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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

    base = Path("work") / "retry_runs" / retry_run_id

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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/dpabi/templates")
def api_dpabi_list_templates(work_dir: str = "./work") -> dict[str, Any]:
    try:
        result = list_dpabi_templates(work_dir=work_dir)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
        raise HTTPException(status_code=400, detail=str(exc))


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
    base = Path("work") / "dpabi" / "template_wizard"

    return {
        "ok": True,
        "latest_preview": _read_json_if_exists(base / "latest_preview.json"),
        "latest_preview_markdown": _read_text_if_exists(base / "latest_preview.md"),
    }


@router.get("/api/experiments/run-index")
def api_experiments_run_index() -> dict[str, Any]:
    from backend.app.tools.experiment_tracker import build_run_index

    result = build_run_index("./work", "./reports")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/experiments/record")
def api_experiments_create_record(
    request: ExperimentTrackingRequest,
) -> dict[str, Any]:
    from backend.app.tools.experiment_tracker import create_experiment_record

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
    from backend.app.tools.experiment_tracker import compare_experiment_runs

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
    path = Path("work") / "experiments" / "records" / f"{experiment_id}.json"
    data = _read_json_if_exists(path)
    if data is None:
        raise HTTPException(status_code=404, detail="Experiment record not found")
    return {"ok": True, "record": data}


@router.get("/api/experiments/comparison/{experiment_id}")
def api_experiments_get_comparison(experiment_id: str) -> dict[str, Any]:
    json_path = Path("reports") / "experiments" / f"{experiment_id}_comparison.json"
    md_path = Path("reports") / "experiments" / f"{experiment_id}_comparison_report.md"

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
    from backend.app.tools.experiment_dashboard import build_experiment_dashboard

    base = Path("work") / "experiments"
    report_base = Path("reports") / "experiments"

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
    from backend.app.tools.experiment_dashboard import build_experiment_dashboard

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
    from backend.app.tools.artifact_browser import build_artifact_index

    index_path = Path("work") / "artifacts" / "artifact_index.json"

    index = _read_json_if_exists(index_path)
    if index is None:
        index = build_artifact_index()

    return {
        "ok": True,
        "index": index,
    }


@router.post("/api/artifacts/refresh")
def api_refresh_artifacts() -> dict[str, Any]:
    from backend.app.tools.artifact_browser import build_artifact_index

    result = build_artifact_index()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/artifacts/preview")
def api_preview_artifact(request: ArtifactPreviewRequest) -> dict[str, Any]:
    from backend.app.tools.artifact_browser import preview_artifact

    result = preview_artifact(request.path)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/bundles")
def api_list_bundles() -> dict[str, Any]:
    from backend.app.tools.reproducibility_bundle import list_reproducibility_bundles

    return list_reproducibility_bundles()


@router.post("/api/bundles/create")
def api_create_bundle(request: BundleCreateRequest) -> dict[str, Any]:
    from backend.app.tools.reproducibility_bundle import create_reproducibility_bundle

    result = create_reproducibility_bundle(
        bundle_id=request.bundle_id,
        include_logs=request.include_logs,
        include_reports=request.include_reports,
        include_artifact_index=request.include_artifact_index,
        max_file_size_bytes=request.max_file_size_bytes,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/api/bundles/{bundle_id}")
def api_inspect_bundle(bundle_id: str) -> dict[str, Any]:
    from backend.app.tools.reproducibility_bundle import inspect_reproducibility_bundle

    result = inspect_reproducibility_bundle(bundle_id)

    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result)

    return result


@router.get("/api/release/readiness")
def api_get_release_readiness() -> dict[str, Any]:
    from backend.app.tools.release_readiness import build_release_readiness

    result = build_release_readiness()
    return result


@router.get("/api/rsfmri/preprocessing-plan")
def api_get_rsfmri_preprocessing_plan() -> dict[str, Any]:
    work_base = Path("work") / "preprocessing" / "rsfmri"
    report_base = Path("reports") / "rsfmri"

    plan = _read_json_if_exists(work_base / "rsfmri_preprocessing_plan.json")
    report = _read_text_if_exists(report_base / "rsfmri_preprocessing_plan_report.md")

    if plan is None:
        plan = write_rsfmri_preprocessing_plan(
            work_dir="./work",
            report_dir="./reports",
        )

    return {
        "ok": True,
        "plan": plan,
        "report": report,
    }


@router.post("/api/rsfmri/preprocessing-plan/refresh")
def api_refresh_rsfmri_preprocessing_plan() -> dict[str, Any]:
    result = write_rsfmri_preprocessing_plan(
        work_dir="./work",
        report_dir="./reports",
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


def _make_spm_realign_motion_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") == "spm_realign_subject":
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@router.post("/api/rsfmri/spm-realign-motion-qc/run")
def api_run_rsfmri_spm_realign_motion_qc(
    request: RsfmriSpmRealignMotionQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM realignment requires approved=true.",
        )

    try:
        approved_pipeline = _make_spm_realign_motion_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_spm_realign_motion_qc.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/spm-realign-motion-qc")
def api_get_rsfmri_spm_realign_motion_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/motion_qc.json")):
        subject_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "motion_qc_summary": _read_json_if_exists(report_base / "motion_qc_summary.json"),
        "motion_qc_report": _read_text_if_exists(report_base / "motion_qc_report.md"),
        "subject_motion_qc": subject_qc,
    }


def _make_spm_slice_timing_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") == "spm_slice_timing_subject":
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@router.post("/api/rsfmri/spm-slice-timing/run")
def api_run_rsfmri_spm_slice_timing(
    request: RsfmriSpmSliceTimingRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM slice timing requires approved=true.",
        )

    try:
        approved_pipeline = _make_spm_slice_timing_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_spm_slice_timing.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/spm-slice-timing")
def api_get_rsfmri_spm_slice_timing() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/slice_timing_qc.json")):
        subject_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "slice_timing_qc_summary": _read_json_if_exists(report_base / "slice_timing_qc_summary.json"),
        "slice_timing_qc_report": _read_text_if_exists(report_base / "slice_timing_qc_report.md"),
        "subject_slice_timing_qc": subject_qc,
    }


def _make_st_realign_motion_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {"spm_slice_timing_subject", "spm_realign_subject"}:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@router.post("/api/rsfmri/st-realign-motion-qc/run")
def api_run_rsfmri_st_realign_motion_qc(
    request: RsfmriStRealignMotionQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="Slice Timing → Realignment → Motion QC chain requires approved=true.",
        )

    try:
        approved_pipeline = _make_st_realign_motion_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_st_realign_motion_qc.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/st-realign-motion-qc")
def api_get_rsfmri_st_realign_motion_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_slice_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/slice_timing_qc.json")):
        subject_slice_qc.append(_read_json_if_exists(path))

    subject_motion_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/motion_qc.json")):
        subject_motion_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "chain_summary": _read_json_if_exists(report_base / "st_realign_motion_chain_summary.json"),
        "chain_report": _read_text_if_exists(report_base / "st_realign_motion_chain_report.md"),
        "slice_timing_qc_summary": _read_json_if_exists(report_base / "slice_timing_qc_summary.json"),
        "motion_qc_summary": _read_json_if_exists(report_base / "motion_qc_summary.json"),
        "subject_slice_timing_qc": subject_slice_qc,
        "subject_motion_qc": subject_motion_qc,
    }


def _make_coregistration_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@router.post("/api/rsfmri/coregistration-qc/run")
def api_run_rsfmri_coregistration_qc(
    request: RsfmriCoregistrationQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM coregistration QC pipeline requires approved=true.",
        )

    try:
        approved_pipeline = _make_coregistration_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_coregistration_qc.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/coregistration-qc")
def api_get_rsfmri_coregistration_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_registration_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/registration_qc.json")):
        subject_registration_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "registration_qc_summary": _read_json_if_exists(report_base / "registration_qc_summary.json"),
        "registration_qc_report": _read_text_if_exists(report_base / "registration_qc_report.md"),
        "subject_registration_qc": subject_registration_qc,
    }


def _make_segmentation_tissue_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
            "spm_segment_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@router.post("/api/rsfmri/segmentation-tissue-qc/run")
def api_run_rsfmri_segmentation_tissue_qc(
    request: RsfmriSegmentationTissueQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM segmentation tissue QC pipeline requires approved=true.",
        )

    try:
        approved_pipeline = _make_segmentation_tissue_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_segmentation_tissue_qc.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/segmentation-tissue-qc")
def api_get_rsfmri_segmentation_tissue_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_tissue_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/tissue_qc.json")):
        subject_tissue_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "tissue_qc_summary": _read_json_if_exists(report_base / "tissue_qc_summary.json"),
        "tissue_qc_report": _read_text_if_exists(report_base / "tissue_qc_report.md"),
        "subject_tissue_qc": subject_tissue_qc,
    }


def _make_normalization_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
            "spm_segment_subject",
            "spm_normalize_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@router.post("/api/rsfmri/normalization-qc/run")
def api_run_rsfmri_normalization_qc(
    request: RsfmriNormalizationQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM normalization QC pipeline requires approved=true.",
        )

    try:
        approved_pipeline = _make_normalization_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_normalization_qc.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/normalization-qc")
def api_get_rsfmri_normalization_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_normalization_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/normalization_qc.json")):
        subject_normalization_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "normalization_qc_summary": _read_json_if_exists(report_base / "normalization_qc_summary.json"),
        "normalization_qc_report": _read_text_if_exists(report_base / "normalization_qc_report.md"),
        "subject_normalization_qc": subject_normalization_qc,
    }


def _make_smoothing_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    for node in data.get("nodes", []):
        if node.get("id") in {"spm_slice_timing_subject", "spm_realign_subject", "spm_coregister_subject", "spm_segment_subject", "spm_normalize_subject", "spm_smooth_subject"}:
            node.setdefault("params", {}); node["params"]["approved"] = True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@router.post("/api/rsfmri/smoothing-qc/run")
def api_run_rsfmri_smoothing_qc(request: RsfmriSmoothingQcRequest) -> dict[str, Any]:
    if not request.approved: raise HTTPException(status_code=403, detail="SPM smoothing QC pipeline requires approved=true.")
    try:
        approved_pipeline = _make_smoothing_qc_approved_copy(source=Path(request.pipeline_path), target=Path("work/rsfmri/approved_pipeline_smoothing_qc.yaml"))
        summary = run_pipeline(request.project_config_path, str(approved_pipeline))
        if summary.get("status") not in {"SUCCESS", "PARTIAL"}: raise HTTPException(status_code=400, detail=summary)
        return summary
    except HTTPException: raise
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/smoothing-qc")
def api_get_rsfmri_smoothing_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")
    subject_smoothing_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/smoothing_qc.json")):
        subject_smoothing_qc.append(_read_json_if_exists(path))
    return {"ok": True, "smoothing_qc_summary": _read_json_if_exists(report_base / "smoothing_qc_summary.json"), "smoothing_qc_report": _read_text_if_exists(report_base / "smoothing_qc_report.md"), "subject_smoothing_qc": subject_smoothing_qc}


def _make_nuisance_regression_approved_copy(source: Path, target: Path) -> Path:
    import yaml
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    for node in data.get("nodes", []):
        if node.get("id") in {"spm_slice_timing_subject","spm_realign_subject","spm_coregister_subject","spm_segment_subject","spm_normalize_subject","spm_smooth_subject"}:
            node.setdefault("params",{}); node["params"]["approved"] = True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target

@router.post("/api/rsfmri/nuisance-regression/run")
def api_run_rsfmri_nuisance_regression(request: RsfmriNuisanceRegressionRequest) -> dict[str, Any]:
    if not request.approved: raise HTTPException(status_code=403, detail="Nuisance regression pipeline requires approved=true because it depends on approved SPM preprocessing derivatives.")
    try:
        approved_pipeline = _make_nuisance_regression_approved_copy(source=Path(request.pipeline_path), target=Path("work/rsfmri/approved_pipeline_nuisance_regression.yaml"))
        summary = run_pipeline(request.project_config_path, str(approved_pipeline))
        if summary.get("status") not in {"SUCCESS", "PARTIAL"}: raise HTTPException(status_code=400, detail=summary)
        return summary
    except HTTPException: raise
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))

@router.get("/api/rsfmri/nuisance-regression")
def api_get_rsfmri_nuisance_regression() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"; derivatives_base = Path("derivatives"); work_base = Path("work") / "dpabi" / "contracts"
    subject_regression_qc = []; subject_confounds = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/nuisance_regression_qc.json")): subject_regression_qc.append(_read_json_if_exists(path))
    for path in sorted((derivatives_base / "rsfmri_confounds").glob("*/confound_qc.json")): subject_confounds.append(_read_json_if_exists(path))
    return {"ok": True, "nuisance_regression_qc_summary": _read_json_if_exists(report_base / "nuisance_regression_qc_summary.json"), "nuisance_regression_qc_report": _read_text_if_exists(report_base / "nuisance_regression_qc_report.md"), "subject_nuisance_regression_qc": subject_regression_qc, "subject_confound_qc": subject_confounds, "dpabi_backend_contract": _read_json_if_exists(work_base / "nuisance_regression_backend_contract.json")}

def _make_temporal_filtering_approved_copy(source: Path, target: Path) -> Path:
    import yaml; data = yaml.safe_load(source.read_text(encoding="utf-8"))
    for node in data.get("nodes", []):
        if node.get("id") in {"spm_slice_timing_subject","spm_realign_subject","spm_coregister_subject","spm_segment_subject","spm_normalize_subject","spm_smooth_subject"}:
            node.setdefault("params",{}); node["params"]["approved"] = True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8"); return target

@router.post("/api/rsfmri/temporal-filtering/run")
def api_run_rsfmri_temporal_filtering(request: RsfmriTemporalFilteringRequest) -> dict[str, Any]:
    if not request.approved: raise HTTPException(403, "Temporal filtering pipeline requires approved=true.")
    try:
        ap = _make_temporal_filtering_approved_copy(Path(request.pipeline_path), Path("work/rsfmri/approved_pipeline_temporal_filtering.yaml"))
        s = run_pipeline(request.project_config_path, str(ap))
        if s.get("status") not in {"SUCCESS","PARTIAL"}: raise HTTPException(400, detail=s)
        return s
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/rsfmri/temporal-filtering")
def api_get_rsfmri_temporal_filtering() -> dict[str, Any]:
    rb = Path("reports") / "rsfmri"; db = Path("derivatives"); wb = Path("work") / "dpabi" / "contracts"
    sqc = []; [sqc.append(_read_json_if_exists(p)) for p in sorted((db / "rsfmri_qc").glob("*/temporal_filtering_qc.json"))]
    return {"ok": True, "temporal_filtering_qc_summary": _read_json_if_exists(rb / "temporal_filtering_qc_summary.json"), "temporal_filtering_qc_report": _read_text_if_exists(rb / "temporal_filtering_qc_report.md"), "subject_temporal_filtering_qc": sqc, "dpabi_backend_contract": _read_json_if_exists(wb / "temporal_filtering_backend_contract.json")}

def _make_alff_falff_approved_copy(source: Path, target: Path) -> Path:
    import yaml; d = yaml.safe_load(source.read_text(encoding="utf-8"))
    for n in d.get("nodes", []):
        if n.get("id") in {"spm_slice_timing_subject","spm_realign_subject","spm_coregister_subject","spm_segment_subject","spm_normalize_subject","spm_smooth_subject"}: n.setdefault("params",{}); n["params"]["approved"] = True
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8"); return target

@router.post("/api/rsfmri/alff-falff/run")
def api_run_rsfmri_alff_falff(request: RsfmriAlffFalffRequest) -> dict[str, Any]:
    if not request.approved: raise HTTPException(403, "ALFF/fALFF pipeline requires approved=true.")
    try:
        ap = _make_alff_falff_approved_copy(Path(request.pipeline_path), Path("work/rsfmri/approved_pipeline_alff_falff.yaml"))
        s = run_pipeline(request.project_config_path, str(ap))
        if s.get("status") not in {"SUCCESS","PARTIAL"}: raise HTTPException(400, detail=s)
        return s
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/rsfmri/alff-falff")
def api_get_rsfmri_alff_falff() -> dict[str, Any]:
    rb = Path("reports") / "rsfmri"; db = Path("derivatives"); gb = Path("work") / "gpu" / "contracts"; wb = Path("work") / "dpabi" / "contracts"
    sqc = []; src = []
    [sqc.append(_read_json_if_exists(p)) for p in sorted((db / "rsfmri_qc").glob("*/alff_falff_qc.json"))]
    [src.append(_read_json_if_exists(p)) for p in sorted((db / "rsfmri_metrics").glob("*/alff_falff_result.json"))]
    return {"ok": True, "alff_falff_qc_summary": _read_json_if_exists(rb / "alff_falff_qc_summary.json"), "alff_falff_qc_report": _read_text_if_exists(rb / "alff_falff_qc_report.md"), "subject_alff_falff_qc": sqc, "subject_alff_falff_results": src, "gpu_candidate_contract": _read_json_if_exists(gb / "alff_falff_gpu_candidate_contract.json"), "dpabi_backend_contract": _read_json_if_exists(wb / "alff_falff_backend_contract.json")}

def _make_reho_approved_copy(source: Path, target: Path) -> Path:
    import yaml; d = yaml.safe_load(source.read_text(encoding="utf-8"))
    for n in d.get("nodes", []):
        if n.get("id") in {"spm_slice_timing_subject","spm_realign_subject","spm_coregister_subject","spm_segment_subject","spm_normalize_subject","spm_smooth_subject"}: n.setdefault("params",{}); n["params"]["approved"] = True
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8"); return target

@router.post("/api/rsfmri/reho/run")
def api_run_rsfmri_reho(request: RsfmriRehoRequest) -> dict[str, Any]:
    if not request.approved: raise HTTPException(403, "ReHo pipeline requires approved=true.")
    try:
        ap = _make_reho_approved_copy(Path(request.pipeline_path), Path("work/rsfmri/approved_pipeline_reho.yaml"))
        s = run_pipeline(request.project_config_path, str(ap))
        if s.get("status") not in {"SUCCESS","PARTIAL"}: raise HTTPException(400, detail=s)
        return s
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/rsfmri/reho")
def api_get_rsfmri_reho() -> dict[str, Any]:
    rb = Path("reports") / "rsfmri"; db = Path("derivatives"); gb = Path("work") / "gpu" / "contracts"; wb = Path("work") / "dpabi" / "contracts"
    sqc = []; src = []
    [sqc.append(_read_json_if_exists(p)) for p in sorted((db / "rsfmri_qc").glob("*/reho_qc.json"))]
    [src.append(_read_json_if_exists(p)) for p in sorted((db / "rsfmri_metrics").glob("*/reho_result.json"))]
    return {"ok": True, "reho_qc_summary": _read_json_if_exists(rb / "reho_qc_summary.json"), "reho_qc_report": _read_text_if_exists(rb / "reho_qc_report.md"), "subject_reho_qc": sqc, "subject_reho_results": src, "gpu_candidate_contract": _read_json_if_exists(gb / "reho_gpu_candidate_contract.json"), "dpabi_backend_contract": _read_json_if_exists(wb / "reho_backend_contract.json")}

def _make_fc_approved_copy(source: Path, target: Path) -> Path:
    import yaml; d = yaml.safe_load(source.read_text(encoding="utf-8"))
    for n in d.get("nodes", []):
        if n.get("id") in {"spm_slice_timing_subject","spm_realign_subject","spm_coregister_subject","spm_segment_subject","spm_normalize_subject","spm_smooth_subject"}: n.setdefault("params",{}); n["params"]["approved"] = True
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8"); return target

@router.post("/api/rsfmri/functional-connectivity/run")
def api_run_rsfmri_fc(request: RsfmriFunctionalConnectivityRequest) -> dict[str, Any]:
    if not request.approved: raise HTTPException(403, "FC pipeline requires approved=true.")
    try:
        ap = _make_fc_approved_copy(Path(request.pipeline_path), Path("work/rsfmri/approved_pipeline_fc.yaml"))
        s = run_pipeline(request.project_config_path, str(ap))
        if s.get("status") not in {"SUCCESS","PARTIAL"}: raise HTTPException(400, detail=s)
        return s
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/rsfmri/functional-connectivity")
def api_get_rsfmri_fc() -> dict[str, Any]:
    rb = Path("reports") / "rsfmri"; db = Path("derivatives"); gb = Path("work") / "gpu" / "contracts"; wb = Path("work") / "dpabi" / "contracts"
    sqc = []; src = []
    [sqc.append(_read_json_if_exists(p)) for p in sorted((db / "rsfmri_qc").glob("*/functional_connectivity_qc.json"))]
    [src.append(_read_json_if_exists(p)) for p in sorted((db / "rsfmri_fc").glob("*/fc_result.json"))]
    return {"ok": True, "functional_connectivity_qc_summary": _read_json_if_exists(rb / "functional_connectivity_qc_summary.json"), "functional_connectivity_qc_report": _read_text_if_exists(rb / "functional_connectivity_qc_report.md"), "subject_fc_qc": sqc, "subject_fc_results": src, "gpu_candidate_contract": _read_json_if_exists(gb / "functional_connectivity_gpu_candidate_contract.json"), "dpabi_backend_contract": _read_json_if_exists(wb / "functional_connectivity_backend_contract.json")}

@router.post("/api/rsfmri/group-summary/run")
def api_run_rsfmri_group_summary(request: RsfmriGroupSummaryRequest) -> dict[str, Any]:
    try:
        s = run_pipeline(request.project_config_path, request.pipeline_path)
        if s.get("status") not in {"SUCCESS","PARTIAL"}: raise HTTPException(400, detail=s)
        return s
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/rsfmri/group-summary")
def api_get_rsfmri_group_summary() -> dict[str, Any]:
    gb = Path("reports") / "rsfmri" / "group_summary"
    return {"ok": True, "dataset_summary": _read_json_if_exists(gb / "dataset_summary.json"), "dashboard_data": _read_json_if_exists(gb / "dashboard_data.json"), "pipeline_completeness": _read_json_if_exists(gb / "pipeline_completeness.json"), "contracts_overview": _read_json_if_exists(gb / "contracts_overview.json"), "dataset_summary_report": _read_text_if_exists(gb / "dataset_summary_report.md"), "subject_metrics_table_path": str(gb / "subject_metrics_table.csv")}

@router.post("/api/rsfmri/report-export/run")
def api_run_report_export(request: RsfmriReportExportRequest) -> dict[str, Any]:
    try:
        s = run_pipeline(request.project_config_path, request.pipeline_path)
        if s.get("status") not in {"SUCCESS","PARTIAL"}: raise HTTPException(400, detail=s)
        return s
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/rsfmri/report-export/latest")
def api_get_latest_report_export() -> dict[str, Any]: return get_latest_rsfmri_report_export()

@router.get("/api/rsfmri/report-export/list")
def api_list_report_exports() -> dict[str, Any]: return list_rsfmri_report_exports()

@router.post("/api/rsfmri/report-validator/run")
def api_run_report_validator(request: RsfmriReportValidationRequest) -> dict[str, Any]:
    try:
        s = run_pipeline(request.project_config_path, request.pipeline_path)
        if s.get("status") not in {"SUCCESS","PARTIAL"}: raise HTTPException(400, detail=s)
        return s
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/rsfmri/report-validator/latest")
def api_get_latest_report_validation() -> dict[str, Any]: return get_latest_rsfmri_report_validation()

@router.get("/api/rsfmri/report-validator/list")
def api_list_report_validations() -> dict[str, Any]: return list_rsfmri_report_validations()

@router.post("/api/release-readiness/run")
def api_run_release_readiness(request: ReleaseReadinessRequest) -> dict[str, Any]:
    try:
        s = run_pipeline(request.project_config_path, request.pipeline_path)
        return s
    except Exception as e: raise HTTPException(400, detail=str(e))

@router.get("/api/release-readiness")
def api_get_release_readiness() -> dict[str, Any]:
    rb = Path("reports/release_readiness")
    return {"ok": True, "result": _read_json_if_exists(rb/"release_readiness_result.json"), "report": _read_text_if_exists(rb/"release_readiness_report.md"), "dashboard": _read_json_if_exists(rb/"release_readiness_dashboard.json")}

@router.get("/api/deployment/profile")
def api_get_deployment_profile() -> dict[str, Any]:
    from backend.app.tools.deployment_profile import build_deployment_profile

    result = build_deployment_profile()
    return result
