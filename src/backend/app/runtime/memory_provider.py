"""MemoryProvider protocol -- pluggable memory backends."""
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

    def read_global(self, key: str) -> str | None:
        """Read a global memory entry (MEMORY.md, USER.md, ERROR_KB.yaml)."""
        ...

    def write_global(self, key: str, content: str) -> None:
        """Write a global memory entry."""
        ...

    def read_project(self, project_name: str, key: str) -> str | None:
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
