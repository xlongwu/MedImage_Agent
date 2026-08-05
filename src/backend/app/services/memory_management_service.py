"""Project-bound command service for user-controlled memory mutations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.backend.app.core.config_schema import MemoryConfig
from src.backend.app.planner.audit_record import stable_hash
from src.backend.app.services.memory_filter_service import MemoryFilterService
from src.backend.app.services.memory_repository import MemoryRepository, MemoryRepositoryError


class MemoryManagementService:
    def __init__(
        self,
        *,
        project_store,
        memory_repository: MemoryRepository,
        config: MemoryConfig,
        filter_service: MemoryFilterService | None = None,
    ) -> None:
        self.project_store = project_store
        self.repository = memory_repository
        self.config = config
        self.filter = filter_service or MemoryFilterService()

    def remember(
        self,
        *,
        project_id: str,
        command_id: str,
        principal: str,
        kind: str,
        key: str,
        value: dict[str, Any],
        summary: str,
        impact_class: str,
    ) -> dict[str, Any]:
        if not self.config.enabled:
            raise MemoryRepositoryError("MEMORY_DISABLED")
        if not self.config.generation_enabled:
            raise MemoryRepositoryError("MEMORY_GENERATION_DISABLED")
        if self.project_store.get_project(project_id) is None:
            raise MemoryRepositoryError("MEMORY_PROJECT_NOT_FOUND")
        consent = self.project_store.get_memory_consent(project_id)
        if not bool(consent.get("generate_enabled")):
            raise MemoryRepositoryError("MEMORY_GENERATION_CONSENT_REQUIRED")
        filtered = self.filter.filter_explicit(value=value, summary=summary)
        if not filtered.ok:
            raise MemoryRepositoryError(
                filtered.rejection_code or "MEMORY_CONTENT_REJECTED"
            )
        return self.repository.remember_explicit(
            project_id=project_id,
            command_id=command_id,
            principal=principal,
            kind=kind,
            key=key,
            value=value,
            summary=summary,
            impact_class=impact_class,
            consent_epoch=int(consent.get("consent_epoch") or 0),
            valid_until=(
                datetime.now(UTC) + timedelta(days=self.config.item_retention_days)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            candidate_expires_at=(
                datetime.now(UTC)
                + timedelta(days=self.config.candidate_retention_days)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )

    def review_candidate(
        self,
        *,
        project_id: str,
        candidate_id: str,
        command_id: str,
        principal: str,
        accept: bool,
        expected_candidate_version: int,
        candidate_hash: str,
        edited_value: dict[str, Any] | None = None,
        edited_summary: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        if accept and not self.config.generation_enabled:
            raise MemoryRepositoryError("MEMORY_GENERATION_DISABLED")
        consent = self.project_store.get_memory_consent(project_id)
        if accept and not bool(consent.get("generate_enabled")):
            raise MemoryRepositoryError("MEMORY_GENERATION_CONSENT_REQUIRED")
        if accept and (edited_value is not None or edited_summary is not None):
            candidate = self.repository.get_candidate(
                project_id=project_id, candidate_id=candidate_id
            )
            if candidate is None:
                raise MemoryRepositoryError("MEMORY_CANDIDATE_NOT_FOUND")
            filtered = self.filter.filter_explicit(
                value=edited_value if edited_value is not None else candidate.content,
                summary=(
                    edited_summary
                    if edited_summary is not None
                    else candidate.content_text
                ),
            )
            if not filtered.ok:
                raise MemoryRepositoryError(
                    filtered.rejection_code or "MEMORY_CONTENT_REJECTED"
                )
        return self.repository.review_candidate(
            project_id=project_id,
            candidate_id=candidate_id,
            command_id=command_id,
            principal=principal,
            accept=accept,
            expected_candidate_version=expected_candidate_version,
            candidate_hash=candidate_hash,
            edited_value=edited_value,
            edited_summary=edited_summary,
            reason=reason,
        )

    def set_pinned(self, **kwargs: Any) -> dict[str, Any]:
        return self.repository.set_pinned(**kwargs)

    def forget(
        self,
        *,
        project_id: str,
        memory_id: str,
        command_id: str,
        principal: str,
        expected_item_version: int,
        expected_revision_hash: str,
    ) -> dict[str, Any]:
        prior_ledger = next(
            (
                record
                for record in self.project_store.list_memory_forget_ledger(project_id)
                if record.get("command_id") == command_id
            ),
            None,
        )
        if prior_ledger is not None:
            return self.repository.forget_item(
                project_id=project_id,
                memory_id=memory_id,
                command_id=command_id,
                principal=principal,
                expected_item_version=expected_item_version,
                expected_revision_hash=expected_revision_hash,
                ledger_record=prior_ledger,
            )
        item = self.repository.get_item(project_id=project_id, memory_id=memory_id)
        if item is None:
            raise MemoryRepositoryError("MEMORY_ITEM_NOT_FOUND")
        if (
            item.item_version != expected_item_version
            or item.revision.content_hash != expected_revision_hash
        ):
            raise MemoryRepositoryError("MEMORY_ITEM_STALE")
        semantic_fingerprint = stable_hash(
            {
                "kind": item.kind,
                "value": item.revision.content,
                "policy_version": "memory-policy-v1",
            }
        )
        lineage = [
            stable_hash(
                {
                    "project_id": project_id,
                    "source_type": source.source_type,
                    "source_id": source.source_id,
                }
            )
            for source in item.sources
        ]
        ledger = self.project_store.append_memory_forget_ledger(
            project_id=project_id,
            command_id=command_id,
            principal=principal,
            canonical_key=item.canonical_key,
            semantic_fingerprint=semantic_fingerprint,
            source_lineage_fingerprints=lineage,
            content_hash=item.revision.content_hash,
            forget_outbox_sequence=self.project_store.get_memory_outbox_max_sequence(
                project_id
            ),
            generation=item.generation,
        )
        return self.repository.forget_item(
            project_id=project_id,
            memory_id=memory_id,
            command_id=command_id,
            principal=principal,
            expected_item_version=expected_item_version,
            expected_revision_hash=expected_revision_hash,
            ledger_record=ledger,
        )

    def restore(
        self,
        *,
        project_id: str,
        memory_id: str,
        command_id: str,
        principal: str,
        expected_item_version: int,
        expected_revision_hash: str,
        value: dict[str, Any],
        summary: str,
    ) -> dict[str, Any]:
        filtered = self.filter.filter_explicit(value=value, summary=summary)
        if not filtered.ok:
            raise MemoryRepositoryError(
                filtered.rejection_code or "MEMORY_CONTENT_REJECTED"
            )
        return self.repository.restore_item(
            project_id=project_id,
            memory_id=memory_id,
            command_id=command_id,
            principal=principal,
            expected_item_version=expected_item_version,
            expected_revision_hash=expected_revision_hash,
            value=value,
            summary=summary,
        )
