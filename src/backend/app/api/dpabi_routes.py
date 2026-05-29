"""DPABI route handlers — MATLAB/DPABI capability, sandbox, templates.

Extracted from routes.py for domain cohesion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.backend.app.api._shared import (
    _load_project_config,
    _read_json_if_exists,
    _read_text_if_exists,
)
from src.backend.app.api.models import (
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
)
from src.backend.app.tools.dpabi_adapter import build_dpabi_input_manifest
from src.backend.app.tools.dpabi_config import write_dpabi_wrapper_scaffold
from src.backend.app.tools.dpabi_contract_registry import write_dpabi_wrapper_contracts
from src.backend.app.tools.dpabi_preflight import run_dpabi_preflight
from src.backend.app.tools.dpabi_run_plan import create_dpabi_run_plan
from src.backend.app.tools.dpabi_runner import run_dpabi_capability_inspection
from src.backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke
from src.backend.app.tools.dpabi_signature_runner import run_dpabi_signature_probe
from src.backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox
from src.backend.app.tools.dpabi_subject_wrapper import run_dpabi_subject_smooth
from src.backend.app.tools.dpabi_subject_wrapper_report import write_dpabi_subject_wrapper_report
from src.backend.app.tools.dpabi_template_instantiator import (
    execute_dpabi_template_instance,
    instantiate_dpabi_template,
    list_dpabi_templates,
)
from src.backend.app.tools.dpabi_template_library import write_dpabi_template_library
from src.backend.app.tools.dpabi_template_wizard import (
    create_dpabi_template_instance_from_wizard,
    get_dpabi_template_wizard_options,
    preview_dpabi_template_instance,
)
from src.backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix

router = APIRouter()


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
            matrix_path=request.signatures_path.replace(
                "dpabi_function_signatures.json",
                "dpabi_wrapper_compatibility_matrix.json",
            ),
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
    base = Path("outputs/work") / "dpabi" / "template_wizard"

    return {
        "ok": True,
        "latest_preview": _read_json_if_exists(base / "latest_preview.json"),
        "latest_preview_markdown": _read_text_if_exists(base / "latest_preview.md"),
    }
