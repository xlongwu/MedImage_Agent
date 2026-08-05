"""Project-serial deterministic Phase 2 memory consolidation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from src.backend.app.services.memory_repository import MemoryRepository


class MemoryConsolidationService:
    def __init__(
        self,
        *,
        project_store,
        memory_repository: MemoryRepository,
        config=None,
        llm_proposal_service=None,
    ) -> None:
        self.project_store = project_store
        self.repository = memory_repository
        self.config = config
        self.llm_proposal_service = llm_proposal_service

    def consolidate_project(
        self, *, project_id: str, owner: str | None = None
    ) -> dict[str, Any]:
        consent = self.project_store.get_memory_consent(project_id)
        if not bool(consent.get("generate_enabled")):
            return {"status": "consent_disabled", "selection_diff": {}}
        owner = owner or f"memory-consolidator-{uuid4().hex}"
        lease = self.repository.claim_project_lease(
            project_id=project_id, owner=owner
        )
        # No model call is made in the deterministic MVP.  If one is added, it
        # must run outside the final commit transaction and the same token must
        # be revalidated by consolidate_accepted().
        token = int(lease["fencing_token"])
        try:
            proposal_actions = ()
            if self.llm_proposal_service is not None:
                accepted = self.repository.list_candidates(
                    project_id=project_id, status="accepted", limit=100
                )
                proposal_actions = self.llm_proposal_service.propose_consolidation(
                    candidates=[
                        {
                            "candidate_id": item.candidate_id,
                            "kind": item.kind,
                            "key": item.canonical_key,
                            "value": item.content,
                            "summary": item.content_text,
                        }
                        for item in accepted
                    ]
                )
            result = self.repository.consolidate_accepted(
                project_id=project_id,
                consent_epoch=int(consent.get("consent_epoch") or 0),
                owner=owner,
                fencing_token=token,
                valid_until=(
                    (
                        datetime.now(UTC)
                        + timedelta(days=self.config.item_retention_days)
                    )
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z")
                    if self.config is not None
                    else None
                ),
            )
            return {
                **result,
                "llm_proposal_actions": [
                    action.model_dump(mode="json") for action in proposal_actions
                ],
            }
        finally:
            self.repository.release_project_lease(
                project_id=project_id, owner=owner, fencing_token=token
            )
