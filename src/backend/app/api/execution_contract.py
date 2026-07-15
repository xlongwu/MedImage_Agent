"""Stable refusal for public execution surfaces that lack reviewed authority."""

from __future__ import annotations

from fastapi import HTTPException

from src.backend.app.services import mock_store as store_module
from src.backend.app.services.execution_ticket_service import ExecutionTicketService


def reject_execution_contract(
    entry_id: str,
    *,
    project_id: str = "unscoped",
    replacement: str = "/api/plans/execute-reviewed",
) -> None:
    service = ExecutionTicketService(store_module.mock_store)
    event = service.record_rejection(
        project_id=project_id or "unscoped",
        reason="EXECUTION_CONTRACT_REQUIRED",
        details={"entry_id": entry_id, "replacement": replacement},
    )
    raise HTTPException(
        status_code=410,
        detail={
            "ok": False,
            "status": "EXECUTION_CONTRACT_REQUIRED",
            "error_code": "EXECUTION_CONTRACT_REQUIRED",
            "entry_id": entry_id,
            "replacement": replacement,
            "audit_event_id": event.event_id,
        },
    )
