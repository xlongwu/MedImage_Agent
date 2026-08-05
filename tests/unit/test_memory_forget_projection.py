from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from src.backend.app.core.config_schema import MemoryConfig
from src.backend.app.services.memory_maintenance_service import MemoryMaintenanceService
from src.backend.app.services.memory_management_service import MemoryManagementService
from src.backend.app.services.memory_projection_service import MemoryProjectionService
from src.backend.app.services.memory_repository import MemoryRepository
from src.backend.app.services.memory_repository import MemoryRepositoryError
from src.backend.app.services.mock_store import SQLiteDesktopStore


def _setup(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    store = SQLiteDesktopStore(tmp_path / "desktop.sqlite")
    project_id = store.list_projects()[0].id
    store.update_project_metadata(
        project_id,
        {
            "project_dir": str(project_root),
            "rawdata_dir": str(project_root / "rawdata"),
        },
    )
    store.set_memory_consent(
        project_id=project_id,
        command_id="phase-c-forget-consent-0001",
        principal="desktop-local-user",
        generate_enabled=True,
        use_enabled=True,
    )
    repository = MemoryRepository(tmp_path / "memory.sqlite")
    config = MemoryConfig(
        enabled=True,
        generation_enabled=True,
        use_enabled=True,
        projection_enabled=False,
        store_path=str(tmp_path / "memory.sqlite"),
    )
    manager = MemoryManagementService(
        project_store=store, memory_repository=repository, config=config
    )
    return project_root, store, repository, manager, config, project_id


def _active_preference(manager, repository, project_id: str, summary: str):
    result = manager.remember(
        project_id=project_id,
        command_id="phase-c-active-preference-0001",
        principal="desktop-local-user",
        kind="presentation_preference",
        key="language",
        value={"language": "zh-CN", "marker": "FORGET_ME_9A71"},
        summary=summary,
        impact_class="presentation",
    )
    item = repository.get_item(project_id=project_id, memory_id=result["memory_id"])
    assert item is not None
    return item


def test_forget_scrubs_all_plaintext_fts_and_prevents_automatic_resurrection(
    tmp_path: Path,
) -> None:
    _root, store, repository, manager, _config, project_id = _setup(tmp_path)
    item = _active_preference(manager, repository, project_id, "Use Chinese FORGET_ME_9A71.")
    result = manager.forget(
        project_id=project_id,
        memory_id=item.memory_id,
        command_id="phase-c-forget-command-0001",
        principal="desktop-local-user",
        expected_item_version=item.item_version,
        expected_revision_hash=item.revision.content_hash,
    )
    forgotten = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    assert result["status"] == "forgotten"
    assert forgotten is not None and forgotten.status == "forgotten"
    assert forgotten.revision.content == {}
    assert forgotten.revision.content_text == ""
    with repository.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM memory_fts WHERE memory_id=?", (item.memory_id,)
        ).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM memory_tombstones").fetchone()[0] == 1
    suppressed = repository.remember_explicit(
        project_id=project_id,
        command_id="phase-c-forget-replay-0001",
        principal="desktop-local-user",
        kind="presentation_preference",
        key="language",
        value={"language": "zh-CN"},
        summary="Use Chinese.",
        impact_class="presentation",
        consent_epoch=1,
    )
    assert suppressed["status"] == "suppressed"
    repository.vacuum()
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(repository.db_path) + suffix)
        if path.exists():
            assert b"FORGET_ME_9A71" not in path.read_bytes()
    assert len(store.list_memory_forget_ledger(project_id)) == 1


