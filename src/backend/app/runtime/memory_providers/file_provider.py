"""FileMemoryProvider -- file-system based memory backend (current behavior)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FileMemoryProvider:
    def __init__(self, root_dir: str = "."):
        self._root_dir = Path(root_dir)
        self._global_dir = self._root_dir / "memory" / "global"
        self._projects_dir = self._root_dir / "memory" / "projects"
        self._sessions_dir = self._root_dir / "memory" / "sessions"

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @root_dir.setter
    def root_dir(self, value: Path) -> None:
        self._root_dir = Path(value)
        self._global_dir = self._root_dir / "memory" / "global"
        self._projects_dir = self._root_dir / "memory" / "projects"
        self._sessions_dir = self._root_dir / "memory" / "sessions"

    # --- MemoryProvider interface ---

    def initialize(self) -> None:
        self._global_dir.mkdir(parents=True, exist_ok=True)
        self._projects_dir.mkdir(parents=True, exist_ok=True)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

        defaults = {
            "MEMORY.md": "# MedImage Agent Memory\n",
            "USER.md": "# User Memory\n",
            "ENVIRONMENT.md": "# Environment Memory\n",
        }
        for filename, content in defaults.items():
            path = self._global_dir / filename
            if not path.exists():
                path.write_text(content, encoding="utf-8")

    def read_global(self, key: str) -> str | None:
        path = self._global_dir / key
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def write_global(self, key: str, content: str) -> None:
        (self._global_dir / key).write_text(content, encoding="utf-8")

    def read_project(self, project_name: str, key: str) -> str | None:
        proj_dir = self._get_project_dir(project_name)
        path = proj_dir / key
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def write_project(self, project_name: str, key: str, content: str) -> None:
        proj_dir = self._get_project_dir(project_name)
        (proj_dir / key).write_text(content, encoding="utf-8")

    def append_event(self, project_name: str, event: dict[str, Any]) -> None:
        proj_dir = self._get_project_dir(project_name)
        history_path = proj_dir / "RUN_HISTORY.jsonl"

        safe = dict(event)
        safe.pop("raw_patient_data", None)
        safe.pop("phi", None)

        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe, ensure_ascii=False) + "\n")

    def query_events(
        self, project_name: str, filters: dict[str, Any] | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        proj_dir = self._get_project_dir(project_name)
        history_path = proj_dir / "RUN_HISTORY.jsonl"
        if not history_path.exists():
            return []

        results = []
        for line in history_path.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if filters:
                if all(record.get(k) == v for k, v in filters.items()):
                    results.append(record)
            else:
                results.append(record)
            if len(results) >= limit:
                break
        return results

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        qlower = query.lower()
        for proj_dir in self._projects_dir.iterdir():
            if not proj_dir.is_dir():
                continue
            history_path = proj_dir / "RUN_HISTORY.jsonl"
            if not history_path.exists():
                continue
            for line in history_path.read_text(encoding="utf-8").strip().splitlines():
                if qlower in line.lower():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                if len(results) >= limit:
                    return results
        return results

    def sync(self) -> None:
        pass  # no-op for file provider

    def shutdown(self) -> None:
        pass  # no-op for file provider

    # --- Helpers ---

    def _sanitize(self, name: str) -> str:
        return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name) or "default_project"

    def _get_project_dir(self, project_name: str) -> Path:
        self.initialize()
        proj_dir = self._projects_dir / self._sanitize(project_name)
        proj_dir.mkdir(parents=True, exist_ok=True)

        project_md = proj_dir / "PROJECT.md"
        lessons_md = proj_dir / "LESSONS.md"
        if not project_md.exists():
            project_md.write_text(f"# Project Memory: {project_name}\n", encoding="utf-8")
        if not lessons_md.exists():
            lessons_md.write_text(f"# Lessons: {project_name}\n", encoding="utf-8")
        return proj_dir
