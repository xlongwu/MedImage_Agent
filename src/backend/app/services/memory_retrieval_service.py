"""Consent-gated retrieval and typed planner context construction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.backend.app.planner.audit_record import stable_hash
from src.backend.app.schemas.memory import (
    MemoryContext,
    MemoryDecisionSuggestion,
    MemoryEvidenceRef,
    MemoryItem,
)

RETRIEVAL_POLICY_VERSION = "memory-retrieval-v1"


@dataclass(frozen=True)
class MemoryRetrievalResult:
    items: tuple[MemoryItem, ...]
    warnings: tuple[str, ...]
    omitted_count: int


class MemoryRetrievalService:
    """Build a bounded read model without granting memory execution authority."""

    def __init__(self, *, repository, project_store, config) -> None:
        self.repository = repository
        self.project_store = project_store
        self.config = config

    def retrieve(self, *, project_id: str, query: str) -> MemoryRetrievalResult:
        consent = self.project_store.get_memory_consent(project_id)
        if not (
            self.config.enabled
            and self.config.use_enabled
            and bool(consent.get("use_enabled"))
        ):
            return MemoryRetrievalResult(items=(), warnings=(), omitted_count=0)
        if not self.repository.health_check().get("ok"):
            return MemoryRetrievalResult(
                items=(), warnings=("MEMORY_STORE_UNHEALTHY",), omitted_count=0
            )

        forgotten = self._forgotten_generations(project_id)
        selected: list[MemoryItem] = []
        warnings: list[str] = []
        omitted = 0
        used_bytes = 0
        for item, _score in self.repository.retrieve_active_items(
            project_id=project_id, query=query, limit=200
        ):
            if item.generation <= forgotten.get(item.canonical_key, -1):
                omitted += 1
                continue
            stale = self._staleness(item)
            if stale and item.kind != "user_preference":
                omitted += 1
                continue
            if stale:
                warnings.append(f"MEMORY_SOURCE_STALE:{item.memory_id}")
            encoded = json.dumps(
                item.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if used_bytes + len(encoded) > self.config.max_context_bytes:
                omitted += 1
                continue
            used_bytes += len(encoded)
            selected.append(item)
        return MemoryRetrievalResult(
            items=tuple(selected),
            warnings=tuple(dict.fromkeys(warnings)),
            omitted_count=omitted,
        )

    def build_context(self, *, project_id: str, goal: str) -> MemoryContext:
        result = self.retrieve(project_id=project_id, query=goal)
        return self._build_context(project_id=project_id, result=result)

    def build_context_with_warnings(
        self, *, project_id: str, goal: str
    ) -> tuple[MemoryContext, tuple[str, ...]]:
        """Return the frozen context together with non-authoritative retrieval warnings."""

        result = self.retrieve(project_id=project_id, query=goal)
        return self._build_context(project_id=project_id, result=result), result.warnings

    def _build_context(
        self, *, project_id: str, result: MemoryRetrievalResult
    ) -> MemoryContext:
        suggestions: list[MemoryDecisionSuggestion] = []
        evidence: list[MemoryEvidenceRef] = []
        for item in result.items:
            revision = item.revision
            source_refs = tuple(source.source_ref for source in item.sources)
            if (
                item.kind == "project_decision"
                and revision.impact_class == "scientific"
                and revision.algorithm_id
                and revision.algorithm_version
                and revision.config_fingerprint
                and revision.confirmation_event_id
                and isinstance(revision.content.get("decision_kind"), str)
            ):
                suggestions.append(
                    MemoryDecisionSuggestion(
                        memory_id=item.memory_id,
                        revision_hash=revision.content_hash,
                        decision_kind=revision.content["decision_kind"],
                        typed_value=dict(revision.content),
                        algorithm_id=revision.algorithm_id,
                        algorithm_version=revision.algorithm_version,
                        config_fingerprint=revision.config_fingerprint,
                        applicability=dict(revision.applicability),
                        confirmation_event_id=revision.confirmation_event_id,
                        source_refs=source_refs,
                    )
                )
                continue
            for source_ref in source_refs or ("memory:no-source",):
                evidence.append(
                    MemoryEvidenceRef(
                        kind=item.kind,
                        memory_id=item.memory_id,
                        revision_hash=revision.content_hash,
                        source_ref=source_ref,
                        provenance_warning=(
                            "source_stale"
                            if f"MEMORY_SOURCE_STALE:{item.memory_id}" in result.warnings
                            else None
                        ),
                    )
                )
        identity = {
            "schema_version": "memory-context-v1",
            "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            "project_id": project_id,
            "planner_constraints": {},
            "decision_suggestions": [
                item.model_dump(mode="json") for item in suggestions
            ],
            "evidence_refs": [item.model_dump(mode="json") for item in evidence],
            "omitted_count": result.omitted_count,
        }
        return MemoryContext(
            **identity,
            context_hash=stable_hash(identity),
        )

    def _forgotten_generations(self, project_id: str) -> dict[str, int]:
        values: dict[str, int] = {}
        for row in self.project_store.list_memory_forget_ledger(project_id):
            key = str(row.get("canonical_key") or "")
            values[key] = max(values.get(key, -1), int(row.get("generation") or 0))
        return values

    def _staleness(self, item: MemoryItem) -> bool:
        for source in item.sources:
            if source.source_trust_class == "explicit_user":
                continue
            projection = self.project_store.get_memory_source_projection(
                project_id=item.project_id,
                source_type=source.source_type,
                source_id=source.source_id,
            )
            if projection is None or projection.get("source_hash") != source.source_hash:
                return True
        return False