def test_forget_fails_closed_until_wal_truncation_succeeds(tmp_path: Path) -> None:
    _root, store, repository, manager, _config, project_id = _setup(tmp_path)
    marker = "WAL_BLOCKED_FORGET_MARKER_5C17"
    item = _active_preference(manager, repository, project_id, f"Use Chinese {marker}.")
    reader = sqlite3.connect(repository.db_path, isolation_level=None)
    reader.execute("PRAGMA journal_mode=WAL")
    reader.execute("BEGIN")
    reader.execute(
        "SELECT content_text FROM memory_revisions WHERE memory_id=?", (item.memory_id,)
    ).fetchone()
    with repository.connect(immediate=True) as conn:
        conn.execute(
            "UPDATE memory_revisions SET content_text=? WHERE memory_id=?",
            (marker, item.memory_id),
        )

    try:
        with pytest.raises(MemoryRepositoryError) as blocked:
            manager.forget(
                project_id=project_id,
                memory_id=item.memory_id,
                command_id="phase-c-wal-forget-0001",
                principal="desktop-local-user",
                expected_item_version=item.item_version,
                expected_revision_hash=item.revision.content_hash,
            )
        assert blocked.value.code == "MEMORY_FORGET_WAL_TRUNCATION_FAILED"
        wal_path = Path(f"{repository.db_path}-wal")
        assert wal_path.exists()
        assert marker.encode("utf-8") in wal_path.read_bytes()
    finally:
        reader.close()

    recovered = manager.forget(
        project_id=project_id,
        memory_id=item.memory_id,
        command_id="phase-c-wal-forget-0001",
        principal="desktop-local-user",
        expected_item_version=item.item_version,
        expected_revision_hash=item.revision.content_hash,
    )
    assert recovered["status"] == "forgotten"
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{repository.db_path}{suffix}")
        if path.exists():
            assert marker.encode("utf-8") not in path.read_bytes()
    assert len(store.list_memory_forget_ledger(project_id)) == 1


def test_explicit_restore_creates_higher_generation_and_keeps_tombstone(
    tmp_path: Path,
) -> None:
    _root, _store, repository, manager, _config, project_id = _setup(tmp_path)
    item = _active_preference(manager, repository, project_id, "Use Chinese.")
    manager.forget(
        project_id=project_id,
        memory_id=item.memory_id,
        command_id="phase-c-restore-forget-0001",
        principal="desktop-local-user",
        expected_item_version=item.item_version,
        expected_revision_hash=item.revision.content_hash,
    )
    forgotten = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    assert forgotten is not None
    result = manager.restore(
        project_id=project_id,
        memory_id=item.memory_id,
        command_id="phase-c-restore-command-0001",
        principal="desktop-local-user",
        expected_item_version=forgotten.item_version,
        expected_revision_hash=forgotten.revision.content_hash,
        value={"language": "en"},
        summary="Use English.",
    )
    restored = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    assert restored is not None and restored.status == "active"
    assert restored.generation == 1
    assert result["generation"] == 1
    with repository.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM memory_tombstones").fetchone()[0] == 1


def test_projection_is_explicit_atomic_rebuildable_and_checksum_guarded(
    tmp_path: Path,
) -> None:
    project_root, store, repository, manager, config, project_id = _setup(tmp_path)
    _active_preference(manager, repository, project_id, "Use Chinese.")
    service = MemoryProjectionService(
        project_store=store, memory_repository=repository, config=config
    )
    with pytest.raises(MemoryRepositoryError) as disabled:
        service.rebuild(project_id=project_id)
    assert disabled.value.code == "MEMORY_PROJECTION_DISABLED"
    rebuilt = service.rebuild(project_id=project_id, explicit_approved=True)
    target = project_root / "work" / "memory"
    assert Path(rebuilt["projection_dir"]) == target.resolve()
    assert service.verify(project_id=project_id)["ok"] is True
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["_schema_version"] == "memory-projection-v1"
    assert manifest["checksums"]["MEMORY.md"] == hashlib.sha256(
        (target / "MEMORY.md").read_bytes()
    ).hexdigest()

    (target / "MEMORY.md").write_text("tampered", encoding="utf-8")
    assert service.verify(project_id=project_id)["error_code"] == (
        "MEMORY_PROJECTION_CHECKSUM_MISMATCH"
    )
    service.rebuild(project_id=project_id, explicit_approved=True)
    assert service.verify(project_id=project_id)["ok"] is True


