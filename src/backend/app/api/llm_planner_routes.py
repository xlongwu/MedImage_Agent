"""LLM Planner API — POST /api/planner/plan-from-goal."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.backend.app.planner.llm_planner import generate_plan_from_goal
from src.backend.app.planner.plan_validator import validate_plan
from src.backend.app.planner.project_context import (
    ProjectContextError,
    apply_project_context_to_plan,
    load_project_context,
)

router = APIRouter()


class PlanFromGoalRequest(BaseModel):
    goal: str
    provider: str = "mock"
    project_id: str | None = None
    project_config_path: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


def _context_error_response(
    request: PlanFromGoalRequest,
    error: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "provider": request.provider,
        "goal": request.goal,
        "plan": {},
        "validation": {},
        "messages": [],
        "warnings": [],
        "errors": [error],
        "project_context": None,
    }


@router.post("/api/planner/plan-from-goal")
def api_plan_from_goal(request: PlanFromGoalRequest) -> dict[str, Any]:
    """Generate a candidate pipeline plan from a natural-language goal.

    Returns PlannerResponse.to_dict().  Business errors (empty goal,
    unsupported goal, unsupported provider) are returned as HTTP 200
    with ok=false.  Only malformed request bodies trigger HTTP 422.
    """
    if not request.project_id and not request.project_config_path:
        return _context_error_response(
            request,
            "PROJECT_CONTEXT_REQUIRED: select a project or provide an explicit project_config_path",
        )

    try:
        context = load_project_context(
            project_id=request.project_id,
            project_config_path=request.project_config_path,
        )
    except ProjectContextError as exc:
        return _context_error_response(request, str(exc))

    result = generate_plan_from_goal(
        goal=request.goal,
        provider=request.provider,
        constraints=request.constraints,
        project_config_path=request.project_config_path,
    ).to_dict()

    result["project_context"] = context.to_dict()
    if not result.get("ok") or not isinstance(result.get("plan"), dict):
        return result

    try:
        plan = apply_project_context_to_plan(result["plan"], context)
    except ProjectContextError as exc:
        result["ok"] = False
        result["plan"] = {}
        result["validation"] = {}
        result["errors"] = [*result.get("errors", []), str(exc)]
        return result

    validation = validate_plan(plan).to_dict()
    result["plan"] = plan
    result["validation"] = validation
    result["ok"] = bool(validation.get("ok"))
    result["warnings"] = [
        *result.get("warnings", []),
        "Project context was applied before plan review.",
    ]
    return result
