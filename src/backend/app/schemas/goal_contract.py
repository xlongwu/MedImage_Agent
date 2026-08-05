"""Reviewed goal contracts and deterministic evaluation records."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.app.schemas.node_contract import CapabilityLevel

GoalEvaluationStatus = Literal["satisfied", "not_satisfied", "indeterminate"]
CriterionResultStatus = Literal["passed", "failed", "indeterminate"]
CriterionType = Literal[
    "pipeline_terminal",
    "node_status",
    "artifact_present",
    "artifact_reloadable",
    "artifact_registered",
    "validation_passed",
    "capability_at_least",
    "scientific_status_allowed",
    "scope_complete",
    "no_blocking_issue",
]
Quantifier = Literal["all", "any", "at_least_count", "at_least_fraction"]


class GoalScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_ids: tuple[str, ...] = ()
    session_ids: tuple[str, ...] = ()
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    completeness_required: bool = True


class GoalCriterion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    criterion_id: str
    criterion_type: CriterionType
    target: str
    quantifier: Quantifier = "all"
    threshold_count: int | None = Field(default=None, ge=1)
    threshold_fraction: float | None = Field(default=None, gt=0, le=1)
    severity: Literal["required", "optional"] = "required"
    required_evidence: tuple[str, ...] = ()
    expected: dict[str, Any] = Field(default_factory=dict)
    failure_semantics: Literal["strict", "indeterminate_if_source_incomplete"] = "strict"


class GoalContractCandidate(BaseModel):
    """Editable review-time semantics; identity and hashes remain server-owned."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    goal_text: str = Field(min_length=1)
    goal_kind: str = Field(min_length=1)
    scope: GoalScope
    criteria: tuple[GoalCriterion, ...] = Field(min_length=1)
    minimum_capability_level: CapabilityLevel
    allowed_limitation_flags: tuple[str, ...] = ()
    forbidden_limitation_flags: tuple[str, ...] = (
        "simplified",
        "preview_only",
        "partial",
    )
    evaluation_policy_version: Literal["goal-evaluator-v1"] = "goal-evaluator-v1"
    builder_source: str = Field(default="reviewed_goal_contract", min_length=1)
    warnings: tuple[str, ...] = ()

    def semantics(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class GoalContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_contract_id: str
    schema_version: int = 1
    goal_text: str
    goal_kind: str
    project_id: str
    reviewed_plan_id: str
    plan_hash: str
    scope: GoalScope
    criteria: tuple[GoalCriterion, ...]
    minimum_capability_level: CapabilityLevel
    allowed_limitation_flags: tuple[str, ...] = ()
    forbidden_limitation_flags: tuple[str, ...] = (
        "simplified",
        "preview_only",
        "partial",
    )
    evaluation_policy_version: str = "goal-evaluator-v1"
    builder_source: str = "deterministic_contract_builder"
    reviewed_actor: str | None = None
    reviewed_at: datetime | None = None
    warnings: tuple[str, ...] = ()
    goal_contract_hash: str


class CriterionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    criterion_id: str
    criterion_type: CriterionType
    status: CriterionResultStatus
    evidence_ids: tuple[str, ...] = ()
    expected: Any = None
    actual: Any = None
    affected_subjects: tuple[str, ...] = ()
    affected_nodes: tuple[str, ...] = ()
    affected_artifacts: tuple[str, ...] = ()
    blocking: bool = False
    reason_code: str


class GoalEvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_evaluation_id: str
    goal_evaluation_hash: str
    status: GoalEvaluationStatus
    failed_criteria: tuple[str, ...] = ()
    indeterminate_criteria: tuple[str, ...] = ()


class GoalEvaluationRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_evaluation_id: str
    schema_version: int = 1
    evaluator_version: str = "goal-evaluator-v1"
    project_id: str
    lifecycle_id: str
    reviewed_plan_id: str
    plan_hash: str
    goal_contract_id: str
    goal_contract_hash: str
    observation_id: str
    observation_hash: str
    recovery_attempt_id: str | None = None
    evaluated_at: datetime
    criterion_results: tuple[CriterionResult, ...]
    status: GoalEvaluationStatus
    warnings: tuple[str, ...] = ()
    previous_goal_evaluation_id: str | None = None
    goal_evaluation_hash: str

    def summary(self) -> GoalEvaluationSummary:
        return GoalEvaluationSummary(
            goal_evaluation_id=self.goal_evaluation_id,
            goal_evaluation_hash=self.goal_evaluation_hash,
            status=self.status,
            failed_criteria=tuple(
                result.criterion_id
                for result in self.criterion_results
                if result.status == "failed"
            ),
            indeterminate_criteria=tuple(
                result.criterion_id
                for result in self.criterion_results
                if result.status == "indeterminate"
            ),
        )
