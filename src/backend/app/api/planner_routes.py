from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.backend.app.api._errors import raise_api_error
from src.backend.app.api.models import (
    PlannerDraftRequest,
    PlannerExecuteRequest,
    PlannerValidateRequest,
)
from src.backend.app.planner import (
    draft_pipeline_plan,
    execute_pipeline_plan,
    get_planner_history,
    validate_pipeline_plan,
)

router = APIRouter()


@router.post("/api/planner/draft")
def api_planner_draft(request: PlannerDraftRequest) -> dict[str, Any]:
    try:
        return draft_pipeline_plan(request.model_dump())
    except Exception as exc:
        raise_api_error(exc)


@router.post("/api/planner/validate")
def api_planner_validate(request: PlannerValidateRequest) -> dict[str, Any]:
    try:
        result = validate_pipeline_plan(request.model_dump())
    except Exception as exc:
        raise_api_error(exc)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/planner/execute")
def api_planner_execute(request: PlannerExecuteRequest) -> dict[str, Any]:
    try:
        result = execute_pipeline_plan(request.model_dump())
    except Exception as exc:
        raise_api_error(exc)
    if result.get("status") == "APPROVAL_REQUIRED":
        raise HTTPException(status_code=403, detail=result)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/planner/history")
def api_planner_history(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    return get_planner_history(limit=limit)
