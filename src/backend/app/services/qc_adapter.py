"""Service adapter for QC routes.

Thin adapter that accepts ProjectStore and delegates to the existing QC
service functions.  Preserves all current behavior; only changes how the
store is supplied (Depends injection instead of module-level mock_store).
"""

from __future__ import annotations

from src.backend.app.api.dependencies import ProjectStore


def build_qc_dashboard_report(
    project_id: str,
    cache: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.qc_dashboard_report import build_qc_dashboard_report as _build

    if cache not in ("off", "prefer", "refresh"):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cache mode: {cache}. Use off, prefer, or refresh.",
        )
    return _build(project_id, cache_mode=cache).model_dump()


def load_latest_qc_dashboard_report(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from fastapi import HTTPException
    from src.backend.app.services.qc_dashboard_report import (
        load_latest_qc_dashboard_report as _load,
    )

    result = _load(project_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No QC dashboard report has been generated yet.",
        )
    return result.model_dump()


def build_qc_dashboard_fingerprint(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.mock_store import mock_store
    from src.backend.app.services.qc_dashboard_fingerprint import (
        collect_qc_dashboard_fingerprint_roots,
    )
    from src.backend.app.services.rawdata_fingerprint import build_rawdata_fingerprint

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    roots = collect_qc_dashboard_fingerprint_roots(metadata)
    fp = build_rawdata_fingerprint(roots)
    return {
        "ok": fp.ok,
        "project_id": project_id,
        "fingerprint": fp.model_dump(),
        "roots": fp.roots,
        "warnings": fp.warnings,
        "errors": fp.errors,
        "safety_flags": {
            "read_only": True,
            "rawdata_not_modified": True,
            "metadata_only": True,
            "no_cache_files_created": True,
            "no_preprocessing_executed": True,
            "no_external_tools_executed": True,
        },
    }


def build_data_readiness(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.data_readiness import build_data_readiness as _build

    return _build(project_id).model_dump()


def validate_bids(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.bids_validation import validate_bids as _validate
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    roots: list[str] = []
    rawdata = metadata.get("rawdata_dir")
    if rawdata and isinstance(rawdata, str):
        roots.append(rawdata)
    try:
        import_roots = mock_store.list_import_paths(project_id)
        for r in import_roots:
            if r not in roots:
                roots.append(r)
    except Exception:
        pass
    result = _validate(roots)
    result.project_id = project_id
    return result.model_dump()


def build_bold_reference_readiness(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.bold_reference_readiness import (
        build_bold_reference_readiness as _build,
    )

    return _build(project_id).model_dump()


def build_rsfmri_qc_planning_report(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.rsfmri_qc_planning_report import (
        build_rsfmri_qc_planning_report as _build,
    )

    return _build(project_id).model_dump()


def build_motion_metrics_draft(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.motion_metrics_draft import (
        build_motion_metrics_draft as _build,
    )

    return _build(project_id).model_dump()


def build_spm_realign_dry_run(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.spm_realign_dry_run import (
        build_spm_realign_dry_run as _build,
    )

    return _build(project_id).model_dump()


def build_spm_realign_wrapper_skeleton(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.spm_realign_wrapper_skeleton import (
        build_spm_realign_wrapper_skeleton as _build,
    )

    return _build(project_id).model_dump()


def build_nifti_qc_snapshot(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.nifti_qc_snapshot import (
        build_nifti_qc_snapshot as _build,
    )

    return _build(project_id).model_dump()


def build_nifti_thumbnail(
    project_id: str,
    image_id: str,
    view: str,
    volume_index: int | None,
    size: int | None,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.nifti_thumbnail import build_nifti_thumbnail as _build

    return _build(project_id, image_id, view, volume_index, size).model_dump()


def build_motion_qc_readiness(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.motion_qc_readiness import (
        build_motion_qc_readiness as _build,
    )

    return _build(project_id).model_dump()
