"""DICOM conversion domain router — extracted from dashboard_routes.py.

All conversion endpoints are preserved with identical URL paths and response
contracts.  The new router uses ``Depends(get_project_store)`` so route
handlers do not reach for the global ``mock_store`` directly.

The original definitions in ``dashboard_routes.py`` are kept with a
``@deprecated`` marker (see that file) and will be removed once downstream
callers are migrated.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.backend.app.api.dependencies import ProjectStore, get_project_store
from src.backend.app.schemas.desktop import (
    ConversionDryRunRequest,
    ConversionDryRunResponse,
    DicomPreflightResponse,
)
from src.backend.app.schemas.dicom_conversion_public_execution import (
    DicomConversionPublicExecutionRequest,
    DicomConversionPublicExecutionResponse,
)
from src.backend.app.services.dicom_conversion_service import (
    run_conversion_dry_run,
    run_conversion_execute,
    run_conversion_preflight,
    run_conversion_persist_plan,
    run_export_conversion_review_package,
    run_get_conversion_release_readiness,
    run_get_conversion_review_package,
)

router = APIRouter()


# ── Dry-run ───────────────────────────────────────────────────────────────

@router.post(
    "/api/projects/{project_id}/conversion/dry-run",
    response_model=ConversionDryRunResponse,
    deprecated=True,
    summary="[deprecated] use the same path on this router",
)
def post_conversion_dry_run(
    project_id: str,
    request: ConversionDryRunRequest = ConversionDryRunRequest(),
    store: ProjectStore = Depends(get_project_store),
) -> ConversionDryRunResponse:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return run_conversion_dry_run(store, project_id, request)


# ── Preflight ─────────────────────────────────────────────────────────────

@router.post(
    "/api/projects/{project_id}/conversion/preflight",
    deprecated=True,
    summary="[deprecated] use the same path on this router",
)
def post_conversion_preflight(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return run_conversion_preflight(store, project_id)


# ── Approval / plan persistence ──────────────────────────────────────────

@router.post(
    "/api/projects/{project_id}/conversion/approval/persist-plan",
    deprecated=True,
    summary="[deprecated] use the same path on this router",
)
def post_conversion_persist_plan(
    project_id: str,
    body: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return run_conversion_persist_plan(store, project_id, body)


# ── Review package ────────────────────────────────────────────────────────

@router.get(
    "/api/projects/{project_id}/conversion/approval/packages/{conversion_run_id}",
    deprecated=True,
    summary="[deprecated] use the same path on this router",
)
def get_conversion_review_package(
    project_id: str,
    conversion_run_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return run_get_conversion_review_package(store, project_id, conversion_run_id)


@router.post(
    "/api/projects/{project_id}/conversion/approval/packages/{conversion_run_id}/export",
    deprecated=True,
    summary="[deprecated] use the same path on this router",
)
def post_conversion_review_package_export(
    project_id: str,
    conversion_run_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return run_export_conversion_review_package(store, project_id, conversion_run_id)


# ── Release readiness ─────────────────────────────────────────────────────

@router.get(
    "/api/projects/{project_id}/conversion/release-readiness/{conversion_run_id}",
    deprecated=True,
    summary="[deprecated] use the same path on this router",
)
def get_conversion_release_readiness(
    project_id: str,
    conversion_run_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if not store.get_project(project_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return run_get_conversion_release_readiness(store, project_id, conversion_run_id)


# ── Public execute ────────────────────────────────────────────────────────

@router.post(
    "/api/projects/{project_id}/conversion/execute",
    deprecated=True,
    summary="[deprecated] use the same path on this router",
)
def post_conversion_execute(
    project_id: str,
    request_raw: dict[str, Any] | None = None,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    # Missing-project is handled inside the service as a blocked response so
    # callers can distinguish "endpoint exists but gated" from "no such route".
    return run_conversion_execute(store, project_id, request_raw)
