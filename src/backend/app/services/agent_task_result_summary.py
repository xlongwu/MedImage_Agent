"""Truthful Agent result projection from bound observation/evaluation evidence."""

from __future__ import annotations

from src.backend.app.core.exceptions import SafetyError
from src.backend.app.schemas.agent_task import AgentTaskArtifactSummary, AgentTaskResultSummary

_LIMITATION_TEXT = {
    "partial": "Only part of the reviewed subject or artifact scope completed.",
    "preview_only": "This is a preview result and is not a full-dataset result.",
    "simplified": "A scientifically simplified method was used; review its limitations.",
    "metadata_only": "Only metadata evidence exists; no declared numerical result was computed.",
}


class AgentTaskResultSummaryService:
    def build(self, *, lifecycle, observation, evaluation) -> AgentTaskResultSummary:
        self._validate_bindings(lifecycle=lifecycle, observation=observation, evaluation=evaluation)
        completed, failed, excluded, total = self._subject_counts(observation)
        capability = observation.capability.defensible_level
        artifacts = tuple(
            AgentTaskArtifactSummary(
                artifact_id=item.artifact_id,
                artifact_type=item.artifact_type,
                label=item.artifact_type.replace("_", " ").title(),
                uri=f"project://{lifecycle.project_id}/artifacts/{item.artifact_id}",
                checksum=item.checksum_sha256,
                capability_level=capability,
                reload_status=(
                    "passed" if item.reload_status == "passed"
                    else "failed" if item.reload_status == "failed"
                    else "not_checked" if item.reload_status == "unknown"
                    else "unavailable"
                ),
            )
            for item in observation.artifacts
            if item.exists
        )
        defensible = any(
            item.exists
            and item.registration_status == "registered"
            and item.reload_status == "passed"
            for item in observation.artifacts
        )
        complete = (
            evaluation.status == "satisfied"
            and capability in {"computed", "validated"}
            and defensible
            and not failed
            and not observation.completeness.conflicts
            and not observation.completeness.blocking_facts
        )
        raw_limitations = tuple(dict.fromkeys([
            *observation.scientific.limitation_flags,
            *observation.completeness.blocking_facts,
            *observation.completeness.conflicts,
        ]))
        limitations = tuple(_LIMITATION_TEXT.get(item, item) for item in raw_limitations)
        validation_failures = sum(item.status == "failed" for item in observation.validations)
        qc_summary = (
            f"{len(observation.validations) - validation_failures} validation check(s) passed; "
            f"{validation_failures} failed."
            if observation.validations
            else "No separate QC validation record was available."
        )
        if complete:
            outcome = "succeeded"
            title = "Research goal satisfied"
            summary = "The goal is supported by complete, registered, reloadable numerical evidence."
        elif evaluation.status == "not_satisfied" or failed:
            outcome = "partial" if artifacts or completed else "failed"
            title = "Research goal not fully satisfied"
            summary = "Some reviewed evidence failed or remained incomplete."
        else:
            outcome = "partial" if artifacts else "indeterminate"
            title = "Result needs attention"
            summary = "Evidence is incomplete, conflicting, or not reloadable."
        return AgentTaskResultSummary(
            outcome=outcome,
            title=title,
            summary=summary,
            qc_summary=qc_summary,
            completed_subjects=completed,
            failed_subjects=failed,
            excluded_subjects=excluded,
            total_subjects=total,
            limitations=limitations,
            recommended_action=None if complete else "Review technical evidence and the bounded recovery proposal.",
            artifacts=artifacts,
        )

    @staticmethod
    def _validate_bindings(*, lifecycle, observation, evaluation) -> None:
        bindings = observation.bindings
        expected = (
            bindings.project_id == lifecycle.project_id
            and bindings.lifecycle_id == lifecycle.lifecycle_id
            and bindings.reviewed_plan_id == lifecycle.reviewed_plan_id
            and bindings.run_id == lifecycle.run_id
            and bindings.execution_ticket_id == lifecycle.execution_ticket_id
            and evaluation.project_id == lifecycle.project_id
            and evaluation.lifecycle_id == lifecycle.lifecycle_id
            and evaluation.observation_id == observation.observation_id
            and evaluation.observation_hash == observation.observation_hash
            and evaluation.reviewed_plan_id == bindings.reviewed_plan_id
            and evaluation.plan_hash == bindings.plan_hash
        )
        if not expected:
            raise SafetyError("AGENT_RESULT_BINDING_MISMATCH", code="AGENT_RESULT_BINDING_MISMATCH")

    @staticmethod
    def _subject_counts(observation) -> tuple[int | None, int | None, int | None, int | None]:
        statuses: dict[str, str] = {}
        for node in observation.nodes:
            if node.subject_id and node.subject_id != "project":
                statuses[node.subject_id] = str(node.status).upper()
        if not statuses:
            return None, None, None, None
        completed = sum(value in {"SUCCESS", "SUCCEEDED", "COMPLETED"} for value in statuses.values())
        failed = sum(value in {"FAILED", "ERROR"} for value in statuses.values())
        excluded = sum(value in {"SKIPPED", "EXCLUDED"} for value in statuses.values())
        return completed, failed, excluded, len(statuses)
