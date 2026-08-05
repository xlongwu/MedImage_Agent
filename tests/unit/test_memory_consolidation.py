from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.backend.app.core.config_schema import MemoryConfig
from src.backend.app.services.memory_consolidation_service import (
    MemoryConsolidationService,
)
from src.backend.app.services.memory_management_service import MemoryManagementService
from src.backend.app.services.memory_repository import MemoryRepository, MemoryRepositoryError
from src.backend.app.services.mock_store import SQLiteDesktopStore


def _setup(tmp_path: Path):
    store = SQLiteDesktopStore(tmp_path / "desktop.sqlite")
    project_id = store.list_projects()[0].id
    store.set_memory_consent(
        project_id=project_id,
        command_id="phase-c-consent-command-0001",
        principal="desktop-local-user",
        generate_enabled=True,
        use_enabled=True,
    )
    repository = MemoryRepository(tmp_path / "memory.sqlite")
    config = MemoryConfig(
        enabled=True,
        generation_enabled=True,
        use_enabled=True,
        store_path=str(tmp_path / "memory.sqlite"),
    )
    manager = MemoryManagementService(
        project_store=store, memory_repository=repository, config=config
    )
    consolidator = MemoryConsolidationService(
        project_store=store, memory_repository=repository
    )
    return store, repository, manager, consolidator, project_id


def _review(manager, repository, project_id: str, command_suffix: str, value: str):
    remembered = manager.remember(
        project_id=project_id,
        command_id=f"phase-c-remember-{command_suffix}",
        principal="desktop-local-user",
        kind="project_decision",
        key="atlas",
        value={"atlas_id": value},
        summary=f"Use {value}.",
        impact_class="scientific",
    )
    candidate = repository.get_candidate(
        project_id=project_id, candidate_id=remembered["candidate_id"]
    )
    assert candidate is not None
    manager.review_candidate(
        project_id=project_id,
        candidate_id=candidate.candidate_id,
        command_id=f"phase-c-accept-{command_suffix}",
        principal="desktop-local-user",
        accept=True,
        expected_candidate_version=candidate.candidate_version,
        candidate_hash=candidate.candidate_hash,
    )
    return candidate.candidate_id


def test_accepted_candidate_adds_then_supersedes_same_logical_item(tmp_path: Path) -> None:
    _store, repository, manager, consolidator, project_id = _setup(tmp_path)
    _review(manager, repository, project_id, "0001", "atlas-a")
    first = consolidator.consolidate_project(project_id=project_id)
    assert len(first["selection_diff"]["added"]) == 1
    item = repository.list_items(project_id=project_id)[0]
    assert item.revision.content == {"atlas_id": "atlas-a"}

    _review(manager, repository, project_id, "0002", "atlas-b")
    second = consolidator.consolidate_project(project_id=project_id)
    assert second["selection_diff"]["superseded"] == [item.memory_id]
    updated = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    assert updated is not None
    assert updated.revision.revision_number == 2
    assert updated.revision.content == {"atlas_id": "atlas-b"}
    assert len(repository.list_items(project_id=project_id)) == 1


def test_pinned_item_is_not_overwritten_and_candidate_returns_to_review(tmp_path: Path) -> None:
    _store, repository, manager, consolidator, project_id = _setup(tmp_path)
    _review(manager, repository, project_id, "pin-0001", "atlas-a")
    consolidator.consolidate_project(project_id=project_id)
    item = repository.list_items(project_id=project_id)[0]
    manager.set_pinned(
        project_id=project_id,
        memory_id=item.memory_id,
        command_id="phase-c-pin-command-0001",
        principal="desktop-local-user",
        expected_item_version=item.item_version,
        pinned=True,
    )
    candidate_id = _review(manager, repository, project_id, "pin-0002", "atlas-b")
    result = consolidator.consolidate_project(project_id=project_id)
    assert result["selection_diff"]["needs_review"] == [candidate_id]
    unchanged = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    assert unchanged is not None
    assert unchanged.revision.content == {"atlas_id": "atlas-a"}
    candidate = repository.get_candidate(project_id=project_id, candidate_id=candidate_id)
    assert candidate is not None and candidate.status == "proposed"


def test_stale_fencing_token_cannot_commit_after_new_owner_claims(tmp_path: Path) -> None:
    _store, repository, manager, _consolidator, project_id = _setup(tmp_path)
    _review(manager, repository, project_id, "lease-0001", "atlas-a")
    first = repository.claim_project_lease(
        project_id=project_id, owner="worker-old", ttl_seconds=5
    )
    with sqlite3.connect(repository.db_path) as conn:
        conn.execute(
            "UPDATE memory_leases SET lease_expires_at='2000-01-01T00:00:00Z' WHERE project_id=?",
            (project_id,),
        )
    second = repository.claim_project_lease(
        project_id=project_id, owner="worker-new", ttl_seconds=60
    )
    assert second["fencing_token"] > first["fencing_token"]
    with pytest.raises(MemoryRepositoryError) as error:
        repository.consolidate_accepted(
            project_id=project_id,
            consent_epoch=1,
            owner="worker-old",
            fencing_token=first["fencing_token"],
        )
    assert error.value.code == "MEMORY_CONSOLIDATION_LEASE_STALE"


def test_candidate_review_uses_optimistic_version_and_idempotent_command(
    tmp_path: Path,
) -> None:
    _store, repository, manager, _consolidator, project_id = _setup(tmp_path)
    remembered = manager.remember(
        project_id=project_id,
        command_id="phase-c-review-remember-0001",
        principal="desktop-local-user",
        kind="workflow_lesson",
        key="missing-input",
        value={"code": "MISSING_INPUT"},
        summary="Check inputs first.",
        impact_class="workflow",
    )
    candidate = repository.get_candidate(
        project_id=project_id, candidate_id=remembered["candidate_id"]
    )
    assert candidate is not None
    kwargs = dict(
        project_id=project_id,
        candidate_id=candidate.candidate_id,
        command_id="phase-c-review-accept-0001",
        principal="desktop-local-user",
        accept=True,
        expected_candidate_version=candidate.candidate_version,
        candidate_hash=candidate.candidate_hash,
    )
    first = manager.review_candidate(**kwargs)
    assert manager.review_candidate(**kwargs) == first
    with pytest.raises(MemoryRepositoryError):
        manager.review_candidate(
            **{**kwargs, "command_id": "phase-c-review-accept-stale"}
        )

