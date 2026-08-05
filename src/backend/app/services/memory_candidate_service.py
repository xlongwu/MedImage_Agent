"""Deterministic Phase 1 consumer for committed project memory sources."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.backend.app.core.config_schema import MemoryConfig
from src.backend.app.planner.audit_record import stable_hash
from src.backend.app.services.memory_filter_service import MemoryFilterService
from src.backend.app.services.memory_repository import (
    MemoryRepository,
    canonical_memory_key,
)

PHASE1_CONSUMER = "memory-phase1-v1"
_SCIENTIFIC_DECISIONS = {
    "atlas",
    "gsr",
    "global_signal_regression",
    "tr",
    "template",
    "backend",
    "experimental_backend",
}


class MemoryCandidateService:
    def __init__(
        self,
        *,
        project_store,
        memory_repository: MemoryRepository,
        config: MemoryConfig,
        filter_service: MemoryFilterService | None = None,
        llm_proposal_service=None,
    ) -> None:
        self.project_store = project_store
        self.repository = memory_repository
        self.config = config
        self.filter = filter_service or MemoryFilterService()
        self.llm_proposal_service = llm_proposal_service

    def process_project(self, *, project_id: str, limit: int = 100) -> dict[str, Any]:
        if not self.config.enabled or not self.config.generation_enabled:
            return {"status": "disabled", "processed": 0, "candidates": 0}
        if self.project_store.get_project(project_id) is None:
            return {"status": "project_not_found", "processed": 0, "candidates": 0}
        consent = self.project_store.get_memory_consent(project_id)
        if not bool(consent.get("generate_enabled")):
            return {"status": "consent_disabled", "processed": 0, "candidates": 0}
        expected_epoch = int(consent.get("consent_epoch") or 0)
        watermark = self.repository.get_watermark(
            consumer=PHASE1_CONSUMER, project_id=project_id
        )
        after = max(
            int(watermark.get("source_sequence") or 0),
            int(consent.get("outbox_cutoff_sequence") or 0),
        )
        rows = self.project_store.list_memory_outbox(
            project_id, after_sequence=after, limit=max(1, min(limit, 500))
        )
        processed = 0
        candidates = 0
        rejected = 0
        no_output = 0
        for row in rows:
            current_consent = self.project_store.get_memory_consent(project_id)
            if (
                not bool(current_consent.get("generate_enabled"))
                or int(current_consent.get("consent_epoch") or 0) != expected_epoch
            ):
                return {
                    "status": "consent_changed",
                    "processed": processed,
                    "candidates": candidates,
                    "rejected": rejected,
                    "no_output": no_output,
                }
            try:
                result = self._process_row(project_id=project_id, row=row)
            except Exception as exc:
                failure = self.repository.record_source_failure(
                    project_id=project_id,
                    source_sequence=int(row["sequence"]),
                    consent_epoch=int(row["consent_epoch"]),
                    error_code=f"MEMORY_PHASE1_FAILED:{type(exc).__name__}",
                )
                return {
                    "status": failure["status"],
                    "processed": processed,
                    "candidates": candidates,
                    "rejected": rejected,
                    "no_output": no_output,
                    "error_code": failure["error_code"],
                }
            processed += 1
            if result["status"] == "succeeded":
                candidates += 1
            elif result["status"] == "rejected":
                rejected += 1
            else:
                no_output += 1
        return {
            "status": "ok",
            "processed": processed,
            "candidates": candidates,
            "rejected": rejected,
            "no_output": no_output,
        }

    def _process_row(self, *, project_id: str, row: dict[str, Any]) -> dict[str, Any]:
        sequence = int(row["sequence"])
        source_type = str(row["source_type"])
        source_id = str(row["source_id"])
        source_hash = str(row["source_hash"])
        trust = str(row["source_trust_class"])
        consent_epoch = int(row["consent_epoch"])
        projection = self.project_store.get_memory_source_projection(
            project_id=project_id,
            source_type=source_type,
            source_id=source_id,
        )
        if projection is None:
            return self.repository.commit_source_result(
                consumer=PHASE1_CONSUMER,
                project_id=project_id,
                source_sequence=sequence,
                source_hash=source_hash,
                consent_epoch=consent_epoch,
                source_type=source_type,
                source_id=source_id,
                source_trust_class=trust,
                outcome="rejected",
                rejection_code="MEMORY_SOURCE_MISSING",
            )
        if str(projection.get("source_hash") or "") != source_hash:
            return self.repository.commit_source_result(
                consumer=PHASE1_CONSUMER,
                project_id=project_id,
                source_sequence=sequence,
                source_hash=source_hash,
                consent_epoch=consent_epoch,
                source_type=source_type,
                source_id=source_id,
                source_trust_class=trust,
                outcome="rejected",
                rejection_code="SOURCE_VERSION_STALE",
            )
        filtered = self.filter.filter_source(
            source_type=source_type,
            source_trust_class=trust,
            projection=projection,
        )
        if not filtered.ok or filtered.cleaned is None:
            return self.repository.commit_source_result(
                consumer=PHASE1_CONSUMER,
                project_id=project_id,
                source_sequence=sequence,
                source_hash=source_hash,
                consent_epoch=consent_epoch,
                source_type=source_type,
                source_id=source_id,
                source_trust_class=trust,
                outcome="rejected",
                rejection_code=filtered.rejection_code or "MEMORY_SOURCE_REJECTED",
            )
        candidate = self._extract(
            project_id=project_id,
            source_type=source_type,
            projection=filtered.cleaned,
        )
        if candidate is None and self.llm_proposal_service is not None:
            proposals = self.llm_proposal_service.propose_extraction(
                source_type=source_type,
                source_trust_class=trust,
                projection=filtered.cleaned,
            )
            if proposals:
                proposal = sorted(
                    proposals,
                    key=lambda item: (-item.confidence, item.kind, item.key),
                )[0]
                candidate = {
                    "kind": proposal.kind,
                    "canonical_key": canonical_memory_key(proposal.kind, proposal.key),
                    "value": dict(proposal.value),
                    "summary": proposal.summary,
                    "impact_class": proposal.impact_class,
                    "extractor": "llm-proposal-v1",
                    "requires_review": True,
                    "confidence": proposal.confidence,
                    "model": self.llm_proposal_service.model_name,
                    "prompt_version": self.llm_proposal_service.prompt_version,
                }
        if candidate is None:
            return self.repository.commit_source_result(
                consumer=PHASE1_CONSUMER,
                project_id=project_id,
                source_sequence=sequence,
                source_hash=source_hash,
                consent_epoch=consent_epoch,
                source_type=source_type,
                source_id=source_id,
                source_trust_class=trust,
                outcome="succeeded_no_output",
            )
        return self.repository.commit_source_result(
            consumer=PHASE1_CONSUMER,
            project_id=project_id,
            source_sequence=sequence,
            source_hash=source_hash,
            consent_epoch=consent_epoch,
            source_type=source_type,
            source_id=source_id,
            source_trust_class=trust,
            outcome="succeeded",
            candidate=candidate,
            candidate_expires_at=(
                datetime.now(UTC)
                + timedelta(days=self.config.candidate_retention_days)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )

    @staticmethod
    def _extract(
        *, project_id: str, source_type: str, projection: dict[str, Any]
    ) -> dict[str, Any] | None:
        if source_type == "agent_lifecycle_event":
            event = projection.get("event") or {}
            if event.get("source_command") != "answer":
                return None
            details = event.get("details") or {}
            decision_kind = str(details.get("decision_kind") or "").strip()
            answer = details.get("answer")
            if not decision_kind or answer is None:
                return None
            impact = "scientific" if decision_kind in _SCIENTIFIC_DECISIONS else "workflow"
            return {
                "kind": "project_decision",
                "canonical_key": canonical_memory_key(
                    "project_decision", decision_kind
                ),
                "value": {
                    "decision_kind": decision_kind,
                    "value": answer,
                    "project_id": project_id,
                },
                "summary": f"Confirmed project decision: {decision_kind}.",
                "impact_class": impact,
                "extractor": "deterministic-lifecycle-v1",
                "requires_review": True,
            }
        if source_type == "observation":
            observation = projection.get("observation") or {}
            signals = sorted(
                {
                    str(value)
                    for key in ("errors", "warnings", "conflicts", "blocking_facts")
                    for value in (observation.get(key) or [])
                    if value
                }
            )
            if not signals:
                return None
            fingerprint = stable_hash(
                {
                    "execution_status": observation.get("execution_status"),
                    "signals": signals,
                }
            )
            return {
                "kind": "workflow_lesson",
                "canonical_key": canonical_memory_key(
                    "workflow_lesson", f"observation-{fingerprint[:20]}"
                ),
                "value": {
                    "execution_status": observation.get("execution_status"),
                    "signals": signals[:20],
                    "capability_level": observation.get("capability_level"),
                    "scientific_status": observation.get("scientific_status"),
                },
                "summary": "Observed a reusable workflow warning or failure pattern.",
                "impact_class": "workflow",
                "extractor": "deterministic-observation-v1",
                "requires_review": True,
            }
        if source_type == "goal_evaluation":
            evaluation = projection.get("evaluation") or {}
            status = str(evaluation.get("status") or "")
            reason_codes = sorted(
                {str(value) for value in evaluation.get("reason_codes") or [] if value}
            )
            if status == "satisfied" and not reason_codes:
                return None
            fingerprint = stable_hash({"status": status, "reason_codes": reason_codes})
            return {
                "kind": "workflow_lesson",
                "canonical_key": canonical_memory_key(
                    "workflow_lesson", f"goal-evaluation-{fingerprint[:20]}"
                ),
                "value": {
                    "evaluation_status": status,
                    "reason_codes": reason_codes[:20],
                    "failed_criteria": evaluation.get("failed_criteria") or [],
                },
                "summary": "Goal evaluation identified a reusable unmet prerequisite.",
                "impact_class": "workflow",
                "extractor": "deterministic-goal-evaluation-v1",
                "requires_review": True,
            }
        if source_type == "run_summary":
            run = projection.get("run") or {}
            status = str(run.get("status") or "").upper()
            warnings = sorted({str(value) for value in run.get("warnings") or [] if value})
            if status in {"SUCCEEDED", "SUCCESS", "COMPLETED"} and not warnings:
                return None
            fingerprint = stable_hash({"status": status, "warnings": warnings})
            return {
                "kind": "workflow_lesson",
                "canonical_key": canonical_memory_key(
                    "workflow_lesson", f"run-summary-{fingerprint[:20]}"
                ),
                "value": {"run_status": status, "warnings": warnings[:20]},
                "summary": "A terminal run exposed a reusable workflow outcome.",
                "impact_class": "workflow",
                "extractor": "deterministic-run-summary-v1",
                "requires_review": True,
            }
        return None
