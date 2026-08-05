from __future__ import annotations

from src.backend.app.services.mock_store import SQLiteDesktopStore


def test_fresh_desktop_store_does_not_seed_demo_records_by_default(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("MEDIMAGE_DESKTOP_SEED_DEMO_DATA", raising=False)

    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")

    assert store.list_projects() == []
    assert store.list_tasks() == []


def test_fresh_desktop_store_can_seed_demo_records_when_explicitly_enabled(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("MEDIMAGE_DESKTOP_SEED_DEMO_DATA", "true")

    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")

    assert store.get_project("brain-tumor-study") is not None
    assert any(task.id == "task-001" for task in store.list_tasks())
