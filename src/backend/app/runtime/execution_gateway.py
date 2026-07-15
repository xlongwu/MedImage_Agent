"""The sole production dispatch boundary for reviewed pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from src.backend.app.core.exceptions import SafetyError
from src.backend.app.planner.audit_record import stable_hash
from src.backend.app.runtime.node_contract_registry import executable_contract_versions
from src.backend.app.schemas.execution_ticket import ExecutionTicket
from src.backend.app.services.execution_ticket_service import ExecutionTicketService


_VERIFICATION_SENTINEL = object()


def _default_pipeline_executor(**kwargs: Any) -> dict[str, Any]:
    from src.backend.app.runtime.pipeline_executor import run_pipeline

    return run_pipeline(**kwargs)


PIPELINE_EXECUTOR: Callable[..., dict[str, Any]] = _default_pipeline_executor


def current_safe_allowlist_fingerprint() -> str:
    """Fingerprint the executable registry so issued authority expires on drift."""
    return stable_hash({
        "policy_version": 2,
        "contracts": executable_contract_versions(),
    })


@dataclass(frozen=True)
class VerifiedExecutionContext:
    ticket: ExecutionTicket
    ticket_service: ExecutionTicketService
    verified_project_config_path: str
    verified_pipeline_path: str
    verification_id: str
    _sentinel: object = field(repr=False, compare=False)


def assert_verified_execution_context(context: VerifiedExecutionContext | None) -> None:
    if not isinstance(context, VerifiedExecutionContext) or context._sentinel is not _VERIFICATION_SENTINEL:
        raise SafetyError(
            "VERIFIED_EXECUTION_CONTEXT_REQUIRED",
            code="VERIFIED_EXECUTION_CONTEXT_REQUIRED",
        )


class ExecutionGateway:
    def __init__(self, ticket_service: ExecutionTicketService) -> None:
        self.ticket_service = ticket_service

    def dispatch(
        self,
        *,
        execution_ticket_id: str,
        project_id: str,
        reviewed_plan_id: str,
        plan_hash: str,
        approval_context_id: str,
        normalized_params_hash: str,
        contract_versions: dict[str, str] | tuple[tuple[str, str], ...],
        project_config_path: str,
        pipeline_path: str,
        goal_contract_hash: str | None = None,
        evaluation_policy_version: str | None = None,
        executor: Callable[..., dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], ExecutionTicket]:
        fingerprint = current_safe_allowlist_fingerprint()
        ticket = self.ticket_service.validate(
            execution_ticket_id,
            project_id=project_id,
            reviewed_plan_id=reviewed_plan_id,
            plan_hash=plan_hash,
            approval_context_id=approval_context_id,
            safe_allowlist_fingerprint=fingerprint,
            normalized_params_hash=normalized_params_hash,
            contract_versions=contract_versions,
            project_config_path=project_config_path,
            pipeline_path=pipeline_path,
            goal_contract_hash=goal_contract_hash,
            evaluation_policy_version=evaluation_policy_version,
        )
        consumed = self.ticket_service.consume(
            ticket,
            idempotency_key=stable_hash(
                {
                    "ticket_id": ticket.execution_ticket_id,
                    "pipeline_path": str(Path(pipeline_path).resolve()),
                }
            ),
        )
        context = VerifiedExecutionContext(
            ticket=consumed,
            ticket_service=self.ticket_service,
            verified_project_config_path=str(Path(project_config_path).resolve()),
            verified_pipeline_path=str(Path(pipeline_path).resolve()),
            verification_id=f"verification_{uuid4().hex}",
            _sentinel=_VERIFICATION_SENTINEL,
        )
        if executor is None:
            executor = PIPELINE_EXECUTOR
        result = executor(
            project_config_path=project_config_path,
            pipeline_path=pipeline_path,
            execution_context=context,
        )
        return result, consumed
