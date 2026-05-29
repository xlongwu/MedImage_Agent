from __future__ import annotations

import asyncio
from typing import Any

from src.backend.app.schemas.desktop import PipelineRunRequest
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.task_manager import TaskManager


async def run_pipeline_simulation(
    task_id: str,
    request: PipelineRunRequest,
    manager: TaskManager,
) -> None:
    """Simulate a non-blocking pipeline run.

    TODO: Replace each step with real Python/SPM/DPABI command execution while
    preserving task events, audit logs, and read-only rawdata guarantees.
    """

    steps = [
        (8, "Preparing input manifest"),
        (24, "Validating sequences and project constraints"),
        (42, f"Running {request.pipeline_id} planning stage"),
        (65, "Running brain tumor segmentation..."),
        (82, "Computing QC metrics and report artifacts"),
        (100, "Pipeline completed successfully"),
    ]

    try:
        for progress, message in steps:
            await asyncio.sleep(0.55)
            status = "completed" if progress == 100 else "running"
            result_path = (
                f"outputs/results/{request.project_id}/{task_id}/report.html"
                if status == "completed"
                else None
            )
            await manager.update_task(
                task_id,
                status=status,
                progress=progress,
                message=message,
                result_path=result_path,
            )
    except Exception as exc:
        await manager.update_task(
            task_id,
            status="failed",
            progress=0,
            message=f"Pipeline failed: {exc}",
        )


async def run_pipeline_task(task_id: str, request: PipelineRunRequest, manager: TaskManager) -> None:
    if request.execution_mode == "external_smoke":
        await run_external_smoke_package(task_id, request, manager)
    elif request.execution_mode == "rsfmri_python":
        await run_rsfmri_python_quickstart(task_id, request, manager)
    else:
        await run_pipeline_simulation(task_id, request, manager)


async def run_external_smoke_package(
    task_id: str,
    request: PipelineRunRequest,
    manager: TaskManager,
) -> None:
    """Generate or run an auditable SPM/DPABI smoke package."""

    try:
        if request.external_smoke_mode == "approved_smoke" and not _has_run_level_approval(task_id, request):
            await manager.update_task(
                task_id,
                status="failed",
                progress=0,
                message="Approved external smoke blocked: missing run-level approval",
                source="approval_gate",
                metadata={"external_smoke_mode": request.external_smoke_mode},
            )
            return

        await manager.update_task(
            task_id,
            status="running",
            progress=10,
            message=(
                "Starting approved external smoke run"
                if request.external_smoke_mode == "approved_smoke"
                else "Preparing external smoke manual package"
            ),
            source="external_smoke",
            metadata={"external_smoke_mode": request.external_smoke_mode},
        )
        result: dict[str, Any] = await asyncio.to_thread(
            _run_external_smoke,
            request,
        )
        _save_external_smoke_artifacts(task_id, result)
        result_path = str(result.get("artifacts", {}).get("result_json", "outputs/reports/external_smoke"))
        warning_count = len(result.get("warnings", []) or [])
        error_count = len(result.get("errors", []) or [])
        message = (
            "Approved external smoke completed"
            if request.external_smoke_mode == "approved_smoke" and not error_count
            else "External smoke package generated"
            if not error_count
            else f"External smoke diagnostics found {error_count} issue(s)"
        )
        if warning_count:
            message = f"{message}; {warning_count} warning(s)"
        await manager.update_task(
            task_id,
            status="completed" if not error_count else "failed",
            progress=100 if not error_count else 75,
            message=message,
            result_path=result_path,
            source="external_smoke",
            metadata={
                "external_smoke_mode": request.external_smoke_mode,
                "warning_count": warning_count,
                "error_count": error_count,
                "artifacts": result.get("artifacts", {}),
            },
        )
    except Exception as exc:
        await manager.update_task(
            task_id,
            status="failed",
            progress=20,
            message=f"External smoke package failed: {exc}",
            source="external_smoke",
            metadata={"external_smoke_mode": request.external_smoke_mode},
        )


async def run_rsfmri_python_quickstart(
    task_id: str,
    request: PipelineRunRequest,
    manager: TaskManager,
) -> None:
    """Run the existing synthetic rs-fMRI Python quickstart adapter."""

    try:
        await manager.update_task(
            task_id,
            status="running",
            progress=12,
            message="Starting synthetic rs-fMRI Python quickstart",
        )
        await manager.update_task(
            task_id,
            status="running",
            progress=38,
            message="Generating synthetic BIDS and QC inputs",
        )
        exit_code = await asyncio.to_thread(_run_quickstart_demo)
        result_path = "outputs/demo_runs"
        if exit_code == 0:
            await manager.update_task(
                task_id,
                status="completed",
                progress=100,
                message="Synthetic rs-fMRI Python quickstart completed",
                result_path=result_path,
            )
        else:
            await manager.update_task(
                task_id,
                status="failed",
                progress=72,
                message=f"Synthetic rs-fMRI quickstart exited with code {exit_code}",
                result_path=result_path,
            )
    except Exception as exc:
        await manager.update_task(
            task_id,
            status="failed",
            progress=35,
            message=f"Synthetic rs-fMRI quickstart failed: {exc}",
        )


def _run_external_smoke(request: PipelineRunRequest) -> dict[str, Any]:
    from src.backend.app.tools.external_smoke import run_external_smoke

    return run_external_smoke(
        target="all",
        mode=request.external_smoke_mode,
        config_path="examples/project_config.yaml",
        approve=request.approved,
        approved_by=request.approved_by or "desktop-runtime",
        dpabi_function=request.dpabi_function,
    )


def _run_quickstart_demo() -> int:
    from src.backend.app.tools.run_quickstart_demo_cli import main

    return int(main())


def _has_run_level_approval(task_id: str, request: PipelineRunRequest) -> bool:
    approval = mock_store.get_latest_approval(task_id)
    return bool(request.approved and request.approved_by and approval and approval.approved)


def _save_external_smoke_artifacts(task_id: str, result: dict[str, Any]) -> None:
    mock_store.save_task_artifacts(
        task_id,
        {
            "ok": result.get("ok", False),
            "target": result.get("target"),
            "mode": result.get("mode"),
            "artifacts": result.get("artifacts", {}),
            "external_tool_results": result.get("external_tool_results", []),
            "checks": result.get("checks", []),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "next_actions": result.get("next_actions", []),
        },
    )
