"""Preprocessing domain routes — extracted from dashboard_routes.py.

All endpoints mirror the original behavior; the only change is store access
via ``Depends(get_project_store)`` instead of the module-level ``mock_store``.
Old routes remain registered in ``dashboard_routes.py`` with ``deprecated=True``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from src.backend.app.api.dependencies import ProjectStore

router = APIRouter()


def get_project_store() -> ProjectStore:
    from src.backend.app.services.mock_store import mock_store
    return mock_store  # type: ignore[return-value]


# Preprocessing handoff


@router.post(
    "/api/projects/{project_id}/preprocessing/input/register-converted",
    response_model=dict[str, Any],
)
def register_converted_preprocessing_input(
    project_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.preprocessing_adapter import (
        build_preprocessing_input_registration,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    return build_preprocessing_input_registration(
        project_id=project_id,
        body=body,
        project_dir=project_dir,
        store=store,
    )


@router.post(
    "/api/projects/{project_id}/preprocessing/plan/preview",
    response_model=dict[str, Any],
)
def preview_preprocessing_plan(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.preprocessing_adapter import (
        build_preprocessing_plan_preview,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    return build_preprocessing_plan_preview(
        project_id=project_id,
        project_dir=project_dir,
        store=store,
    )


# Preprocessing run workspace


@router.post(
    "/api/projects/{project_id}/preprocessing/runs",
    response_model=dict[str, Any],
)
def create_preprocessing_run(
    project_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.preprocessing_adapter import (
        build_preprocessing_run_create,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    return build_preprocessing_run_create(
        project_id=project_id,
        body=body,
        project_dir=project_dir,
        store=store,
    )


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/execute-python-preflight",
    response_model=dict[str, Any],
)
def execute_python_preflight_endpoint(
    project_id: str,
    preprocessing_run_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.preprocessing_adapter import (
        execute_python_preflight,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    return execute_python_preflight(
        project_id=project_id,
        preprocessing_run_id=preprocessing_run_id,
        project_dir=project_dir,
        store=store,
    )


@router.get(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}",
    response_model=dict[str, Any],
)
def get_preprocessing_run(
    project_id: str,
    preprocessing_run_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.preprocessing_adapter import (
        get_preprocessing_run_status,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    return get_preprocessing_run_status(
        project_id=project_id,
        preprocessing_run_id=preprocessing_run_id,
        project_dir=project_dir,
        store=store,
    )


# SPM/MATLAB runtime preflight


@router.get(
    "/api/projects/{project_id}/preprocessing/spm-runtime/preflight",
    response_model=dict[str, Any],
)
def spm_runtime_preflight(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.spm_runtime import spm_runtime_preflight as _preflight

    return _preflight(project_id).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/spm-runtime/synthetic-smoke",
    response_model=dict[str, Any],
)
def spm_synthetic_smoke(
    project_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.spm_runtime import SpmSyntheticSmokeRequest
    from src.backend.app.services.spm_runtime import run_synthetic_spm_smoke as _run
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = SpmSyntheticSmokeRequest(
        confirm_synthetic_only=bool(body.get("confirm_synthetic_only", False)),
        confirm_no_user_rawdata=bool(body.get("confirm_no_user_rawdata", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
        matlab_executable=str(body.get("matlab_executable", "matlab")),
        spm_path=str(body.get("spm_path", "")),
    )
    return _run(project_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# SPM Slice Timing + Realign


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/spm/slice-timing-realign/dry-run",
    response_model=dict[str, Any],
)
def slice_timing_realign_dry_run(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_spm_dry_run import SliceTimingRealignDryRunRequest
    from src.backend.app.services.preprocessing_spm_dry_run import (
        run_slice_timing_realign_dry_run as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = SliceTimingRealignDryRunRequest(
        tr=body.get("tr"),
        num_slices=body.get("num_slices"),
        slice_order=str(body.get("slice_order", "")),
        reference_slice=body.get("reference_slice"),
        confirm_dry_run_only=bool(body.get("confirm_dry_run_only", False)),
        confirm_no_matlab_execution=bool(body.get("confirm_no_matlab_execution", False)),
        confirm_no_image_modification=bool(body.get("confirm_no_image_modification", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/spm/slice-timing-realign/execute-sandbox",
    response_model=dict[str, Any],
)
def slice_timing_realign_sandbox(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_spm_execution import SpmSandboxExecutionRequest
    from src.backend.app.services.preprocessing_spm_execution import (
        run_sandbox_spm_execution as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = SpmSandboxExecutionRequest(
        dry_run_id=str(body.get("dry_run_id", "")),
        confirm_sandbox_copy=bool(body.get("confirm_sandbox_copy", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_no_converted_input_modification=bool(body.get("confirm_no_converted_input_modification", False)),
        confirm_slice_timing_realign_only=bool(body.get("confirm_slice_timing_realign_only", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
        matlab_executable=str(body.get("matlab_executable", "matlab")),
        spm_path=str(body.get("spm_path", "")),
        timeout_seconds=int(body.get("timeout_seconds", 600)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# Coregistration + Normalization


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/spm/coreg-normalize/dry-run",
    response_model=dict[str, Any],
)
def coreg_norm_dry_run(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_coreg_norm_dry_run import CoregNormDryRunRequest
    from src.backend.app.services.preprocessing_coreg_norm_dry_run import (
        run_coreg_norm_dry_run as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = CoregNormDryRunRequest(
        registered_stage_output_id=str(body.get("registered_stage_output_id", "")),
        confirm_dry_run_only=bool(body.get("confirm_dry_run_only", False)),
        confirm_no_matlab_execution=bool(body.get("confirm_no_matlab_execution", False)),
        confirm_no_image_modification=bool(body.get("confirm_no_image_modification", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        coreg_target=str(body.get("coreg_target", "mean_functional")),
        normalization_voxel_size=str(body.get("normalization_voxel_size", "[3,3,3]")),
        write_normalized_functional=bool(body.get("write_normalized_functional", True)),
        write_normalized_t1w=bool(body.get("write_normalized_t1w", True)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/spm/coreg-normalize/execute-sandbox",
    response_model=dict[str, Any],
)
def coreg_norm_sandbox(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_coreg_norm_execution import CoregNormSandboxExecutionRequest
    from src.backend.app.services.preprocessing_coreg_norm_execution import (
        run_coreg_norm_sandbox_execution as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = CoregNormSandboxExecutionRequest(
        dry_run_id=str(body.get("dry_run_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        confirm_sandbox_copy=bool(body.get("confirm_sandbox_copy", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_no_converted_input_modification=bool(body.get("confirm_no_converted_input_modification", False)),
        confirm_no_previous_output_modification=bool(body.get("confirm_no_previous_output_modification", False)),
        confirm_coreg_norm_only=bool(body.get("confirm_coreg_norm_only", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
        matlab_executable=str(body.get("matlab_executable", "matlab")),
        spm_path=str(body.get("spm_path", "")),
        timeout_seconds=int(body.get("timeout_seconds", 600)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# Smoothing


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/spm/smoothing/dry-run",
    response_model=dict[str, Any],
)
def smoothing_dry_run(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_smoothing_dry_run import SmoothingDryRunRequest
    from src.backend.app.services.preprocessing_smoothing_dry_run import (
        run_smoothing_dry_run as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = SmoothingDryRunRequest(
        registered_stage_output_id=str(body.get("registered_stage_output_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        fwhm=str(body.get("fwhm", "[6,6,6]")),
        confirm_dry_run_only=bool(body.get("confirm_dry_run_only", False)),
        confirm_no_matlab_execution=bool(body.get("confirm_no_matlab_execution", False)),
        confirm_no_image_modification=bool(body.get("confirm_no_image_modification", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_previous_outputs_readonly=bool(body.get("confirm_previous_outputs_readonly", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/spm/smoothing/execute-sandbox",
    response_model=dict[str, Any],
)
def smoothing_sandbox(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_smoothing_execution import SmoothingSandboxExecutionRequest
    from src.backend.app.services.preprocessing_smoothing_execution import (
        run_smoothing_sandbox_execution as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = SmoothingSandboxExecutionRequest(
        dry_run_id=str(body.get("dry_run_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        confirm_sandbox_copy=bool(body.get("confirm_sandbox_copy", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_no_converted_input_modification=bool(body.get("confirm_no_converted_input_modification", False)),
        confirm_previous_stage_readonly=bool(body.get("confirm_previous_stage_readonly", False)),
        confirm_smoothing_only=bool(body.get("confirm_smoothing_only", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
        matlab_executable=str(body.get("matlab_executable", "matlab")),
        spm_path=str(body.get("spm_path", "")),
        timeout_seconds=int(body.get("timeout_seconds", 600)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# Stage outputs registration helpers


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/stage-outputs/register-sandbox-spm",
    response_model=dict[str, Any],
)
def register_sandbox_spm_outputs(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import (
        register_sandbox_spm_outputs as _register,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = StageOutputRegistrationRequest(
        execution_id=str(body.get("execution_id", "")),
        confirm_sandbox_outputs=bool(body.get("confirm_sandbox_outputs", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        confirm_no_additional_execution=bool(body.get("confirm_no_additional_execution", False)),
        confirm_use_as_next_stage_input=bool(body.get("confirm_use_as_next_stage_input", False)),
    )
    return _register(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/stage-outputs/register-coreg-norm",
    response_model=dict[str, Any],
)
def register_coreg_norm_outputs(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import (
        register_coreg_norm_outputs as _register,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = StageOutputRegistrationRequest(
        execution_id=str(body.get("execution_id", "")),
        confirm_sandbox_outputs=bool(body.get("confirm_sandbox_outputs", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        confirm_no_additional_execution=bool(body.get("confirm_no_additional_execution", False)),
        confirm_use_as_next_stage_input=bool(body.get("confirm_use_as_next_stage_input", False)),
    )
    return _register(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/stage-outputs/register-smoothing",
    response_model=dict[str, Any],
)
def register_smoothing_outputs(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import (
        register_smoothing_outputs as _register,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = StageOutputRegistrationRequest(
        execution_id=str(body.get("execution_id", "")),
        confirm_sandbox_outputs=bool(body.get("confirm_sandbox_outputs", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        confirm_no_additional_execution=bool(body.get("confirm_no_additional_execution", False)),
        confirm_use_as_next_stage_input=bool(body.get("confirm_use_as_next_stage_input", False)),
    )
    return _register(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# Nuisance regression


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/nuisance-regression/dry-run",
    response_model=dict[str, Any],
)
def nuisance_dry_run(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_nuisance_dry_run import NuisanceDryRunRequest
    from src.backend.app.services.preprocessing_nuisance_dry_run import (
        run_nuisance_dry_run as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = NuisanceDryRunRequest(
        registered_stage_output_id=str(body.get("registered_stage_output_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        include_motion_24=bool(body.get("include_motion_24", True)),
        include_wm_csf=bool(body.get("include_wm_csf", False)),
        include_global_signal=bool(body.get("include_global_signal", False)),
        include_linear_trend=bool(body.get("include_linear_trend", True)),
        include_constant=bool(body.get("include_constant", True)),
        confirm_dry_run_only=bool(body.get("confirm_dry_run_only", False)),
        confirm_no_image_modification=bool(body.get("confirm_no_image_modification", False)),
        confirm_no_external_tools=bool(body.get("confirm_no_external_tools", False)),
        confirm_previous_outputs_readonly=bool(body.get("confirm_previous_outputs_readonly", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/nuisance-regression/execute-sandbox",
    response_model=dict[str, Any],
)
def nuisance_sandbox(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_nuisance_execution import NuisanceSandboxExecutionRequest
    from src.backend.app.services.preprocessing_nuisance_execution import (
        run_nuisance_sandbox_execution as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = NuisanceSandboxExecutionRequest(
        dry_run_id=str(body.get("dry_run_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        confirm_sandbox_copy=bool(body.get("confirm_sandbox_copy", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_previous_stage_readonly=bool(body.get("confirm_previous_stage_readonly", False)),
        confirm_nuisance_regression_only=bool(body.get("confirm_nuisance_regression_only", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/stage-outputs/register-nuisance",
    response_model=dict[str, Any],
)
def register_nuisance_outputs(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import (
        register_nuisance_outputs as _register,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = StageOutputRegistrationRequest(
        execution_id=str(body.get("execution_id", "")),
        confirm_sandbox_outputs=bool(body.get("confirm_sandbox_outputs", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        confirm_no_additional_execution=bool(body.get("confirm_no_additional_execution", False)),
        confirm_use_as_next_stage_input=bool(body.get("confirm_use_as_next_stage_input", False)),
    )
    return _register(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# Temporal filtering


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/temporal-filtering/dry-run",
    response_model=dict[str, Any],
)
def filtering_dry_run(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_filtering_dry_run import FilteringDryRunRequest
    from src.backend.app.services.preprocessing_filtering_dry_run import (
        run_filtering_dry_run as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = FilteringDryRunRequest(
        registered_stage_output_id=str(body.get("registered_stage_output_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        low_cut_hz=float(body.get("low_cut_hz", 0.01)),
        high_cut_hz=float(body.get("high_cut_hz", 0.08)),
        confirm_dry_run_only=bool(body.get("confirm_dry_run_only", False)),
        confirm_no_image_modification=bool(body.get("confirm_no_image_modification", False)),
        confirm_no_external_tools=bool(body.get("confirm_no_external_tools", False)),
        confirm_previous_outputs_readonly=bool(body.get("confirm_previous_outputs_readonly", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/temporal-filtering/execute-sandbox",
    response_model=dict[str, Any],
)
def filtering_sandbox(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_filtering_execution import FilteringSandboxExecutionRequest
    from src.backend.app.services.preprocessing_filtering_execution import (
        run_filtering_sandbox_execution as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = FilteringSandboxExecutionRequest(
        dry_run_id=str(body.get("dry_run_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        confirm_sandbox_copy=bool(body.get("confirm_sandbox_copy", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_previous_stage_readonly=bool(body.get("confirm_previous_stage_readonly", False)),
        confirm_temporal_filtering_only=bool(body.get("confirm_temporal_filtering_only", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/stage-outputs/register-filtering",
    response_model=dict[str, Any],
)
def register_filtering_outputs(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import (
        register_filtering_outputs as _register,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = StageOutputRegistrationRequest(
        execution_id=str(body.get("execution_id", "")),
        confirm_sandbox_outputs=bool(body.get("confirm_sandbox_outputs", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        confirm_no_additional_execution=bool(body.get("confirm_no_additional_execution", False)),
        confirm_use_as_next_stage_input=bool(body.get("confirm_use_as_next_stage_input", False)),
    )
    return _register(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# ALFF/ReHo


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/alff-reho/dry-run",
    response_model=dict[str, Any],
)
def alff_reho_dry_run(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_alff_reho_dry_run import AlffRehoDryRunRequest
    from src.backend.app.services.preprocessing_alff_reho_dry_run import (
        run_alff_reho_dry_run as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = AlffRehoDryRunRequest(
        registered_stage_output_id=str(body.get("registered_stage_output_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        compute_alff=bool(body.get("compute_alff", True)),
        compute_falff=bool(body.get("compute_falff", True)),
        compute_reho=bool(body.get("compute_reho", True)),
        reho_neighbors=int(body.get("reho_neighbors", 27)),
        confirm_dry_run_only=bool(body.get("confirm_dry_run_only", False)),
        confirm_no_image_modification=bool(body.get("confirm_no_image_modification", False)),
        confirm_no_external_tools=bool(body.get("confirm_no_external_tools", False)),
        confirm_previous_outputs_readonly=bool(body.get("confirm_previous_outputs_readonly", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/alff-reho/execute-sandbox",
    response_model=dict[str, Any],
)
def alff_reho_sandbox(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_alff_reho_execution import AlffRehoSandboxExecutionRequest
    from src.backend.app.services.preprocessing_alff_reho_execution import (
        run_alff_reho_sandbox_execution as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = AlffRehoSandboxExecutionRequest(
        dry_run_id=str(body.get("dry_run_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        confirm_sandbox_copy=bool(body.get("confirm_sandbox_copy", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_previous_stage_readonly=bool(body.get("confirm_previous_stage_readonly", False)),
        confirm_alff_reho_only=bool(body.get("confirm_alff_reho_only", False)),
        confirm_no_fc_execution=bool(body.get("confirm_no_fc_execution", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/stage-outputs/register-alff-reho",
    response_model=dict[str, Any],
)
def register_alff_reho_outputs(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import (
        register_alff_reho_outputs as _register,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = StageOutputRegistrationRequest(
        execution_id=str(body.get("execution_id", "")),
        confirm_sandbox_outputs=bool(body.get("confirm_sandbox_outputs", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        confirm_no_additional_execution=bool(body.get("confirm_no_additional_execution", False)),
        confirm_use_as_next_stage_input=bool(body.get("confirm_use_as_next_stage_input", False)),
    )
    return _register(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# FC


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/fc/dry-run",
    response_model=dict[str, Any],
)
def fc_dry_run(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_fc_dry_run import FcDryRunRequest
    from src.backend.app.services.preprocessing_fc_dry_run import (
        run_fc_dry_run as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = FcDryRunRequest(
        filtered_stage_output_id=str(body.get("filtered_stage_output_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        atlas_name=str(body.get("atlas_name", "")),
        atlas_path=str(body.get("atlas_path", "")),
        correlation_method=str(body.get("correlation_method", "pearson")),
        fisher_z=bool(body.get("fisher_z", True)),
        confirm_dry_run_only=bool(body.get("confirm_dry_run_only", False)),
        confirm_no_image_modification=bool(body.get("confirm_no_image_modification", False)),
        confirm_no_external_tools=bool(body.get("confirm_no_external_tools", False)),
        confirm_previous_outputs_readonly=bool(body.get("confirm_previous_outputs_readonly", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/fc/execute-sandbox",
    response_model=dict[str, Any],
)
def fc_sandbox(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_fc_execution import FcSandboxExecutionRequest
    from src.backend.app.services.preprocessing_fc_execution import (
        run_fc_sandbox_execution as _run,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = FcSandboxExecutionRequest(
        dry_run_id=str(body.get("dry_run_id", "")),
        functional_input_dir=str(body.get("functional_input_dir", "")),
        confirm_sandbox_copy=bool(body.get("confirm_sandbox_copy", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_previous_stage_readonly=bool(body.get("confirm_previous_stage_readonly", False)),
        confirm_fc_only=bool(body.get("confirm_fc_only", False)),
        confirm_no_group_statistics=bool(body.get("confirm_no_group_statistics", False)),
        confirm_no_classification=bool(body.get("confirm_no_classification", False)),
        confirm_no_full_preprocessing=bool(body.get("confirm_no_full_preprocessing", False)),
        confirm_research_use_only=bool(body.get("confirm_research_use_only", False)),
    )
    return _run(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.post(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/stage-outputs/register-fc",
    response_model=dict[str, Any],
)
def register_fc_outputs(
    project_id: str,
    preprocessing_run_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import (
        register_fc_outputs as _register,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    req = StageOutputRegistrationRequest(
        execution_id=str(body.get("execution_id", "")),
        confirm_sandbox_outputs=bool(body.get("confirm_sandbox_outputs", False)),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_converted_input_readonly=bool(body.get("confirm_converted_input_readonly", False)),
        confirm_no_additional_execution=bool(body.get("confirm_no_additional_execution", False)),
        confirm_use_as_next_stage_input=bool(body.get("confirm_use_as_next_stage_input", False)),
    )
    return _register(project_id, preprocessing_run_id, req, project_dir=str(meta.get("project_dir", ""))).model_dump()


# Reports


@router.get(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/report",
    response_model=dict[str, Any],
)
def get_pipeline_report(
    project_id: str,
    preprocessing_run_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.preprocessing_pipeline_report import (
        generate_pipeline_report as _generate,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    return _generate(project_id, preprocessing_run_id, project_dir=str(meta.get("project_dir", ""))).model_dump()


@router.get(
    "/api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/validation",
    response_model=dict[str, Any],
)
def get_pipeline_validation(
    project_id: str,
    preprocessing_run_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.preprocessing_pipeline_validation import (
        validate_preprocessing_pipeline as _validate,
    )
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    return _validate(project_id, preprocessing_run_id, project_dir=str(meta.get("project_dir", ""))).model_dump()
