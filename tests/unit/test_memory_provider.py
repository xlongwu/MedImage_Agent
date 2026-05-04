from pathlib import Path

from src.backend.app.runtime.memory_store import (
    get_provider,
    set_provider,
    append_run_history,
    ensure_memory_layout,
    sanitize_project_name,
)
from src.backend.app.runtime.memory_provider import MemoryProvider
from src.backend.app.runtime.memory_providers.file_provider import FileMemoryProvider
from src.backend.app.runtime.memory_providers.sqlite_provider import SQLiteMemoryProvider


def test_file_provider_roundtrip(tmp_path: Path):
    provider = FileMemoryProvider(root_dir=str(tmp_path))
    provider.initialize()
    provider.write_global("TEST.md", "# Test content")
    result = provider.read_global("TEST.md")
    assert result is not None
    assert "# Test content" in result
    provider.shutdown()


def test_file_provider_append_and_query(tmp_path: Path):
    provider = FileMemoryProvider(root_dir=str(tmp_path))
    provider.initialize()
    provider.append_event("proj1", {"run_id": "r1", "status": "SUCCESS"})
    provider.append_event("proj1", {"run_id": "r2", "status": "FAILED"})
    events = provider.query_events("proj1")
    assert len(events) == 2


def test_sqlite_provider_roundtrip(tmp_path: Path):
    provider = SQLiteMemoryProvider(db_path=str(tmp_path / "test.sqlite"))
    provider.initialize()
    provider.write_global("TEST.md", "# Test SQLite content")
    result = provider.read_global("TEST.md")
    assert result is not None
    provider.append_event("test_project", {"run_id": "r1", "status": "SUCCESS"})
    events = provider.query_events("test_project")
    assert len(events) >= 1
    provider.shutdown()


def test_provider_swap_preserves_backward_compat(tmp_path: Path):
    # Default is FileMemoryProvider
    provider = get_provider()
    assert isinstance(provider, MemoryProvider)

    # Swap to SQLite
    sqlite = SQLiteMemoryProvider(db_path=str(tmp_path / "swap.sqlite"))
    set_provider(sqlite)
    append_run_history("proj", {"run_id": "r99", "ok": True})
    current = get_provider()
    assert isinstance(current, SQLiteMemoryProvider)
    current.shutdown()

    # Restore default
    set_provider(FileMemoryProvider())


def test_existing_memory_store_functions_still_work(tmp_path: Path):
    layout = ensure_memory_layout(str(tmp_path))
    assert "global_dir" in layout
    assert "projects_dir" in layout

    safe = sanitize_project_name("my project!")
    assert " " not in safe

    path = append_run_history("test_proj", {"run_id": "x1", "status": "OK"}, str(tmp_path))
    assert path.parent.exists()
