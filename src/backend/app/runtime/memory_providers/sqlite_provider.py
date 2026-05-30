"""SQLiteMemoryProvider -- SessionDB-backed memory backend."""
from __future__ import annotations

import json
from typing import Any


class SQLiteMemoryProvider:
    def __init__(self, db_path: str = "outputs/memory/sessions/archive.sqlite"):
        self.db_path = db_path
        self._db = None
        self._globals: dict[str, str] = {}
        self._projects: dict[str, dict[str, str]] = {}

    def _get_db(self):
        if self._db is None:
            from src.backend.app.memory.session_db import SessionDB
            self._db = SessionDB(self.db_path)
            self._db.stats()  # ensure tables exist
        return self._db

    # --- MemoryProvider interface ---

    def initialize(self) -> None:
        _ = self._get_db()

    def read_global(self, key: str) -> str | None:
        if key in self._globals:
            return self._globals[key]
        # Fallback: try FTS
        db = self._get_db()
        query = key.replace(".md", "").replace(".yaml", "").replace("_", " ")
        try:
            results = db.search(query, limit=5)
            for r in results:
                if r.get("record_type") == "global" and r.get("record_id") == key:
                    return r.get("title", "")
        except Exception:
            pass
        return None

    def write_global(self, key: str, content: str) -> None:
        self._globals[key] = content
        db = self._get_db()
        try:
            db.index_document(key, "global", key, content)
        except Exception:
            pass

    def read_project(self, project_name: str, key: str) -> str | None:
        pkey = f"{project_name}/{key}"
        return self._projects.get(project_name, {}).get(key)

    def write_project(self, project_name: str, key: str, content: str) -> None:
        self._projects.setdefault(project_name, {})[key] = content
        db = self._get_db()
        try:
            db.index_document(f"{project_name}/{key}", "project", key, content)
        except Exception:
            pass

    def append_event(self, project_name: str, event: dict[str, Any]) -> None:
        db = self._get_db()
        safe = dict(event)
        safe.pop("raw_patient_data", None)
        safe.pop("phi", None)
        run_id = safe.get("run_id", "")
        try:
            db.upsert_run({
                "run_id": run_id,
                "pipeline_id": safe.get("pipeline_id", ""),
                "project_name": project_name,
                "status": safe.get("status", "UNKNOWN"),
                "started_at": safe.get("started_at"),
                "finished_at": safe.get("finished_at"),
                "source_path": safe.get("source_path", ""),
            })
        except Exception:
            pass
        try:
            db.index_document(
                f"{project_name}/event/{run_id}",
                "project_event",
                f"Run: {run_id}",
                json.dumps(safe, ensure_ascii=False),
            )
        except Exception:
            pass

    def query_events(self, project_name: str, filters: dict[str, Any] | None = None, limit: int = 50) -> list[dict[str, Any]]:
        db = self._get_db()
        try:
            status = filters.get("status") if filters else None
            return db.query_runs_filtered(project_name=project_name, status=status, limit=limit)
        except Exception:
            return []

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        db = self._get_db()
        try:
            return db.search(query, limit=limit)
        except Exception:
            return []

    def sync(self) -> None:
        pass

    def shutdown(self) -> None:
        if self._db:
            self._db.close()
            self._db = None
        self._globals.clear()
        self._projects.clear()
