"""Controlled recovery approval, reservation, child-attempt, and event ledger."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.app.schemas.recovery import (
    ApprovalClass,
    RecoveryAction,
    RecoveryQuotaDecision,
)

RecoveryApprovalMode = Literal[
    "within_original_approval",
    "explicit_retry_approval",
    "new_plan_approval",
    "not_executable",
]
RecoveryApprovalStatus = Literal["active", "revoked", "expired"]
RecoveryAttemptStatus = Literal[
    "PROPOSED",
    "APPROVED",
    "TICKET_ISSUED",
    "RUNNING",
    "EXECUTION_SUCCEEDED",
    "EXECUTION_FAILED",
    "OBSERVED",
    "EVALUATED",
    "REPLAN_CREATED",
    "HANDOFF",
]
QuotaReservationStatus = Literal["reserved", "consumed", "released"]


class RecoveryApprovalRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    recovery_approval_id: str
    schema_version: Literal[1] = 1
    project_id: str
    lifecycle_id: str
    recovery_proposal_id: str
    recovery_proposal_hash: str
    candidate_id: str
    candidate_hash: str
    action: RecoveryAction
    target_node_ids: tuple[str, ...] = ()
    target_subject_ids: tuple[str, ...] = ()
    parent_reviewed_plan_id: str
    parent_plan_hash: str
    goal_contract_hash: str
    parent_execution_ticket_id: str
    parent_ticket_hash: str
    parent_run_id: str
    quota_snapshot: RecoveryQuotaDecision
    proposal_approval_class: ApprovalClass
    approval_mode: RecoveryApprovalMode
    approved_actor: str
    approved_at: datetime
    expires_at: datetime
    command_id: str
    idempotency_key: str
    audit_id: str
    status: RecoveryApprovalStatus = "active"
    recovery_approval_hash: str


class RecoveryApprovalEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    recovery_approval_id: str
    project_id: str
    event_type: Literal["approved", "revoked", "expired", "rejected"]
    occurred_at: datetime
    actor: str
    command_id: str
    reason_code: str | None = None
    audit_id: str


class RecoveryQuotaReservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reservation_id: str
    schema_version: Literal[1] = 1
    project_id: str
    lifecycle_id: str
    recovery_proposal_id: str
    candidate_id: str
    recovery_attempt_id: str
    action: RecoveryAction
    node_ids: tuple[str, ...] = ()
    subject_ids: tuple[str, ...] = ()
    reserves_replan: bool = False
    reserved_wall_seconds: int = Field(default=0, ge=0)
    effective_limits: dict[str, int]
    status: QuotaReservationStatus = "reserved"
    created_at: datetime
    consumed_at: datetime | None = None
    released_at: datetime | None = None
    reservation_hash: str


class RecoveryAttemptRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    recovery_attempt_id: str
    schema_version: Literal[1] = 1
    project_id: str
    lifecycle_id: str
    recovery_proposal_id: str
    recovery_proposal_hash: str
    candidate_id: str
    candidate_hash: str
    action: RecoveryAction
    target_node_ids: tuple[str, ...] = ()
    target_subject_ids: tuple[str, ...] = ()
    checkpoint_id: str | None = None
    parent_reviewed_plan_id: str
    parent_plan_hash: str
    goal_contract_hash: str
    parent_execution_ticket_id: str
    parent_ticket_hash: str
    parent_run_id: str
    recovery_approval_id: str | None = None
    quota_reservation_id: str | None = None
    child_execution_ticket_id: str | None = None
    child_ticket_hash: str | None = None
    recovery_run_id: str
    output_namespace: str
    status: RecoveryAttemptStatus = "PROPOSED"
    audit_id: str
    command_id: str
    idempotency_key: str
    execution_status: str | None = None
    observation_id: str | None = None
    goal_evaluation_id: str | None = None
    goal_evaluation_status: str | None = None
    error_codes: tuple[str, ...] = ()
    handoff_reasons: tuple[str, ...] = ()
    prior_recovery_attempt_ids: tuple[str, ...] = ()
    remaining_goal_gap_ids: tuple[str, ...] = ()
    safe_human_actions: tuple[str, ...] = ()
    created_at: datetime
    updated_at: datetime
    dispatch_started_at: datetime | None = None
    dispatch_completed_at: datetime | None = None
    recovery_attempt_hash: str


class RecoveryAttemptEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    recovery_attempt_id: str
    project_id: str
    lifecycle_id: str
    command_id: str
    event_type: str
    from_status: RecoveryAttemptStatus | None
    to_status: RecoveryAttemptStatus
    occurred_at: datetime
    audit_id: str
    reason_code: str | None = None
    attempt_hash: str