def test_maintenance_completes_desktop_first_forget_saga(tmp_path: Path) -> None:
    _root, store, repository, manager, _config, project_id = _setup(tmp_path)
    item = _active_preference(manager, repository, project_id, "Use Chinese.")
    ledger = store.append_memory_forget_ledger(
        project_id=project_id,
        command_id="phase-c-crash-forget-0001",
        principal="desktop-local-user",
        canonical_key=item.canonical_key,
        semantic_fingerprint="semantic-hash",
        source_lineage_fingerprints=[],
        content_hash=item.revision.content_hash,
        forget_outbox_sequence=store.get_memory_outbox_max_sequence(project_id),
        generation=item.generation,
    )
    assert ledger["forget_epoch"] == 1
    result = MemoryMaintenanceService(
        project_store=store, memory_repository=repository
    ).reconcile_project(project_id=project_id)
    assert result["forget_sagas_completed"] == 1
    forgotten = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    assert forgotten is not None and forgotten.status == "forgotten"


def test_projection_failure_does_not_rollback_or_corrupt_database(
    monkeypatch, tmp_path: Path
) -> None:
    _root, store, repository, manager, config, project_id = _setup(tmp_path)
    item = _active_preference(manager, repository, project_id, "Use Chinese.")
    service = MemoryProjectionService(
        project_store=store, memory_repository=repository, config=config
    )

    def fail_write(*_args, **_kwargs):
        raise OSError("locked")

    monkeypatch.setattr(
        "src.backend.app.services.memory_projection_service.atomic_write_text",
        fail_write,
    )
    with pytest.raises(OSError, match="locked"):
        service.rebuild(project_id=project_id, explicit_approved=True)
    persisted = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    assert persisted is not None and persisted.status == "active"


def test_maintenance_expires_due_items_and_scrubs_old_epoch_candidates(
    tmp_path: Path,
) -> None:
    _root, store, repository, manager, _config, project_id = _setup(tmp_path)
    item = _active_preference(manager, repository, project_id, "Use Chinese.")
    proposed = manager.remember(
        project_id=project_id,
        command_id="phase-c-stale-candidate-0001",
        principal="desktop-local-user",
        kind="workflow_lesson",
        key="temporary-lesson",
        value={"code": "TEMPORARY"},
        summary="Temporary lesson.",
        impact_class="workflow",
    )
    with repository.connect(immediate=True) as conn:
        conn.execute(
            "UPDATE memory_items SET valid_until='2000-01-01T00:00:00Z' WHERE memory_id=?",
            (item.memory_id,),
        )
    store.set_memory_consent(
        project_id=project_id,
        command_id="phase-c-forget-consent-0002",
        principal="desktop-local-user",
        generate_enabled=True,
        use_enabled=True,
    )
    result = MemoryMaintenanceService(
        project_store=store, memory_repository=repository
    ).reconcile_project(project_id=project_id)
    assert result["items_expired"] == 1
    assert result["stale_candidates_scrubbed"] == 1
    expired = repository.get_item(project_id=project_id, memory_id=item.memory_id)
    candidate = repository.get_candidate(
        project_id=project_id, candidate_id=proposed["candidate_id"]
    )
    assert expired is not None and expired.status == "expired"
    assert candidate is not None and candidate.status == "suppressed"
    assert candidate.content == {}


def test_configured_candidate_retention_expires_and_scrubs_plaintext(
    tmp_path: Path,
) -> None:
    _root, store, repository, manager, _config, project_id = _setup(tmp_path)
    proposed = manager.remember(
        project_id=project_id,
        command_id="phase-c-expiring-candidate-0001",
        principal="desktop-local-user",
        kind="workflow_lesson",
        key="short-lived-lesson",
        value={"code": "SHORT_LIVED"},
        summary="Short-lived workflow lesson.",
        impact_class="workflow",
    )
    before = repository.get_candidate(
        project_id=project_id, candidate_id=proposed["candidate_id"]
    )
    assert before is not None and before.expires_at is not None
    with repository.connect(immediate=True) as conn:
        conn.execute(
            "UPDATE memory_candidates SET expires_at='2000-01-01T00:00:00Z' WHERE candidate_id=?",
            (proposed["candidate_id"],),
        )

    result = MemoryMaintenanceService(
        project_store=store, memory_repository=repository
    ).reconcile_project(project_id=project_id)

    assert result["candidates_expired"] == 1
    expired = repository.get_candidate(
        project_id=project_id, candidate_id=proposed["candidate_id"]
    )
    assert expired is not None and expired.status == "expired"
    assert expired.content == {}
    assert expired.content_text == ""
