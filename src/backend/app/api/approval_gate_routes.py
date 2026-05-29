"""Approval Gate API — POST /api/approval/check."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.backend.app.planner.approval_gate import check_approval_gate

router = APIRouter()


class ApprovalCheckRequest(BaseModel):
    plan: dict[str, Any]
    validation: dict[str, Any]
    approval: dict[str, Any] | None = None


@router.post("/api/approval/check")
def api_approval_check(request: ApprovalCheckRequest) -> dict[str, Any]:
    """Check whether a plan may proceed to execution given its validation
    and approval state.

    Returns ApprovalGateResult.to_dict().  Business errors (missing
    validation, missing approval, rejected nodes) are returned as
    HTTP 200 with execution_allowed=false.
    """
    return check_approval_gate(
        plan=request.plan,
        validation=request.validation,
        approval=request.approval,
    ).to_dict()
