"""Task domain routes — extracted from dashboard_routes.py.

All endpoints mirror the original behavior; the only change is store access
via ``Depends(get_project_store)`` instead of the module-level ``mock_store``.
Old routes remain registered in ``dashboard_routes.py`` with ``deprecated=True``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from src.backend.app.api.dependencies import ProjectStore
from src.backend.app.schemas.desktop import (
    AssistantChatRequest,
    AssistantChatResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    TaskApprovalRequest,
    TaskApprovalResponse,
    TaskArtifactsResponse,
    TaskAuditPackageResponse,
    TaskDiagnosticsResponse,
    TaskDetail,
    TaskEvent,
    TaskLogEntry,
)
from src.backend.app.services.task_adapter import (
    approve_task,
    generate_task_audit_package,
    get_task,
    get_task_artifacts,
    get_task_diagnostics,
    list_task_events,
    list_tasks,
)

router = APIRouter()


def get_project_store() -> ProjectStore:
    from src.backend.app.services.mock_store import mock_store
    return mock_store  # type: ignore[return-value]


# Task listing and detail


@router.get(
    "/api/tasks",
    response_model=list[dict[str, object]],
)
def list_tasks_endpoint(
    store: ProjectStore = Depends(get_project_store),
) -> list[dict[str, object]]:
    return list_tasks(store=store)


@router.get(
    "/api/tasks/{task_id}",
    response_model=dict[str, object],
)
def get_task_endpoint(
    task_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    return get_task(task_id=task_id, store=store)


@router.get(
    "/api/tasks/{task_id}/events",
    response_model=list[dict[str, object]],
)
def get_task_events_endpoint(
    task_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> list[dict[str, object]]:
    return list_task_events(task_id=task_id, store=store)


@router.post(
    "/api/tasks/{task_id}/approve",
    response_model=dict[str, object],
)
async def approve_task_endpoint(
    task_id: str,
    request: TaskApprovalRequest,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    return await approve_task(
        task_id=task_id,
        request=request.model_dump(),
        store=store,
    )


# Task diagnostics and artifacts


@router.get(
    "/api/tasks/{task_id}/diagnostics",
    response_model=dict[str, object],
)
def get_task_diagnostics_endpoint(
    task_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    return get_task_diagnostics(task_id=task_id, store=store)


@router.get(
    "/api/tasks/{task_id}/artifacts",
    response_model=dict[str, object],
)
def get_task_artifacts_endpoint(
    task_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    return get_task_artifacts(task_id=task_id, store=store)


@router.post(
    "/api/tasks/{task_id}/audit-package",
    response_model=dict[str, object],
)
def generate_task_audit_package_endpoint(
    task_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    return generate_task_audit_package(task_id=task_id, store=store)


# Pipeline execution


@router.post(
    "/api/pipelines/run",
    response_model=dict[str, object],
)
async def run_pipeline(
    request: PipelineRunRequest,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    import asyncio
    from fastapi import HTTPException
    from src.backend.app.services.mock_store import mock_store
    from src.backend.app.services.pipeline_runner import run_pipeline_task
    from src.backend.app.services.task_manager import task_manager

    if not request.input_sequences:
        raise HTTPException(status_code=400, detail="input_sequences must not be empty")

    if request.execution_mode == "external_smoke" and request.external_smoke_mode == "approved_smoke":
        if not request.approved:
            raise HTTPException(status_code=403, detail="approved=true is required for approved_smoke")
        if not (request.approved_by or "").strip():
            raise HTTPException(status_code=400, detail="approved_by is required for approved_smoke")

    try:
        task = task_manager.create_pipeline_task(request)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")  # type: ignore[return-value]

    if request.execution_mode == "external_smoke" and request.external_smoke_mode == "approved_smoke":
        approval = mock_store.add_approval(
            task.id,
            approved=True,
            approved_by=(request.approved_by or "").strip(),
            safety_flags={
                "rawdata_read_only": True,
                "no_dparsf_blackbox": True,
                "matlab_external_execution": True,
            },
        )
        mock_store.append_task_event(
            task.id,
            status=task.status,
            progress=task.progress,
            message=f"Run-level approval recorded by {approval.approved_by}",
            source="approval_gate",
            metadata={"approval_id": approval.approval_id},
        )
    asyncio.create_task(run_pipeline_task(task.id, request, task_manager))
    return {"task_id": task.id, "status": task.status}


# Assistant chat


@router.post(
    "/api/assistant/chat",
    response_model=dict[str, object],
)
def assistant_chat(
    request: AssistantChatRequest,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    from src.backend.app.services.mock_store import mock_store

    project = mock_store.get_project(request.project_id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")

    message = request.message.lower()
    dataset = mock_store.get_dataset_summary(request.project_id)
    if "pipeline" in message or "workflow" in message:
        reply = (
            f"Current pipeline is {project.current_pipeline_id}. Use approved runs for SPM/DPABI "
            "steps and keep rawdata read-only. The UI can start a simulated run now; real runners "
            "should plug into the same task event stream."
        )
    elif "failed" in message or "error" in message or "log" in message:
        reply = (
            "For failed tasks, open the latest task detail and inspect logs/result_path first. "
            "If it is an external SPM/DPABI smoke failure, verify the MATLAB stdout/stderr and "
            "expected result JSON path."
        )
    elif "dataset" in message or "data" in message:
        reply = (
            f"{project.name} currently has {dataset.subjects if dataset else project.subjects_count} subjects, "
            f"{dataset.scans if dataset else project.scans_count} scans, and health status "
            f"{dataset.health_status if dataset else 'Unknown'}."
        )
    else:
        reply = (
            "I can help review dataset readiness, explain pipeline settings, summarize task failures, "
            "or prepare the next auditable SPM/DPABI smoke run. TODO: connect this panel to a real LLM provider."
        )
    return {"reply": reply}
