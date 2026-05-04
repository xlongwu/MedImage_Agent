"""SessionDB -- SQLite-backed run memory with FTS5 full-text search."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    duration_seconds REAL,
    source_path TEXT,
    errors_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    subject_id TEXT NOT NULL DEFAULT 'project',
    status TEXT NOT NULL,
    ok INTEGER NOT NULL DEFAULT 0,
    duration_seconds REAL,
    outputs_json TEXT,
    warnings_json TEXT,
    errors_json TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    node_id TEXT,
    subject_id TEXT DEFAULT 'project',
    category TEXT,
    message TEXT NOT NULL,
    retryable INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_nodes_run ON nodes(run_id);
CREATE INDEX IF NOT EXISTS idx_nodes_subject ON nodes(subject_id);
CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);
CREATE INDEX IF NOT EXISTS idx_errors_run ON errors(run_id);
CREATE INDEX IF NOT EXISTS idx_errors_category ON errors(category);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    record_id,
    record_type,
    title,
    body,
    tokenize='porter unicode61'
);
"""


class SessionDB:
    def __init__(self, db_path: str | Path = "outputs/memory/sessions/archive.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(SCHEMA)
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- Write ---

    def upsert_run(self, run: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO runs
               (run_id, pipeline_id, status, started_at, finished_at,
                duration_seconds, source_path, errors_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (run["run_id"], run.get("pipeline_id", ""), run.get("status", ""),
             run.get("started_at"), run.get("finished_at"),
             run.get("duration_seconds"), run.get("source_path"),
             json.dumps(run.get("errors", []), ensure_ascii=False)),
        )
        self.conn.commit()

    def insert_node(self, node: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO nodes (run_id, node_id, subject_id, status, ok,
               duration_seconds, outputs_json, warnings_json, errors_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (node["run_id"], node["node_id"], node.get("subject_id", "project"),
             node.get("status", ""), 1 if node.get("ok") else 0,
             node.get("duration_seconds"),
             json.dumps(node.get("outputs", []), ensure_ascii=False),
             json.dumps(node.get("warnings", []), ensure_ascii=False),
             json.dumps(node.get("errors", []), ensure_ascii=False)),
        )
        self.conn.commit()

    def insert_error(self, error: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO errors (run_id, node_id, subject_id, category, message, retryable)
               VALUES (?,?,?,?,?,?)""",
            (error.get("run_id", ""), error.get("node_id"),
             error.get("subject_id", "project"), error.get("category"),
             error.get("message", ""), 1 if error.get("retryable") else 0),
        )
        self.conn.commit()

    def index_document(self, record_id: str, record_type: str, title: str, body: str) -> None:
        self.conn.execute(
            "INSERT INTO documents_fts (record_id, record_type, title, body) VALUES (?,?,?,?)",
            (record_id, record_type, title, body),
        )
        self.conn.commit()

    def clear_fts(self) -> None:
        self.conn.execute("DELETE FROM documents_fts")
        self.conn.commit()

    # --- Query ---

    def query_runs(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM runs WHERE status=? ORDER BY started_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def query_nodes_by_run(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE run_id=? ORDER BY id", (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_nodes_by_subject(self, subject_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE subject_id=? ORDER BY run_id DESC", (subject_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_errors(self, category: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if category:
            rows = self.conn.execute(
                "SELECT * FROM errors WHERE category=? ORDER BY created_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM errors ORDER BY created_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        # Escape special FTS5 characters to avoid syntax errors
        safe_query = query.replace(".", " ").replace("-", " ").replace("_", " ")
        safe_query = " ".join(t for t in safe_query.split() if t)
        if not safe_query:
            safe_query = query.replace(".", "").replace("-", "").replace("_", "") or query
        try:
            rows = self.conn.execute(
                """SELECT record_id, record_type, title, snippet(documents_fts, 2, '<b>', '</b>', '...', 32) as snippet
                   FROM documents_fts WHERE documents_fts MATCH ? ORDER BY rank LIMIT ?""",
                (safe_query, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def stats(self) -> dict[str, Any]:
        total_runs = self.conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        success_runs = self.conn.execute(
            "SELECT COUNT(*) FROM runs WHERE status='SUCCESS'"
        ).fetchone()[0]
        total_nodes = self.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        failed_nodes = self.conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE status='FAILED'"
        ).fetchone()[0]
        total_errors = self.conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
        return {
            "total_runs": total_runs,
            "success_runs": success_runs,
            "total_nodes": total_nodes,
            "failed_nodes": failed_nodes,
            "total_errors": total_errors,
        }

    def error_categories(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT category, COUNT(*) as count FROM errors GROUP BY category ORDER BY count DESC"
        ).fetchall()
        return [dict(r) for r in rows]
