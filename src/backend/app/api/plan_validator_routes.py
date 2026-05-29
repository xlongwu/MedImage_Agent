"""Plan Validator API — POST /api/plans/validate."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.backend.app.planner.plan_validator import validate_plan

router = APIRouter()


class PlanValidateRequest(BaseModel):
    plan: dict[str, Any]


@router.post("/api/plans/validate")
def api_validate_plan(request: PlanValidateRequest) -> dict[str, Any]:
    """Validate a candidate pipeline plan.

    Returns PlanValidationResult.to_dict().  Validation errors are
    returned in the response body (HTTP 200) — only malformed request
    bodies trigger HTTP 422 from FastAPI.
    """
    return validate_plan(request.plan).to_dict()
