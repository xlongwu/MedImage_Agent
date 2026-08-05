"""Deterministic Goal Contract evaluator over one immutable Observation."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from src.backend.app.core.exceptions import SafetyError, StateStoreError
from src.backend.app.planner.audit_record import stable_hash
from src.backend.app.schemas.desktop import ReviewedPlanRecord
from src.backend.app.schemas.goal_contract import (
    CriterionResult,
    GoalContract,
    GoalCriterion,
    GoalEvaluationRecord,
)
from src.backend.app.schemas.observation import ArtifactObservation, ObservationRecord


class GoalEvaluationStore(Protocol):
    def get_reviewed_plan(self, reviewed_plan_id: str) -> ReviewedPlanRecord | None: ...
    def get_observation(self, observation_id: str) -> ObservationRecord | None: ...
    def add_goal_evaluation(self, record: GoalEvaluationRecord) -> GoalEvaluationRecord: ...
    def get_goal_evaluation(self, goal_evaluation_id: str) -> GoalEvaluationRecord | None: ...
    def list_goal_evaluations(
        self,
        project_id: str,
        *,
        lifecycle_id: str | None = None,
        observation_id: str | None = None,
    ) -> list[GoalEvaluationRecord]: ...


_LEVELS = ["unavailable", "scaffolded", "metadata_only", "computed", "validated"]


def _artifact_type(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return {"functional_connectivity_matrix": "fc_matrix"}.get(normalized, normalized)


def calculate_goal_evaluation_hash(
    record: GoalEvaluationRecord | dict[str, object],
) -> str:
    payload = (
        record.model_dump(mode="json") if isinstance(record, GoalEvaluationRecord) else dict(record)
    )
    payload.pop("goal_evaluation_hash", None)
    return stable_hash(payload)


def _source_available(observation: ObservationRecord, source_types: Iterable[str]) -> bool:
    if observation.completeness.conflicts:
        return False
    requested = set(source_types)
    return any(
        source.source_type in requested and source.read_status == "ok"
        for source in observation.sources
    )


def _sources_available_all(observation: ObservationRecord, source_types: Iterable[str]) -> bool:
    return all(_source_available(observation, (source_type,)) for source_type in source_types)


def _result(
    criterion: GoalCriterion,
    status: str,
    reason_code: str,
    *,
    evidence_ids: Iterable[str] = (),
    actual=None,
    affected_subjects: Iterable[str] = (),
    affected_nodes: Iterable[str] = (),
    affected_artifacts: Iterable[str] = (),
    blocking: bool | None = None,
) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion.criterion_id,
        criterion_type=criterion.criterion_type,
        status=status,
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        expected=criterion.expected,
        actual=actual,
        affected_subjects=tuple(sorted(set(affected_subjects))),
        affected_nodes=tuple(sorted(set(affected_nodes))),
        affected_artifacts=tuple(sorted(set(affected_artifacts))),
        blocking=(criterion.severity == "required") if blocking is None else blocking,
        reason_code=reason_code,
    )


def _scope_artifacts(
    observation: ObservationRecord,
    goal: GoalContract,
    artifact_type: str,
) -> list[ArtifactObservation]:
    values = [
        artifact
        for artifact in observation.artifacts
        if _artifact_type(artifact.artifact_type) == _artifact_type(artifact_type)
    ]
    if goal.scope.subject_ids:
        values = [artifact for artifact in values if artifact.subject_id in goal.scope.subject_ids]
    if goal.scope.session_ids:
        values = [artifact for artifact in values if artifact.session_id in goal.scope.session_ids]
    return values


def _quantifier_pass(criterion: GoalCriterion, values: list[bool]) -> bool:
    if not values:
        return False
    if criterion.quantifier == "all":
        return all(values)
    if criterion.quantifier == "any":
        return any(values)
    if criterion.quantifier == "at_least_count":
        return sum(values) >= int(criterion.threshold_count or 1)
    if criterion.quantifier == "at_least_fraction":
        return (sum(values) / len(values)) >= float(criterion.threshold_fraction or 1.0)
    return False


def _evaluate_artifact(
    criterion: GoalCriterion,
    goal: GoalContract,
    observation: ObservationRecord,
) -> CriterionResult:
    artifacts = _scope_artifacts(observation, goal, criterion.target)
    if criterion.criterion_type == "artifact_present":
        source_ok = _source_available(observation, ("artifact_discovery",))
        def predicate(artifact):
            return artifact.exists
        reason = "ARTIFACT_MISSING"
    elif criterion.criterion_type == "artifact_reloadable":
        source_ok = _source_available(observation, ("artifact_discovery", "artifact_registry"))
        def predicate(artifact):
            return artifact.exists and artifact.reload_status == "passed"
        reason = "ARTIFACT_NOT_RELOADABLE"
    else:
        source_ok = _source_available(observation, ("artifact_registry",))
        def predicate(artifact):
            return artifact.registration_status == "registered"
        reason = "ARTIFACT_NOT_REGISTERED"
    if not artifacts and not goal.scope.subject_ids:
        return _result(
            criterion,
            "failed" if source_ok else "indeterminate",
            reason if source_ok else "ARTIFACT_SOURCE_INCOMPLETE",
            actual={"count": 0},
        )
    if goal.scope.subject_ids:
        values = [
            any(artifact.subject_id == subject and predicate(artifact) for artifact in artifacts)
            for subject in goal.scope.subject_ids
        ]
        failed_subjects = [
            subject
            for subject, passed in zip(goal.scope.subject_ids, values, strict=True)
            if not passed
        ]
    else:
        values = [predicate(artifact) for artifact in artifacts]
        failed_subjects = []
    failed = [artifact for artifact in artifacts if not predicate(artifact)]
    if not _quantifier_pass(criterion, values):
        return _result(
            criterion,
            "failed" if source_ok else "indeterminate",
            reason if source_ok else "ARTIFACT_SOURCE_INCOMPLETE",
            evidence_ids=(evidence for artifact in failed for evidence in artifact.evidence_ids),
            actual={
                "count": len(values),
                "passed": sum(values),
                "failed": len(values) - sum(values),
            },
            affected_subjects=(
                *failed_subjects,
                *(artifact.subject_id for artifact in failed if artifact.subject_id),
            ),
            affected_artifacts=(artifact.artifact_id for artifact in failed),
        )
    return _result(
        criterion,
        "passed",
        "CRITERION_PASSED",
        evidence_ids=(evidence for artifact in artifacts for evidence in artifact.evidence_ids),
        actual={"count": len(values), "passed": sum(values)},
        affected_artifacts=(artifact.artifact_id for artifact in artifacts),
        blocking=False,
    )


def evaluate_criterion(
    criterion: GoalCriterion,
    goal: GoalContract,
    observation: ObservationRecord,
) -> CriterionResult:
    kind = criterion.criterion_type
    if kind == "pipeline_terminal":
        source_ok = _source_available(observation, ("pipeline_summary", "node_state"))
        allowed = {
            str(item).upper()
            for item in criterion.expected.get("statuses", ["SUCCESS", "COMPLETED"])
        }
        if not source_ok:
            return _result(criterion, "indeterminate", "PIPELINE_SOURCE_INCOMPLETE")
        passed = (
            observation.pipeline.status.upper() in allowed
            and (observation.pipeline.active_nodes or 0) == 0
        )
        return _result(
            criterion,
            "passed" if passed else "failed",
            "CRITERION_PASSED" if passed else "PIPELINE_TERMINAL_STATUS_FAILED",
            evidence_ids=observation.pipeline.evidence_ids,
            actual={
                "status": observation.pipeline.status,
                "active_nodes": observation.pipeline.active_nodes,
            },
            blocking=not passed,
        )
    if kind == "node_status":
        source_ok = _source_available(observation, ("node_state", "node_states"))
        required = {str(item) for item in criterion.expected.get("node_ids", [])}
        allowed = {
            str(item).upper()
            for item in criterion.expected.get("statuses", ["SUCCESS", "COMPLETED"])
        }
        relevant = [node for node in observation.nodes if node.node_id in required]
        observed = {node.node_id for node in relevant}
        missing = required - observed
        failed = [node for node in relevant if node.status.upper() not in allowed]
        values = [
            any(node.node_id == node_id and node.status.upper() in allowed for node in relevant)
            for node_id in sorted(required)
        ]
        if (missing or not relevant) and not source_ok:
            return _result(
                criterion, "indeterminate", "NODE_STATE_SOURCE_INCOMPLETE", affected_nodes=missing
            )
        if not _quantifier_pass(criterion, values):
            return _result(
                criterion,
                "failed" if source_ok else "indeterminate",
                "REQUIRED_NODE_NOT_SUCCESSFUL" if source_ok else "NODE_STATE_SOURCE_INCOMPLETE",
                evidence_ids=(evidence for node in failed for evidence in node.evidence_ids),
                actual={node.node_id: node.status for node in relevant},
                affected_subjects=(node.subject_id for node in failed),
                affected_nodes=(*missing, *(node.node_id for node in failed)),
            )
        return _result(
            criterion,
            "passed",
            "CRITERION_PASSED",
            evidence_ids=(evidence for node in relevant for evidence in node.evidence_ids),
            actual={node.node_id: node.status for node in relevant},
            blocking=False,
        )
    if kind in {"artifact_present", "artifact_reloadable", "artifact_registered"}:
        return _evaluate_artifact(criterion, goal, observation)
    if kind == "validation_passed":
        source_ok = _source_available(observation, ("validation",))
        if not source_ok:
            return _result(criterion, "indeterminate", "VALIDATION_SOURCE_INCOMPLETE")
        if not observation.validations:
            return _result(
                criterion,
                "failed",
                "VALIDATION_MISSING",
            )
        failed = [
            validation for validation in observation.validations if validation.status != "passed"
        ]
        return _result(
            criterion,
            "failed" if failed else "passed",
            "VALIDATION_FAILED" if failed else "CRITERION_PASSED",
            evidence_ids=(
                evidence
                for validation in observation.validations
                for evidence in validation.evidence_ids
            ),
            actual={
                validation.validation_id: validation.status
                for validation in observation.validations
            },
            blocking=bool(failed),
        )
    if kind == "capability_at_least":
        minimum = str(criterion.expected.get("minimum") or criterion.target)
        actual = observation.capability.defensible_level
        passed = _LEVELS.index(actual) >= _LEVELS.index(minimum)
        source_ok = _sources_available_all(observation, ("node_contract", "artifact_discovery"))
        status = "passed" if passed else "failed" if source_ok else "indeterminate"
        return _result(
            criterion,
            status,
            "CRITERION_PASSED"
            if passed
            else "CAPABILITY_BELOW_MINIMUM"
            if source_ok
            else "CAPABILITY_SOURCE_INCOMPLETE",
            evidence_ids=observation.capability.evidence_ids,
            actual=actual,
            blocking=not passed,
        )
    if kind == "scientific_status_allowed":
        minimum = str(criterion.expected.get("minimum") or goal.minimum_capability_level)
        forbidden = set(
            criterion.expected.get("forbidden_limitation_flags", goal.forbidden_limitation_flags)
        )
        forbidden.difference_update(goal.allowed_limitation_flags)
        active_forbidden = forbidden.intersection(observation.scientific.limitation_flags)
        level_ok = _LEVELS.index(observation.scientific.status) >= _LEVELS.index(minimum)
        passed = level_ok and not active_forbidden
        source_ok = _sources_available_all(
            observation, ("artifact_registry", "validation", "node_contract")
        )
        return _result(
            criterion,
            "passed" if passed else "failed" if source_ok else "indeterminate",
            "CRITERION_PASSED"
            if passed
            else "SCIENTIFIC_STATUS_NOT_ALLOWED"
            if source_ok
            else "SCIENTIFIC_SOURCE_INCOMPLETE",
            evidence_ids=observation.scientific.validation_evidence_ids,
            actual={
                "status": observation.scientific.status,
                "limitation_flags": list(observation.scientific.limitation_flags),
            },
            blocking=not passed,
        )
    if kind == "scope_complete":
        artifact_types = [str(item) for item in criterion.expected.get("artifact_types", [])]
        source_ok = (
            _source_available(observation, ("artifact_registry",))
            if artifact_types
            else _source_available(observation, ("node_state",))
        )
        subjects = set(goal.scope.subject_ids)
        if not subjects:
            subjects = {
                node.subject_id for node in observation.nodes if node.subject_id != "project"
            }
        missing: list[str] = []
        if subjects:
            for subject in sorted(subjects):
                for target in artifact_types:
                    if not any(
                        artifact.subject_id == subject
                        and _artifact_type(artifact.artifact_type) == _artifact_type(target)
                        and artifact.exists
                        for artifact in observation.artifacts
                    ):
                        missing.append(f"{subject}:{target}")
        else:
            for target in artifact_types:
                if not any(
                    _artifact_type(artifact.artifact_type) == _artifact_type(target)
                    and artifact.exists
                    for artifact in observation.artifacts
                ):
                    missing.append(target)
        if missing:
            return _result(
                criterion,
                "failed" if source_ok else "indeterminate",
                "SCOPE_INCOMPLETE" if source_ok else "SCOPE_SOURCE_INCOMPLETE",
                actual={"missing": missing},
                affected_subjects=subjects,
            )
        return _result(
            criterion,
            "passed",
            "CRITERION_PASSED",
            actual={"subjects": sorted(subjects)},
            blocking=False,
        )
    if kind == "no_blocking_issue":
        if observation.completeness.conflicts:
            return _result(
                criterion,
                "indeterminate",
                "OBSERVATION_CONFLICT",
                actual={"conflicts": observation.completeness.conflicts},
            )
        if observation.completeness.blocking_facts:
            return _result(
                criterion,
                "failed",
                "OBSERVATION_BLOCKING_FACT",
                actual={"blocking_facts": observation.completeness.blocking_facts},
            )
        return _result(
            criterion, "passed", "CRITERION_PASSED", actual={"blocking_facts": 0}, blocking=False
        )
    return _result(criterion, "indeterminate", "CRITERION_TYPE_UNSUPPORTED")


class GoalEvaluator:
    VERSION = "goal-evaluator-v1"

    def __init__(self, store: GoalEvaluationStore) -> None:
        self.store = store

    def evaluate(
        self,
        *,
        project_id: str,
        lifecycle_id: str,
        observation_id: str,
        previous_goal_evaluation_id: str | None = None,
    ) -> GoalEvaluationRecord:
        observation = self.store.get_observation(observation_id)
        if (
            observation is None
            or observation.bindings.project_id != project_id
            or observation.bindings.lifecycle_id != lifecycle_id
        ):
            raise SafetyError(
                "GOAL_EVALUATION_OBSERVATION_MISMATCH", code="GOAL_EVALUATION_OBSERVATION_MISMATCH"
            )
        reviewed = self.store.get_reviewed_plan(observation.bindings.reviewed_plan_id)
        payload = reviewed.payload.get("goal_contract") if reviewed else None
        if reviewed is None or reviewed.project_id != project_id or not isinstance(payload, dict):
            raise SafetyError("GOAL_CONTRACT_REVIEW_REQUIRED", code="GOAL_CONTRACT_REVIEW_REQUIRED")
        try:
            goal = GoalContract(**payload)
        except Exception as exc:
            raise SafetyError("GOAL_CONTRACT_INVALID", code="GOAL_CONTRACT_INVALID") from exc
        if (
            goal.reviewed_plan_id != reviewed.reviewed_plan_id
            or goal.plan_hash != reviewed.plan_hash
            or goal.goal_contract_hash != observation.bindings.goal_contract_hash
            or goal.goal_contract_id != observation.bindings.goal_contract_id
        ):
            raise SafetyError("GOAL_CONTRACT_BINDING_DRIFT", code="GOAL_CONTRACT_BINDING_DRIFT")
        results = tuple(
            evaluate_criterion(criterion, goal, observation) for criterion in goal.criteria
        )
        required = [
            result
            for result, criterion in zip(results, goal.criteria, strict=True)
            if criterion.severity == "required"
        ]
        if any(result.status == "failed" for result in required):
            status = "not_satisfied"
        elif any(result.status == "indeterminate" for result in required):
            status = "indeterminate"
        else:
            status = "satisfied"
        if previous_goal_evaluation_id is None:
            existing = self.store.list_goal_evaluations(
                project_id,
                lifecycle_id=lifecycle_id,
                observation_id=observation_id,
            )
            previous_goal_evaluation_id = existing[0].goal_evaluation_id if existing else None
        elif self.store.get_goal_evaluation(previous_goal_evaluation_id) is None:
            raise SafetyError(
                "GOAL_EVALUATION_PREVIOUS_NOT_FOUND", code="GOAL_EVALUATION_PREVIOUS_NOT_FOUND"
            )
        record = GoalEvaluationRecord(
            goal_evaluation_id=f"goal_evaluation_{uuid4().hex}",
            evaluator_version=self.VERSION,
            project_id=project_id,
            lifecycle_id=lifecycle_id,
            reviewed_plan_id=reviewed.reviewed_plan_id,
            plan_hash=reviewed.plan_hash,
            goal_contract_id=goal.goal_contract_id,
            goal_contract_hash=goal.goal_contract_hash,
            observation_id=observation.observation_id,
            observation_hash=observation.observation_hash,
            recovery_attempt_id=observation.bindings.recovery_attempt_id,
            evaluated_at=datetime.now(UTC),
            criterion_results=results,
            status=status,
            previous_goal_evaluation_id=previous_goal_evaluation_id,
            goal_evaluation_hash="pending",
        )
        record = record.model_copy(
            update={"goal_evaluation_hash": calculate_goal_evaluation_hash(record)}
        )
        try:
            return self.store.add_goal_evaluation(record)
        except Exception as exc:
            raise StateStoreError("GOAL_EVALUATION_PERSISTENCE_FAILED") from exc
