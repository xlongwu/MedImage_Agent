"""Bounded maintenance and crash reconciliation for the Memory Domain."""

from __future__ import annotations

from typing import Any

from src.backend.app.services.memory_repository import MemoryRepository


class MemoryMaintenanceService:
    def __init__(self, *, project_store, memory_repository: MemoryRepository) -> None:
        self.project_store = project_store
        self.repository = memory_repository

    def reconcile_project(self, *, project_id: str, max_forget_records: int = 100) -> dict[str, Any]:
        consent = self.project_store.get_memory_consent(project_id)
        epoch = int(consent.get("consent_epoch") or 0)
        stale_candidates = self.repository.scrub_stale_candidates(
            project_id=project_id, current_consent_epoch=epoch
        )
        expired_items = self.repository.expire_due_items(project_id=project_id)
        expired_candidates = self.repository.expire_due_candidates(project_id=project_id)
        completed_forgets = 0
        ledgers = self.project_store.list_memory_forget_ledger(project_id)
        for ledger in ledgers[: max(0, max_forget_records)]:
            item = self.repository.get_item_by_canonical_key(
                project_id=project_id,
                canonical_key=str(ledger["canonical_key"]),
            )
            if item is None or item.status == "forgotten":
                continue
            self.repository.forget_item(
                project_id=project_id,
                memory_id=item.memory_id,
                command_id=str(ledger["command_id"]),
                principal=str(ledger["principal"]),
                expected_item_version=item.item_version,
                expected_revision_hash=item.revision.content_hash,
                ledger_record=ledger,
            )
            completed_forgets += 1
        if ledgers:
            self.repository.ensure_forget_wal_truncated()
        return {
            "status": "ok",
            "stale_candidates_scrubbed": stale_candidates,
            "items_expired": expired_items,
            "candidates_expired": expired_candidates,
            "forget_sagas_completed": completed_forgets,
            "expired_leases_released": self.repository.release_expired_leases(),
        }
