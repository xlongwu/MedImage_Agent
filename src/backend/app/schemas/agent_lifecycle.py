"""Versioned persisted state for the controlled Agent workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.backend.app.schemas.observation import ObservationSummary
from src.backend.app.schemas.goal_contract import GoalEvaluationSummary
from src.backend.app.schemas.recovery import DiagnosisSummary, RecoveryProposalSummary


AgentLifecycleState = Literal[
    "CREATED",
    "CONTEXT_READY",
    "PLAN_DRAFTED",
    "PLAN_VALIDATED",
    "WAITING_FOR_APPROVAL",
    "APPROVED",
    "EXECUTION_READY",
    "RUNNING",
    "OBSERVING",
    "EVALUATING",
    "GOAL_SATISFIED",
    "SUCCEEDED",
    "FAILED",
    "DIAGNOSING",
    "RETRY_PROPOSED",
    "WAITING_FOR_RETRY_APPROVAL",
    "RETRYING",
    "RECOVERY_PROPOSED",
    "WAITING_FOR_RECOVERY_APPROVAL",
    "RECOVERY_READY",
    "RECOVERING",
    "HUMAN_HANDOFF",
]


class LifecycleObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary_status: str
    node_states_consistent: bool = False
    artifacts_reloadable: bool = False
    numerical_artifacts_present: bool = False
    capability_level: str = "unavailable"
    warnings: tuple[str, ...] = ()
    evidence: dict[str, Any] = Field(default_factory=dict)

    @property
    def supports_success(self) -> bool:
        return (
            self.summary_status.upper() in {"SUCCESS", "COMPLETED"}
            and self.node_states_consistent
            and self.artifacts_reloadable
            and self.capability_level in {"computed", "validated"}
        )


class RetryProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_id: str
    node_ids: tuple[str, ...]
    backend_ids: tuple[str, ...]
    parameter_hash: str
    input_roots: tuple[str, ...]
    output_roots: tuple[str, ...]
    classifier: str
    risk: Literal["low", "high", "unknown"] = "unknown"
    requires_approval: bool = True
    changes_reviewed_contract: bool = False


class AgentLifecycleRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 2
    lifecycle_id: str
    project_id: str
    state: AgentLifecycleState = "CREATED"
    reviewed_plan_id: str | None = None
    execution_ticket_id: str | None = None
    parent_execution_ticket_id: str | None = None
    audit_id: str | None = None
    run_id: str | None = None
    parent_run_id: str | None = None
    goal_contract_id: str | None = None
    goal_contract_hash: str | None = None
    goal_evaluation_id: str | None = None
    goal_evaluation_summary: GoalEvaluationSummary | None = None
    diagnosis_id: str | None = None
    diagnosis_summary: DiagnosisSummary | None = None
    recovery_proposal_id: str | None = None
    recovery_proposal_summary: RecoveryProposalSummary | None = None
    recovery_approval_id: str | None = None
    recovery_attempt_id: str | None = None
    retry_count: int = 0
    retry_quota: int = 0
    observation_id: str | None = None
    observation_summary: ObservationSummary | None = None
    # v1 compatibility only. New commands never accept or persist this field.
    observation: LifecycleObservation | None = None
    legacy_observation_needs_review: bool = False
    retry_proposal: RetryProposal | None = None
    last_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_command_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def mark_legacy_observation_unverified(cls, value: Any) -> Any:
        if isinstance(value, dict) and value.get("observation") and not value.get("observation_id"):
            value = dict(value)
            value["legacy_observation_needs_review"] = True
        return value


class AgentLifecycleEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    event_id: str
    lifecycle_id: str
    project_id: str
    command_id: str
    actor: str
    source_command: str
    occurred_at: datetime
    from_state: AgentLifecycleState | None
    to_state: AgentLifecycleState
    reviewed_plan_id: str | None = None
    execution_ticket_id: str | None = None
    recovery_approval_id: str | None = None
    recovery_attempt_id: str | None = None
    audit_id: str | None = None
    run_id: str | None = None
    observation_id: str | None = None
    goal_contract_id: str | None = None
    goal_evaluation_id: str | None = None
    diagnosis_id: str | None = None
    recovery_proposal_id: str | None = None
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class LifecycleCommand(BaseModel):
    command_id: str
    action: str
    actor: str
    reason: str | None = None
    reviewed_plan_id: str | None = None
    execution_ticket_id: str | None = None
    audit_id: str | None = None
    run_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class LifecycleCreateRequest(BaseModel):
    command_id: str
    actor: str
