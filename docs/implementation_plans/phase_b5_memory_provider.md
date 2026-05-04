# Phase B5：MemoryProvider 抽象

> 目标版本：v0.2.0 | 预计工期：2–3 天 | 前置条件：Phase B1 SessionDB 完成

---

## 1. 目标与范围

将当前基于文件系统的 `memory_store.py` 抽象为 `MemoryProvider` 协议接口，提供 `FileMemoryProvider` 和 `SQLiteMemoryProvider` 两个实现。当前行为保持不变。

**不做**：外部 provider 集成（Postgres、cloud storage）、自动 provider 切换。

---

## 2. 前置条件检查

- [ ] `memory_store.py` 当前使用文件系统直接读写
- [ ] Phase B1 SessionDB 可用

---

## 3. 新增/修改文件清单

```text
backend/app/runtime/memory_provider.py        # 新增：MemoryProvider 协议接口
backend/app/runtime/memory_providers/         # 新增目录
  __init__.py
  file_provider.py                             # 新增：FileMemoryProvider（当前行为）
  sqlite_provider.py                           # 新增：SQLiteMemoryProvider（基于 SessionDB）
backend/app/runtime/memory_store.py            # 修改：使用 Provider 而非直接文件操作
tests/unit/test_memory_provider.py             # 新增：测试
```

---

## 4. 协议接口设计

文件：`backend/app/runtime/memory_provider.py`

```python
"""MemoryProvider protocol — pluggable memory backends."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryProvider(Protocol):
    """Protocol for memory storage backends.

    Concrete implementations:
      - FileMemoryProvider (current behavior, file-system based)
      - SQLiteMemoryProvider (SessionDB-backed)
    """

    def initialize(self) -> None:
        """Set up storage (create directories, tables, etc.)."""
        ...

    def read_global(self, key: str) -> dict[str, Any] | None:
        """Read a global memory entry (MEMORY.md, USER.md, ERROR_KB.yaml)."""
        ...

    def write_global(self, key: str, content: str) -> None:
        """Write a global memory entry."""
        ...

    def read_project(self, project_name: str, key: str) -> dict[str, Any] | None:
        """Read a project-scoped memory entry."""
        ...

    def write_project(self, project_name: str, key: str, content: str) -> None:
        """Write a project-scoped memory entry."""
        ...

    def append_event(self, project_name: str, event: dict[str, Any]) -> None:
        """Append a run history event to project memory."""
        ...

    def query_events(
        self, project_name: str, filters: dict[str, Any] | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Query project events with optional filters."""
        ...

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Full-text search across all memory."""
        ...

    def sync(self) -> None:
        """Flush pending writes."""
        ...

    def shutdown(self) -> None:
        """Close connections, clean up."""
        ...
```

### FileMemoryProvider

文件：`backend/app/runtime/memory_providers/file_provider.py`

本质是当前 `memory_store.py` 的所有逻辑，封装为 `MemoryProvider` 协议。包含：
- `initialize()` → `ensure_memory_layout()`
- `read_global(key)` → 读 `memory/global/{key}`
- `write_global(key, content)` → 写 `memory/global/{key}`
- `read_project(project_name, key)` → 读 `memory/projects/{name}/{key}`
- `write_project(project_name, key, content)` → 写 `memory/projects/{name}/{key}`
- `append_event(project_name, event)` → `append_run_history()`
- `search()` → 遍历所有 JSONL 文件做 grep（简单实现）
- `sync()` / `shutdown()` → no-op

### SQLiteMemoryProvider

文件：`backend/app/runtime/memory_providers/sqlite_provider.py`

基于 Phase B1 的 `SessionDB`，提供相同的 `MemoryProvider` 接口：
- `initialize()` → 创建 SessionDB 和表
- `read_global(key)` → 从 `documents` 表查 `record_type='global'`
- `write_global(key, content)` → upsert 到 `documents` 表
- `append_event(project_name, event)` → `insert_node()` + `index_document()`
- `search(query)` → FTS5 `db.search(query)`
- `shutdown()` → `db.close()`

---

## 5. 修改 memory_store.py

```python
"""Memory store — uses configured MemoryProvider backend."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.runtime.memory_provider import MemoryProvider
from backend.app.runtime.memory_providers.file_provider import FileMemoryProvider


_default_provider: MemoryProvider | None = None


def get_provider() -> MemoryProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = FileMemoryProvider()
        _default_provider.initialize()
    return _default_provider


def set_provider(provider: MemoryProvider) -> None:
    global _default_provider
    if _default_provider:
        _default_provider.shutdown()
    _default_provider = provider
    provider.initialize()


# Keep existing function signatures as convenience wrappers:
def ensure_memory_layout(root_dir: str = ".") -> dict[str, str]:
    return get_provider().initialize()  # simplified

def append_run_history(project_name: str, record: dict[str, Any], root_dir: str = ".") -> None:
    get_provider().append_event(project_name, record)

# ... etc. Each existing function delegates to get_provider()
```

---

## 6. 测试

```python
def test_file_provider_roundtrip(tmp_path: Path):
    from backend.app.runtime.memory_providers.file_provider import FileMemoryProvider

    provider = FileMemoryProvider(root_dir=str(tmp_path))
    provider.initialize()
    provider.write_global("TEST.md", "# Test content")
    result = provider.read_global("TEST.md")
    assert result is not None
    provider.shutdown()


def test_sqlite_provider_roundtrip(tmp_path: Path):
    from backend.app.runtime.memory_providers.sqlite_provider import SQLiteMemoryProvider

    provider = SQLiteMemoryProvider(db_path=str(tmp_path / "test.sqlite"))
    provider.initialize()
    provider.write_global("TEST.md", "# Test SQLite content")
    result = provider.read_global("TEST.md")
    assert result is not None
    provider.append_event("test_project", {"run_id": "r1", "status": "SUCCESS"})
    events = provider.query_events("test_project")
    assert len(events) >= 1
    provider.shutdown()


def test_provider_swap(tmp_path: Path):
    from backend.app.runtime.memory_store import set_provider, get_provider, append_run_history
    from backend.app.runtime.memory_providers.sqlite_provider import SQLiteMemoryProvider

    sqlite = SQLiteMemoryProvider(db_path=str(tmp_path / "swap.sqlite"))
    set_provider(sqlite)
    append_run_history("proj", {"run_id": "r99", "ok": True})
    assert isinstance(get_provider(), SQLiteMemoryProvider)
    get_provider().shutdown()
```

---

## 7. 验收标准

- [ ] `MemoryProvider` 协议定义 8 个方法
- [ ] `FileMemoryProvider` 保持当前行为不变
- [ ] `SQLiteMemoryProvider` 基于 SessionDB 实现相同接口
- [ ] `memory_store.py` 的现有公开函数仍然可用（向后兼容）
- [ ] 可通过 `set_provider()` 切换 provider
- [ ] 3 个单元测试通过
- [ ] 现有 `test_memory_store.py` 测试仍然通过
