"""LLM Planner API — POST /api/planner/plan-from-goal."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.backend.app.planner.llm_planner import generate_plan_from_goal

router = APIRouter()


class PlanFromGoalRequest(BaseModel):
    goal: str
    provider: str = "mock"
    project_config_path: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


@router.post("/api/planner/plan-from-goal")
def api_plan_from_goal(request: PlanFromGoalRequest) -> dict[str, Any]:
    """Generate a candidate pipeline plan from a natural-language goal.

    Returns PlannerResponse.to_dict().  Business errors (empty goal,
    unsupported goal, unsupported provider) are returned as HTTP 200
    with ok=false.  Only malformed request bodies trigger HTTP 422.
    """
    return generate_plan_from_goal(
        goal=request.goal,
        provider=request.provider,
        constraints=request.constraints,
        project_config_path=request.project_config_path,
    ).to_dict()
