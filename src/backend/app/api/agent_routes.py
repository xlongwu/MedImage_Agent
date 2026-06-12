"""Agent runtime, retry, and scheduler route handlers.

Extracted from routes.py for domain cohesion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.backend.app.api._errors import raise_api_error
from src.backend.app.api._shared import (
    _load_project_config,
    _read_json_if_exists,
    _read_text_if_exists,
)
from src.backend.app.api.models import (
    AgentExecuteRequest,
    AgentPlanRequest,
    RetryDryRunRequest,
    RetryExecuteRequest,
    SchedulerPlanRequest,
)
from src.backend.app.runtime.agent_runtime import (
    run_orchestrator_execute,
    run_orchestrator_plan,
)
from src.backend.app.runtime.error_diagnoser import diagnose_run
from src.backend.app.runtime.retry_runtime import (
    dry_run_retry_plan,
    execute_retry_plan,
)
from src.backend.app.runtime.run_inspector import (
    inspect_run,
    list_available_runs,
    read_state_detail,
)
from src.backend.app.runtime.scheduler import create_scheduler_plan
from src.backend.app.schemas.pipeline_schema import load_pipeline_yaml
from src.backend.app.runtime.path_safety import (
    PathSafetyError,
    read_safe_text_file,
)

router = APIRouter()


# ── Agent plan / execute ──────────────────────────────────────────────────

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

    plan_path = Path("outputs/work") / "agent_runs" / request.agent_run_id / "plan.json"

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

    base = Path("outputs/work") / "agent_runs" / agent_run_id

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


# ── Run inspection ────────────────────────────────────────────────────────

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


@router.get("/api/runs/{run_id}/diagnosis")
def api_diagnose_run(run_id: str) -> dict[str, Any]:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")

    result = diagnose_run(run_id=run_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


# ── Retry ─────────────────────────────────────────────────────────────────

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

    base = Path("outputs/work") / "retry_runs" / retry_run_id

    dry_run_summary = _read_json_if_exists(base / "dry_run_summary.json")
    retry_execution_summary = _read_json_if_exists(base / "retry_execution_summary.json")

    return {
        "ok": True,
        "retry_run_id": retry_run_id,
        "dry_run_summary": dry_run_summary,
        "retry_execution_summary": retry_execution_summary,
    }


# ── Scheduler ─────────────────────────────────────────────────────────────

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
        raise_api_error(exc)
