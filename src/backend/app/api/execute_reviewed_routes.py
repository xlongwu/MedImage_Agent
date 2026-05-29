"""Execute Reviewed Plan API — dry-run only (POST /api/plans/execute-reviewed).

This endpoint validates that a reviewed plan would be allowed to execute,
but NEVER calls pipeline_executor.  It re-runs Plan Validator and
Approval Gate internally — front-end submitted validation is NOT trusted.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.backend.app.planner.approval_gate import check_approval_gate
from src.backend.app.planner.plan_validator import validate_plan

router = APIRouter()


class ExecuteReviewedRequest(BaseModel):
    plan: dict[str, Any]
    approval: dict[str, Any] | None = None
    project_config_path: str | None = None
    dry_run: bool = True


def _plan_summary(plan: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    nodes = plan.get("nodes", []) or []
    return {
        "pipeline_id": plan.get("pipeline_id", "unknown"),
        "nodes_total": len(nodes),
        "approval_required_nodes": validation.get("approval_required_nodes", []),
        "high_risk_nodes": validation.get("high_risk_nodes", []),
    }


def _execution_meta(submitted: bool = False, run_id: str | None = None) -> dict[str, Any]:
    return {
        "submitted": submitted,
        "run_id": run_id,
        "executor_called": False,
    }


@router.post("/api/plans/execute-reviewed")
def api_execute_reviewed(request: ExecuteReviewedRequest) -> dict[str, Any]:
    """Dry-run check: validate a reviewed plan without executing it.

    Currently only dry_run=True is supported.  The endpoint re-runs
    Plan Validator and Approval Gate — it does NOT trust any validation
    submitted by the front end.
    """
    # ── Dry-run guard ──
    if request.dry_run is not True:
        return {
            "ok": False,
            "status": "DRY_RUN_ONLY",
            "dry_run": request.dry_run,
            "would_execute": False,
            "execution_allowed": False,
            "validation": None,
            "approval_gate": None,
            "plan_summary": None,
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }

    # ── 1. Re-validate plan (backend-owned, never trust front-end) ──
    plan = request.plan
    validation = validate_plan(plan).to_dict()

    if not validation.get("ok"):
        return {
            "ok": False,
            "status": "VALIDATION_FAILED",
            "dry_run": True,
            "would_execute": False,
            "execution_allowed": False,
            "validation": validation,
            "approval_gate": None,
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }

    # ── 2. Re-check approval gate ──
    gate = check_approval_gate(plan, validation, request.approval).to_dict()

    if not gate.get("execution_allowed"):
        return {
            "ok": False,
            "status": "APPROVAL_GATE_BLOCKED",
            "dry_run": True,
            "would_execute": False,
            "execution_allowed": False,
            "validation": validation,
            "approval_gate": gate,
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }

    # ── 3. Dry-run OK (but never executor) ──
    return {
        "ok": True,
        "status": "DRY_RUN_OK",
        "dry_run": True,
        "would_execute": True,
        "execution_allowed": True,
        "validation": validation,
        "approval_gate": gate,
        "plan_summary": _plan_summary(plan, validation),
        "project_config_path": request.project_config_path,
        "execution": _execution_meta(),
    }
