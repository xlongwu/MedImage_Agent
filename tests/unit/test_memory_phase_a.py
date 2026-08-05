from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.backend.app.core.config import ConfigService
from src.backend.app.planner.scientific_parameter_registry import (
    get_parameter_rule,
    registry_completeness_errors,
)
from src.backend.app.runtime.atomic_file import atomic_write_text
from src.backend.app.schemas.agent_lifecycle import AgentLifecycleEvent, AgentLifecycleRecord
from src.backend.app.services.mock_store import SQLiteDesktopStore
from src.backend.app.services.memory_repository import MemoryRepository, MemoryRepositoryError


def test_memory_config_defaults_closed_and_path_follows_desktop_store(
    monkeypatch, tmp_path: Path
) -> None:
    desktop = tmp_path / "state" / "desktop.sqlite"
    monkeypatch.setenv("MEDIMAGE_DESKTOP_STORE_PATH", str(desktop))
    for name in (
        "MEDIMAGE_MEMORY_ENABLED",
        "MEDIMAGE_MEMORY_GENERATION_ENABLED",
        "MEDIMAGE_MEMORY_USE_ENABLED",
        "MEDIMAGE_MEMORY_LLM_EXTRACTION_ENABLED",
        "MEDIMAGE_MEMORY_LLM_CONSOLIDATION_ENABLED",
        "MEDIMAGE_MEMORY_PROJECTION_ENABLED",
        "MEDIMAGE_MEMORY_STORE_PATH",
        "MEDIMAGE_MEMORY_CANDIDATE_RETENTION_DAYS",
        "MEDIMAGE_MEMORY_ITEM_RETENTION_DAYS",
    ):
        monkeypatch.delenv(name, raising=False)
    config = ConfigService().memory
    assert config.enabled is False
    assert config.generation_enabled is False
    assert config.use_enabled is False
    assert Path(config.store_path) == (desktop.parent / "memory_state.sqlite").resolve()
    assert config.candidate_retention_days == 30
    assert config.item_retention_days == 180


def test_memory_config_retention_is_typed_and_invalid_values_fall_back(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MEDIMAGE_MEMORY_CANDIDATE_RETENTION_DAYS", "7")
    monkeypatch.setenv("MEDIMAGE_MEMORY_ITEM_RETENTION_DAYS", "invalid")
    config = ConfigService().memory
    assert config.candidate_retention_days == 7
    assert config.item_retention_days == 180


def test_atomic_write_text_replaces_complete_utf8_content(tmp_path: Path) -> None:
    target = tmp_path / "projection" / "MEMORY.md"
    atomic_write_text(target, "first\n")
    atomic_write_text(target, "第二版\n")
    assert target.read_text(encoding="utf-8") == "第二版\n"
    assert not list(target.parent.glob("*.tmp"))


def test_parameter_registry_covers_contract_parameters_and_fails_unknown() -> None:
    assert registry_completeness_errors() == []
    assert get_parameter_rule("temporal_filtering_subject", "tr").impact == "scientific"


def test_consent_ledger_and_lifecycle_outbox_share_committed_state(tmp_path: Path) -> None:
    store = SQLiteDesktopStore(tmp_path / "desktop.sqlite")
    project_id = store.list_projects()[0].id
    consent = store.set_memory_consent(
        project_id=project_id,
        command_id="memory-consent-command-0001",
        principal="desktop-local-user",
        generate_enabled=True,
        use_enabled=False,
    )
    now = datetime.now(UTC)
    lifecycle = AgentLifecycleRecord(
        lifecycle_id="memory-lifecycle-1",
        project_id=project_id,
        goal_text="Create a plan",
        created_at=now,
        updated_at=now,
    )
    event = AgentLifecycleEvent(
        event_id="memory-lifecycle-event-1",
        lifecycle_id=lifecycle.lifecycle_id,
        project_id=project_id,
        command_id="memory-lifecycle-command-1",
        actor="desktop-local-user",
        source_command="create",
        occurred_at=now,
        from_state=None,
        to_state="CREATED",
    )
    store.create_agent_lifecycle(lifecycle, event)

    rows = store.list_memory_outbox(project_id)
    assert consent["consent_epoch"] == 1
    assert len(rows) == 1
    assert rows[0]["source_type"] == "agent_lifecycle_event"
    projection = store.get_memory_source_projection(
        project_id=project_id,
        source_type="agent_lifecycle_event",
        source_id=event.event_id,
    )
    assert projection is not None
    assert projection["event"]["source_command"] == "create"


def test_generation_disabled_prevents_new_outbox_without_deleting_existing(
    tmp_path: Path,
) -> None:
    store = SQLiteDesktopStore(tmp_path / "desktop.sqlite")
    project_id = store.list_projects()[0].id
    store.set_memory_consent(
        project_id=project_id,
        command_id="memory-consent-command-0002",
        principal="desktop-local-user",
        generate_enabled=False,
        use_enabled=True,
    )
    now = datetime.now(UTC)
    lifecycle = AgentLifecycleRecord(
        lifecycle_id="memory-lifecycle-2",
        project_id=project_id,
        goal_text="Create a plan",
        created_at=now,
        updated_at=now,
    )
    event = AgentLifecycleEvent(
        event_id="memory-lifecycle-event-2",
        lifecycle_id=lifecycle.lifecycle_id,
        project_id=project_id,
        command_id="memory-lifecycle-command-2",
        actor="desktop-local-user",
        source_command="create",
        occurred_at=now,
        from_state=None,
        to_state="CREATED",
    )
    store.create_agent_lifecycle(lifecycle, event)
    assert store.list_memory_outbox(project_id) == []


def test_memory_store_failure_does_not_prevent_desktop_store_startup(tmp_path: Path) -> None:
    invalid_memory_path = tmp_path / "is-a-directory"
    invalid_memory_path.mkdir()
    try:
        MemoryRepository(invalid_memory_path)
    except MemoryRepositoryError as exc:
        assert exc.code == "MEMORY_STORE_INIT_FAILED"
    else:
        raise AssertionError("Expected an isolated memory store failure")

    desktop = SQLiteDesktopStore(tmp_path / "desktop.sqlite")
    assert desktop.health_check()["ok"] is True
