from __future__ import annotations

from src.backend.app.services.mock_store import SQLiteDesktopStore


def test_empty_rawdata_path_is_not_registered_as_import_root(tmp_path):
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    project = store.get_project("brain-tumor-study")
    assert project is not None

    store.add_project(project, health_status="Review", rawdata_dir="", overwrite=True)

    assert "" not in store.list_import_paths(project.id)
    assert all(record["path"] for record in store.list_import_records(project.id))


def test_blank_import_record_is_reported_missing_and_filtered_from_paths(tmp_path):
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    with store._lock, store._connect() as conn:
        conn.execute(
            """
            INSERT INTO imports (dataset_id, project_id, path, dataset_type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("blank-import", "brain-tumor-study", "   ", "bids", "2026-06-28T00:00:00Z"),
        )

    assert "   " not in store.list_import_paths("brain-tumor-study")
    blank_record = next(
        item for item in store.list_import_records("brain-tumor-study")
        if item["dataset_id"] == "blank-import"
    )
    assert blank_record["exists"] is False
