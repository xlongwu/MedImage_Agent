"""Service adapter for preprocessing routes.

Thin adapter that accepts ProjectStore and delegates to the existing
preprocessing service functions.  Preserves all current behavior; only
changes how the store is supplied (Depends injection instead of module-level
mock_store).
"""

from __future__ import annotations

from src.backend.app.api.dependencies import ProjectStore


def build_preprocessing_input_registration(
    project_id: str,
    body: dict[str, object],
    project_dir: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.schemas.preprocessing_handoff import (
        PreprocessingInputRegistrationRequest,
    )
    from src.backend.app.services.preprocessing_handoff import (
        register_converted_bids_as_preprocessing_input,
    )

    req = PreprocessingInputRegistrationRequest(
        conversion_run_id=str(body.get("conversion_run_id", "")),
        converted_bids_dir=body.get("converted_bids_dir"),
        manifest_path=body.get("manifest_path"),
        provenance_path=body.get("provenance_path"),
        checksum_verified=bool(body.get("checksum_verified", False)),
        mode=str(body.get("mode", "reference")),
        confirm_rawdata_readonly=bool(body.get("confirm_rawdata_readonly", False)),
        confirm_use_converted_outputs=bool(body.get("confirm_use_converted_outputs", False)),
    )
    return register_converted_bids_as_preprocessing_input(
        project_id=project_id,
        request=req,
        project_dir=project_dir,
        store=store,
    ).model_dump()


def build_preprocessing_plan_preview(
    project_id: str,
    project_dir: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.schemas.preprocessing_handoff import (
        build_default_dparsfa_style_plan,
    )
    project = store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    input_registered = bool(metadata.get("preprocessing_input_dir"))

    plan = build_default_dparsfa_style_plan(
        project_id=project_id,
        input_registered=input_registered,
    )
    return plan.model_dump()


def build_preprocessing_run_create(
    project_id: str,
    body: dict[str, object],
    project_dir: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run

    req = PreprocessingRunCreateRequest(
        plan_id=str(body.get("plan_id", "")),
        preprocessing_input_dir=str(body.get("preprocessing_input_dir", "")),
        input_registry_path=str(body.get("input_registry_path", "")),
        source_kind=str(body.get("source_kind", "")),
        conversion_run_id=str(body.get("conversion_run_id", "")),
        run_name=str(body.get("run_name", "")),
        confirm_use_converted_input=bool(body.get("confirm_use_converted_input", False)),
        confirm_no_rawdata_modification=bool(body.get("confirm_no_rawdata_modification", False)),
        confirm_python_only_execution=bool(body.get("confirm_python_only_execution", False)),
        confirm_no_spm_matlab=bool(body.get("confirm_no_spm_matlab", False)),
    )
    return create_preprocessing_run(
        project_id,
        req,
        project_dir=project_dir,
        store=store,
    ).model_dump()


def execute_python_preflight(
    project_id: str,
    preprocessing_run_id: str,
    project_dir: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.preprocessing_run import execute_python_preflight

    return execute_python_preflight(
        project_id,
        preprocessing_run_id,
        project_dir=project_dir,
        store=store,
    ).model_dump()


def get_preprocessing_run_status(
    project_id: str,
    preprocessing_run_id: str,
    project_dir: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.preprocessing_run import get_preprocessing_run_status

    return get_preprocessing_run_status(
        project_id,
        preprocessing_run_id,
        project_dir=project_dir,
        store=store,
    ).model_dump()
