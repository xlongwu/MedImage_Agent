"""rs-fMRI pipeline QC and report route handlers.

Extracted from routes.py for domain cohesion.
All endpoints delegate to run_pipeline with domain-specific pipeline YAMLs.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from src.backend.app.api._shared import (
    _load_project_config,
    _read_json_if_exists,
    _read_text_if_exists,
)
from src.backend.app.api.models import (
    RsfmriAlffFalffRequest,
    RsfmriCoregistrationQcRequest,
    RsfmriFunctionalConnectivityRequest,
    RsfmriGroupSummaryRequest,
    RsfmriNormalizationQcRequest,
    RsfmriNuisanceRegressionRequest,
    RsfmriRehoRequest,
    RsfmriReportExportRequest,
    RsfmriReportValidationRequest,
    RsfmriSegmentationTissueQcRequest,
    RsfmriSmoothingQcRequest,
    RsfmriSpmRealignMotionQcRequest,
    RsfmriSpmSliceTimingRequest,
    RsfmriStRealignMotionQcRequest,
    RsfmriTemporalFilteringRequest,
    ReleaseReadinessRequest,
)
from src.backend.app.runtime.pipeline_executor import run_pipeline
from src.backend.app.schemas.pipeline_schema import load_pipeline_yaml
from src.backend.app.tools.report_exporter import (
    get_latest_rsfmri_report_export,
    list_rsfmri_report_exports,
)
from src.backend.app.tools.report_package_validator import (
    get_latest_rsfmri_report_validation,
    list_rsfmri_report_validations,
)

router = APIRouter()

# ── Helper ────────────────────────────────────────────────────────────────

def _run_rsfmri_pipeline(
    project_config_path: str,
    pipeline_path: str,
) -> dict[str, Any]:
    """Shared runner for all rs-fMRI pipeline endpoints."""
    result = run_pipeline(
        project_config_path=project_config_path,
        pipeline_path=pipeline_path,
    )
    if result.get("status") in {"SUCCESS", "PARTIAL"}:
        return {"ok": True, **result}
    raise HTTPException(status_code=400, detail=result)


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
        raise HTTPException(status_code=404, detail="No chain report found.")
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


# ── SPM pipeline QC endpoints ─────────────────────────────────────────────

@router.post("/api/rsfmri/spm/realign-motion-qc")
def api_rsfmri_spm_realign_motion_qc(payload: RsfmriSpmRealignMotionQcRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/spm/slice-timing")
def api_rsfmri_spm_slice_timing(payload: RsfmriSpmSliceTimingRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/st/realign-motion-qc")
def api_rsfmri_st_realign_motion_qc(payload: RsfmriStRealignMotionQcRequest) -> dict[str, Any]:
    project_config = _load_project_config(payload.project_config_path)
    pipeline = load_pipeline_yaml(payload.pipeline_path)

    approved_pipeline_path = None
    if payload.approved:
        for node in pipeline.nodes:
            if node.id == "spm_realign_subject":
                node.params["approved"] = True

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
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/segmentation-tissue-qc")
def api_rsfmri_segmentation_tissue_qc(payload: RsfmriSegmentationTissueQcRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/normalization-qc")
def api_rsfmri_normalization_qc(payload: RsfmriNormalizationQcRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/smoothing-qc")
def api_rsfmri_smoothing_qc(payload: RsfmriSmoothingQcRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/nuisance-regression")
def api_rsfmri_nuisance_regression(payload: RsfmriNuisanceRegressionRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/temporal-filtering")
def api_rsfmri_temporal_filtering(payload: RsfmriTemporalFilteringRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/alff-falff")
def api_rsfmri_alff_falff(payload: RsfmriAlffFalffRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/reho")
def api_rsfmri_reho(payload: RsfmriRehoRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/functional-connectivity")
def api_rsfmri_functional_connectivity(payload: RsfmriFunctionalConnectivityRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/group-summary")
def api_rsfmri_group_summary(payload: RsfmriGroupSummaryRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/report-export")
def api_rsfmri_report_export(payload: RsfmriReportExportRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/rsfmri/report-validation")
def api_rsfmri_report_validation(payload: RsfmriReportValidationRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


@router.post("/api/release-readiness")
def api_release_readiness(payload: ReleaseReadinessRequest) -> dict[str, Any]:
    return _run_rsfmri_pipeline(payload.project_config_path, payload.pipeline_path)


# ── Report export / validation listing ────────────────────────────────────

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
