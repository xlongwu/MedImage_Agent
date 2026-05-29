"""Execute Reviewed Plan API — dry-run only (POST /api/plans/execute-reviewed).

This endpoint validates that a reviewed plan would be allowed to execute,
but NEVER calls pipeline_executor.  It re-runs Plan Validator, Approval
Gate, and Plan Adapter internally — front-end submitted validation is
NOT trusted.

When persist_audit=true, an audit record is atomically written for
traceability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.backend.app.planner.approval_gate import check_approval_gate
from src.backend.app.planner.audit_record import build_review_audit_record, write_audit_record
from src.backend.app.planner.plan_adapter import adapt_reviewed_plan
from src.backend.app.planner.plan_validator import validate_plan

router = APIRouter()

AUDIT_RECORD_DIR = Path("outputs/reports/audit_records")


class ExecuteReviewedRequest(BaseModel):
    plan: dict[str, Any]
    approval: dict[str, Any] | None = None
    project_config_path: str | None = None
    dry_run: bool = True
    persist_audit: bool = False
    actor: str | None = None


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


def _no_audit() -> dict[str, Any]:
    return {"persisted": False}


def _adapter_summary(adapter_result: Any) -> dict[str, Any]:
    """Build a compact adapter summary for the response."""
    if adapter_result is None:
        return {"ok": False, "errors": [], "warnings": [], "policy": {}, "pipeline": {"available": False}}
    pipeline = adapter_result.pipeline
    return {
        "ok": adapter_result.ok,
        "errors": adapter_result.errors,
        "warnings": adapter_result.warnings,
        "policy": adapter_result.policy,
        "pipeline": {
            "available": adapter_result.ok and pipeline is not None,
            "name": pipeline.get("pipeline_id", "unknown") if pipeline else "unknown",
            "nodes_total": len(pipeline.get("nodes", [])) if pipeline else 0,
            "modality": pipeline.get("modality", "rsfmri") if pipeline else "rsfmri",
        } if adapter_result.ok and pipeline else {"available": False},
    }


def _is_policy_blocked(policy: dict[str, list[str]]) -> bool:
    blocked = (policy.get("blocked_spm_nodes", []) +
               policy.get("blocked_dpabi_execution_nodes", []) +
               policy.get("blocked_gui_nodes", []) +
               policy.get("blocked_manual_required_nodes", []) +
               policy.get("blocked_unknown_nodes", []) +
               policy.get("blocked_uncataloged_nodes", []))
    return len(blocked) > 0


def _write_audit(
    event_type: str,
    plan: dict[str, Any],
    validation: dict[str, Any],
    approval: dict[str, Any] | None,
    gate: dict[str, Any] | None,
    dry_run_result: dict[str, Any] | None,
    actor: str | None,
    request: ExecuteReviewedRequest,
) -> dict[str, Any]:
    if not request.persist_audit:
        return _no_audit()
    try:
        record = build_review_audit_record(
            event_type=event_type,
            plan=plan,
            validation=validation,
            approval=approval,
            approval_gate=gate,
            dry_run_result=dry_run_result,
            actor=actor or request.actor,
            source="execute_reviewed_api",
        )
        path = write_audit_record(record, AUDIT_RECORD_DIR)
        return {
            "persisted": True,
            "audit_id": record.audit_id,
            "audit_path": str(path),
            "event_type": event_type,
        }
    except Exception:
        return {"persisted": False, "error": "Failed to write audit record"}


def _blocked_result(
    status: str,
    plan: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any] | None,
    adapter: Any,
    request: ExecuteReviewedRequest,
) -> dict[str, Any]:
    result = {
        "ok": False,
        "status": status,
        "dry_run": True,
        "would_execute": False,
        "execution_allowed": False,
        "validation": validation,
        "approval_gate": gate,
        "adapter": _adapter_summary(adapter),
        "project_config_path": request.project_config_path,
        "execution": _execution_meta(),
    }
    result["audit"] = _write_audit(
        "execution_blocked", plan, validation, request.approval,
        gate, result, request.actor, request,
    )
    return result


@router.post("/api/plans/execute-reviewed")
def api_execute_reviewed(request: ExecuteReviewedRequest) -> dict[str, Any]:
    """Dry-run check: validate a reviewed plan without executing it.

    Currently only dry_run=True is supported.  The endpoint re-runs
    Plan Validator, Approval Gate, and Plan Adapter — it does NOT trust
    any validation submitted by the front end.
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
            "adapter": None,
            "plan_summary": None,
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
            "audit": _no_audit(),
        }

    # ── 1. Re-validate plan (backend-owned, never trust front-end) ──
    plan = request.plan
    validation = validate_plan(plan).to_dict()

    if not validation.get("ok"):
        result = {
            "ok": False,
            "status": "VALIDATION_FAILED",
            "dry_run": True,
            "would_execute": False,
            "execution_allowed": False,
            "validation": validation,
            "approval_gate": None,
            "adapter": None,
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }
        result["audit"] = _write_audit(
            "execution_blocked", plan, validation, request.approval,
            None, result, request.actor, request,
        )
        return result

    # ── 2. Re-check approval gate ──
    gate = check_approval_gate(plan, validation, request.approval).to_dict()

    if not gate.get("execution_allowed"):
        result = {
            "ok": False,
            "status": "APPROVAL_GATE_BLOCKED",
            "dry_run": True,
            "would_execute": False,
            "execution_allowed": False,
            "validation": validation,
            "approval_gate": gate,
            "adapter": None,
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }
        result["audit"] = _write_audit(
            "execution_blocked", plan, validation, request.approval,
            gate, result, request.actor, request,
        )
        return result

    # ── 3. Plan adapter check ──
    adapter = adapt_reviewed_plan(plan)

    if not adapter.ok:
        return _blocked_result("PLAN_ADAPTER_FAILED", plan, validation, gate, adapter, request)

    if _is_policy_blocked(adapter.policy):
        return _blocked_result("EXECUTION_POLICY_BLOCKED", plan, validation, gate, adapter, request)

    # ── 4. Dry-run OK (but never executor) ──
    result = {
        "ok": True,
        "status": "DRY_RUN_OK",
        "dry_run": True,
        "would_execute": True,
        "execution_allowed": True,
        "validation": validation,
        "approval_gate": gate,
        "adapter": _adapter_summary(adapter),
        "plan_summary": _plan_summary(plan, validation),
        "project_config_path": request.project_config_path,
        "execution": _execution_meta(),
    }
    result["audit"] = _write_audit(
        "dry_run_checked", plan, validation, request.approval,
        gate, result, request.actor, request,
    )
    return result
