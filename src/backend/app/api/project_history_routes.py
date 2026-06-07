"""Project-scoped reviewed plan and execution history APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.backend.app.planner.reviewed_plan_store import (
    ReviewedPlanStoreError,
    artifact_warnings,
    save_reviewed_plan,
    snapshot_warnings,
)
from src.backend.app.schemas.desktop import ProjectDetail, ReviewedPlanRecord, RunLinkRecord
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.run_artifact_discovery import (
    discover_run_artifacts,
    find_run_artifact,
)
from src.backend.app.services.run_artifact_preview import artifact_preview_payload
from src.backend.app.services.run_event_log_reader import (
    discover_run_events,
    discover_run_logs,
)
from src.backend.app.services.run_summary_preview import load_run_summary_preview
from src.backend.app.tools.artifact_utils import is_safe_artifact_id

router = APIRouter()


class ReviewedPlanSaveRequest(BaseModel):
    plan: dict[str, Any]
    project_config_path: str | None = None
    validation: dict[str, Any] = Field(default_factory=dict)
    goal: str | None = None
    provider: str | None = None
    status: str = "REVIEWED"
    warnings: list[str] = Field(default_factory=list)


def _ensure_project(project_id: str) -> None:
    if mock_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def _get_project(project_id: str) -> ProjectDetail:
    project = mock_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return project


def _reviewed_plan_payload(record: ReviewedPlanRecord) -> dict[str, Any]:
    payload = record.model_dump()
    payload["warnings"] = snapshot_warnings(record)
    return payload


def _run_link_payload(record: RunLinkRecord) -> dict[str, Any]:
    payload = record.model_dump()
    payload["warnings"] = artifact_warnings(record)
    return payload


def _dedupe(messages: list[str]) -> list[str]:
    return list(dict.fromkeys(message for message in messages if message))


@router.post("/api/projects/{project_id}/plans")
def save_project_reviewed_plan(
    project_id: str,
    request: ReviewedPlanSaveRequest,
) -> dict[str, Any]:
    _ensure_project(project_id)
    try:
        record = save_reviewed_plan(
            project_id=project_id,
            project_config_path=request.project_config_path,
            plan=request.plan,
            validation=request.validation,
            goal=request.goal,
            provider=request.provider,
            status=request.status,
            warnings=request.warnings,
        )
    except ReviewedPlanStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "reviewed_plan": _reviewed_plan_payload(record)}


@router.get("/api/projects/{project_id}/plans")
def list_project_reviewed_plans(project_id: str) -> dict[str, Any]:
    _ensure_project(project_id)
    return {
        "ok": True,
        "project_id": project_id,
        "reviewed_plans": [
            _reviewed_plan_payload(record)
            for record in mock_store.list_reviewed_plans(project_id)
        ],
    }


@router.get("/api/projects/{project_id}/plans/{reviewed_plan_id}")
def get_project_reviewed_plan(
    project_id: str,
    reviewed_plan_id: str,
) -> dict[str, Any]:
    _ensure_project(project_id)
    record = mock_store.get_reviewed_plan(reviewed_plan_id)
    if record is None or record.project_id != project_id:
        raise HTTPException(status_code=404, detail="Reviewed plan not found")
    return {"ok": True, "reviewed_plan": _reviewed_plan_payload(record)}


@router.get("/api/projects/{project_id}/runs")
def list_project_run_links(
    project_id: str,
    reviewed_plan_id: str | None = Query(default=None),
) -> dict[str, Any]:
    _ensure_project(project_id)
    return {
        "ok": True,
        "project_id": project_id,
        "runs": [
            _run_link_payload(record)
            for record in mock_store.list_run_links(project_id, reviewed_plan_id)
        ],
    }


@router.get("/api/projects/{project_id}/runs/{run_id}")
def get_project_run_link(project_id: str, run_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    run_link = _run_link_payload(record)
    summary_preview, summary_warnings, summary_error = load_run_summary_preview(
        project,
        record,
    )
    warnings = _dedupe(
        [
            *run_link.get("warnings", []),
            *summary_warnings,
            *([summary_error] if summary_error else []),
        ]
    )
    return {
        "ok": True,
        "run_link": run_link,
        "summary_preview": summary_preview,
        "summary_preview_error": summary_error,
        "warnings": warnings,
    }


@router.get("/api/projects/{project_id}/runs/{run_id}/artifacts")
def list_project_run_artifacts(project_id: str, run_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    artifacts, warnings = discover_run_artifacts(project, record)
    return {
        "ok": True,
        "project_id": project_id,
        "run_id": run_id,
        "artifacts": artifacts,
        "warnings": warnings,
    }


@router.get("/api/projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}")
def get_project_run_artifact(
    project_id: str,
    run_id: str,
    artifact_id: str,
) -> dict[str, Any]:
    if not is_safe_artifact_id(artifact_id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    artifact, warnings = find_run_artifact(project, record, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found for run")
    payload = artifact_preview_payload(artifact)
    payload["project_id"] = project_id
    payload["run_id"] = run_id
    payload["warnings"] = _dedupe([*warnings, *payload.get("warnings", [])])
    return payload


@router.get("/api/projects/{project_id}/runs/{run_id}/events")
def list_project_run_events(project_id: str, run_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    events, warnings = discover_run_events(project, record)
    return {
        "ok": True,
        "project_id": project_id,
        "run_id": run_id,
        "events": events,
        "warnings": warnings,
        "errors": [],
    }


@router.get("/api/projects/{project_id}/runs/{run_id}/logs")
def list_project_run_logs(
    project_id: str,
    run_id: str,
    max_bytes: int = Query(default=20000, ge=1000, le=200000),
    include_content: bool = Query(default=True),
) -> dict[str, Any]:
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    logs, warnings, errors = discover_run_logs(
        project,
        record,
        max_bytes=max_bytes,
        include_content=include_content,
    )
    return {
        "ok": True,
        "project_id": project_id,
        "run_id": run_id,
        "logs": logs,
        "warnings": warnings,
        "errors": errors,
    }
