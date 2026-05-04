# Phase B1：SessionDB + FTS5 可查询运行记忆

> 目标版本：v0.2.0 | 预计工期：3–4 天 | 前置条件：Phase A 完成

---

## 1. 目标与范围

将分散的 JSON/JSONL/run history 记录汇总进 SQLite 数据库，支持跨运行 FTS5 全文搜索和结构化查询。

**不做**：修改核心 pipeline runtime、接入真实 SPM/DPABI/GPU、LLM 集成。

---

## 2. 前置条件检查

- [ ] Phase A 验收通过
- [ ] 已有数据源存在：
  - `work/pipeline_runs/*/summary.json`
  - `demo_runs/*/quickstart_demo_summary.json`
  - `reports/run_history/run_history_index.json`
  - `memory/projects/*/RUN_HISTORY.jsonl`

---

## 3. 新增/修改文件清单

```text
backend/app/memory/session_db.py            # 新增：SessionDB 核心类
backend/app/tools/session_indexer.py        # 新增：索引构建工具
backend/app/tools/session_query.py          # 新增：查询工具
backend/app/api/routes.py                   # 修改：新增 5 个端点
backend/app/api/models.py                   # 修改：新增 Pydantic models
examples/pipeline_session_index.yaml        # 新增：pipeline YAML
tests/unit/test_session_db.py               # 新增：SessionDB 测试
frontend/src/components/SessionMemoryBrowserPanel.tsx  # 新增：前端面板
frontend/src/App.tsx                        # 修改：注册新面板
```

---

## 4. 逐步实施步骤

### Step 1：创建 SQLite Schema 和 SessionDB 类

文件：`backend/app/memory/session_db.py`

```python
"""SessionDB — SQLite-backed run memory with FTS5 full-text search."""
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
    def __init__(self, db_path: str | Path = "memory/sessions/archive.sqlite"):
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
            (run["run_id"], run.get("pipeline_id",""), run.get("status",""),
             run.get("started_at"), run.get("finished_at"),
             run.get("duration_seconds"), run.get("source_path"),
             json.dumps(run.get("errors",[]), ensure_ascii=False)),
        )
        self.conn.commit()

    def insert_node(self, node: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO nodes (run_id, node_id, subject_id, status, ok,
               duration_seconds, outputs_json, warnings_json, errors_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (node["run_id"], node["node_id"], node.get("subject_id","project"),
             node.get("status",""), 1 if node.get("ok") else 0,
             node.get("duration_seconds"),
             json.dumps(node.get("outputs",[]), ensure_ascii=False),
             json.dumps(node.get("warnings",[]), ensure_ascii=False),
             json.dumps(node.get("errors",[]), ensure_ascii=False)),
        )
        self.conn.commit()

    def insert_error(self, error: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO errors (run_id, node_id, subject_id, category, message, retryable)
               VALUES (?,?,?,?,?,?)""",
            (error.get("run_id",""), error.get("node_id"),
             error.get("subject_id","project"), error.get("category"),
             error.get("message",""), 1 if error.get("retryable") else 0),
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
        rows = self.conn.execute(
            """SELECT record_id, record_type, title, snippet(documents_fts, 2, '<b>', '</b>', '...', 32) as snippet
               FROM documents_fts WHERE documents_fts MATCH ? ORDER BY rank LIMIT ?""",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

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
```

### Step 2：创建索引器

文件：`backend/app/tools/session_indexer.py`

```python
"""Index existing run histories into SessionDB."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.memory.session_db import SessionDB


def index_pipeline_runs(work_dir: str = "./work", db_path: str = "memory/sessions/archive.sqlite") -> dict[str, Any]:
    db = SessionDB(db_path)
    work = Path(work_dir)
    pipeline_runs_dir = work / "pipeline_runs"

    indexed_runs = 0
    indexed_nodes = 0
    indexed_errors = 0
    skipped = 0

    if pipeline_runs_dir.exists():
        for run_dir in sorted(pipeline_runs_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_path = run_dir / "summary.json"
            if not summary_path.exists():
                skipped += 1
                continue

            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                skipped += 1
                continue

            run_id = summary.get("run_id", run_dir.name)
            db.upsert_run({
                "run_id": run_id,
                "pipeline_id": summary.get("pipeline_id", ""),
                "status": summary.get("status", "UNKNOWN"),
                "started_at": summary.get("started_at"),
                "finished_at": summary.get("ended_at"),
                "duration_seconds": summary.get("duration_seconds"),
                "source_path": str(summary_path),
                "errors": summary.get("errors", []),
            })
            indexed_runs += 1

            for nr in summary.get("node_results", []):
                db.insert_node({
                    "run_id": run_id,
                    "node_id": nr.get("node_id", ""),
                    "subject_id": nr.get("subject_id", nr.get("subject", "project")),
                    "status": "SUCCESS" if nr.get("ok") else "FAILED",
                    "ok": nr.get("ok", False),
                    "outputs": nr.get("outputs", []),
                    "warnings": nr.get("warnings", []),
                    "errors": nr.get("errors", []),
                })
                indexed_nodes += 1

                for err_msg in nr.get("errors", []):
                    db.insert_error({
                        "run_id": run_id,
                        "node_id": nr.get("node_id", ""),
                        "subject_id": nr.get("subject_id", nr.get("subject", "project")),
                        "category": "UNKNOWN",
                        "message": str(err_msg),
                    })
                    indexed_errors += 1

            # Index as FTS document
            db.index_document(
                record_id=run_id,
                record_type="pipeline_run",
                title=f"{run_id} ({summary.get('pipeline_id', '')})",
                body=json.dumps(summary, ensure_ascii=False),
            )

    db.close()
    return {
        "ok": True,
        "indexed_runs": indexed_runs,
        "indexed_nodes": indexed_nodes,
        "indexed_errors": indexed_errors,
        "skipped": skipped,
    }


def index_demo_runs(demo_dir: str = "./demo_runs", db_path: str = "memory/sessions/archive.sqlite") -> dict[str, Any]:
    db = SessionDB(db_path)
    demo = Path(demo_dir)
    count = 0
    if demo.exists():
        for run_dir in sorted(demo.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_path = run_dir / "quickstart_demo_summary.json"
            if not summary_path.exists():
                continue
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                continue
            run_id = f"demo_{run_dir.name}"
            db.upsert_run({
                "run_id": run_id,
                "pipeline_id": "quickstart_demo",
                "status": "SUCCESS" if summary.get("ok") else "FAILED",
                "started_at": summary.get("started_at"),
                "finished_at": summary.get("ended_at"),
                "source_path": str(summary_path),
            })
            count += 1
            db.index_document(
                record_id=run_id,
                record_type="demo_run",
                title=f"Demo: {run_dir.name}",
                body=json.dumps(summary, ensure_ascii=False),
            )
    db.close()
    return {"ok": True, "indexed_demo_runs": count}
```

### Step 3：创建查询工具

文件：`backend/app/tools/session_query.py`

```python
"""Query interface for SessionDB."""
from __future__ import annotations

from typing import Any

from backend.app.memory.session_db import SessionDB


def query_sessions(
    q: str | None = None,
    status: str | None = None,
    subject_id: str | None = None,
    category: str | None = None,
    limit: int = 50,
    db_path: str = "memory/sessions/archive.sqlite",
) -> dict[str, Any]:
    db = SessionDB(db_path)

    result: dict[str, Any] = {"ok": True, "query": {}}

    if q:
        result["query"]["search"] = q
        result["results"] = db.search(q, limit=limit)
    elif subject_id:
        result["query"]["subject_id"] = subject_id
        result["results"] = db.query_nodes_by_subject(subject_id)[:limit]
    elif category:
        result["query"]["error_category"] = category
        result["results"] = db.query_errors(category=category, limit=limit)
    elif status:
        result["query"]["run_status"] = status
        result["results"] = db.query_runs(status=status, limit=limit)
    else:
        result["results"] = db.query_runs(limit=limit)

    result["stats"] = db.stats()
    result["error_categories"] = db.error_categories()
    result["total_results"] = len(result["results"])
    db.close()
    return result
```

### Step 4：新增 API 端点

在 `backend/app/api/routes.py` 中新增：

```python
# === SessionDB endpoints ===

@router.post("/api/sessions/index")
async def sessions_index():
    """Index all existing run histories into SessionDB."""
    pipe_result = index_pipeline_runs()
    demo_result = index_demo_runs()
    return {
        "ok": True,
        "pipeline_runs": pipe_result,
        "demo_runs": demo_result,
    }


@router.get("/api/sessions/query")
async def sessions_query(
    q: str | None = Query(None),
    status: str | None = Query(None),
    subject_id: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50),
):
    """Query SessionDB with optional filters or FTS search."""
    return query_sessions(q=q, status=status, subject_id=subject_id, category=category, limit=limit)


@router.get("/api/sessions/runs")
async def sessions_runs(status: str | None = None, limit: int = 50):
    """List runs from SessionDB."""
    db = SessionDB()
    runs = db.query_runs(status=status, limit=limit)
    stats = db.stats()
    db.close()
    return {"ok": True, "runs": runs, "stats": stats, "total": len(runs)}


@router.get("/api/sessions/errors")
async def sessions_errors(category: str | None = None, limit: int = 100):
    """List errors from SessionDB, optionally filtered by category."""
    db = SessionDB()
    errors = db.query_errors(category=category, limit=limit)
    cats = db.error_categories()
    db.close()
    return {"ok": True, "errors": errors, "categories": cats, "total": len(errors)}


@router.get("/api/sessions/subjects/{subject_id}")
async def sessions_subject(subject_id: str):
    """Get run history for a specific subject."""
    db = SessionDB()
    nodes = db.query_nodes_by_subject(subject_id)
    db.close()
    return {"ok": True, "subject_id": subject_id, "nodes": nodes, "total": len(nodes)}
```

### Step 5：前端组件

文件：`frontend/src/components/SessionMemoryBrowserPanel.tsx`

```tsx
import React, { useEffect, useState } from 'react';
import { apiGet, apiPost } from '../api';

export default function SessionMemoryBrowserPanel() {
  const [stats, setStats] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadRuns();
  }, []);

  async function loadRuns() {
    setLoading(true);
    const res = await apiGet('/api/sessions/runs?limit=50');
    setStats(res.stats);
    setRuns(res.runs);
    setLoading(false);
  }

  async function doIndex() {
    setLoading(true);
    await apiPost('/api/sessions/index', {});
    await loadRuns();
  }

  async function doSearch() {
    if (!search.trim()) return;
    setLoading(true);
    const res = await apiGet(`/api/sessions/query?q=${encodeURIComponent(search)}&limit=50`);
    setResults(res.results || []);
    setLoading(false);
  }

  return (
    <div className="session-memory-panel">
      <h2>Session Memory Browser</h2>

      {stats && (
        <div className="stats-bar">
          <span>Runs: {stats.total_runs}</span>
          <span>Success: {stats.success_runs}</span>
          <span>Nodes: {stats.total_nodes}</span>
          <span>Failed: {stats.failed_nodes}</span>
          <span>Errors: {stats.total_errors}</span>
        </div>
      )}

      <div className="toolbar">
        <button onClick={doIndex} disabled={loading}>Index All Runs</button>
        <input
          type="text"
          placeholder="Search runs, errors, subjects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && doSearch()}
        />
        <button onClick={doSearch} disabled={loading || !search.trim()}>Search</button>
      </div>

      {results.length > 0 && (
        <div className="search-results">
          <h3>Search Results ({results.length})</h3>
          {results.map((r: any, i: number) => (
            <div key={i} className="result-item">
              <strong>[{r.record_type}]</strong> {r.title}
              {r.snippet && <p dangerouslySetInnerHTML={{ __html: r.snippet }} />}
            </div>
          ))}
        </div>
      )}

      <h3>Recent Runs</h3>
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Pipeline</th>
            <th>Status</th>
            <th>Started</th>
            <th>Duration (s)</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r: any) => (
            <tr key={r.run_id} className={r.status === 'FAILED' ? 'row-failed' : ''}>
              <td>{r.run_id}</td>
              <td>{r.pipeline_id}</td>
              <td>{r.status}</td>
              <td>{r.started_at?.slice(0, 19)}</td>
              <td>{r.duration_seconds?.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {loading && <div className="loading">Loading...</div>}
    </div>
  );
}
```

在 `App.tsx` 中注册：
```tsx
import SessionMemoryBrowserPanel from './components/SessionMemoryBrowserPanel';
// ... 在 tabs 中添加
{id: 'session-memory', label: 'Session Memory', component: <SessionMemoryBrowserPanel />}
```

---

## 5. 测试用例

文件：`tests/unit/test_session_db.py`

```python
from __future__ import annotations

from pathlib import Path

from backend.app.memory.session_db import SessionDB


def test_session_db_create_and_upsert_run(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))

    db.upsert_run({
        "run_id": "test-run-1",
        "pipeline_id": "rsfmri_mvp",
        "status": "SUCCESS",
        "started_at": "2026-01-01T00:00:00",
        "finished_at": "2026-01-01T00:05:00",
        "duration_seconds": 300.0,
    })

    runs = db.query_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "test-run-1"
    assert runs[0]["status"] == "SUCCESS"
    db.close()


def test_session_db_insert_and_query_nodes(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))
    db.upsert_run({"run_id": "r1", "pipeline_id": "p1", "status": "SUCCESS"})

    db.insert_node({"run_id": "r1", "node_id": "motion_qc", "subject_id": "sub-001", "ok": True, "status": "SUCCESS"})
    db.insert_node({"run_id": "r1", "node_id": "normalize", "subject_id": "sub-002", "ok": False, "status": "FAILED", "errors": ["bad norm"]})

    nodes = db.query_nodes_by_run("r1")
    assert len(nodes) == 2

    sub_nodes = db.query_nodes_by_subject("sub-002")
    assert len(sub_nodes) == 1
    assert sub_nodes[0]["status"] == "FAILED"

    stats = db.stats()
    assert stats["total_nodes"] == 2
    assert stats["failed_nodes"] == 1
    db.close()


def test_session_db_error_and_fts(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))
    db.upsert_run({"run_id": "r1", "pipeline_id": "p1", "status": "FAILED"})
    db.insert_error({"run_id": "r1", "node_id": "normalize", "category": "SPM_ERROR", "message": "Undefined function spm"})

    errors = db.query_errors(category="SPM_ERROR")
    assert len(errors) == 1

    db.index_document("r1", "pipeline_run", "Run r1", "SPM normalization failed with Undefined function spm")
    results = db.search("spm")
    assert len(results) == 1
    assert "spm" in results[0]["snippet"].lower()
    db.close()
```

---

## 6. 验收标准

- [ ] `SessionDB` 类可创建 SQLite 数据库
- [ ] `upsert_run` / `insert_node` / `insert_error` 写入正确
- [ ] `query_runs` / `query_nodes_by_run` / `query_nodes_by_subject` 查询正确
- [ ] `search()` FTS5 全文搜索正常
- [ ] `stats()` 返回正确的聚合数据
- [ ] `session_indexer.index_pipeline_runs()` 可从 work/ 目录索引
- [ ] `session_indexer.index_demo_runs()` 可从 demo_runs/ 目录索引
- [ ] API `POST /api/sessions/index` 可触发索引
- [ ] API `GET /api/sessions/query?q=...` 可搜索
- [ ] API `GET /api/sessions/runs` 返回运行列表
- [ ] API `GET /api/sessions/errors` 返回错误列表
- [ ] API `GET /api/sessions/subjects/{id}` 返回 subject 历史
- [ ] 前端 SessionMemoryBrowserPanel 可查看运行列表和执行搜索
- [ ] 不修改任何现有历史文件
- [ ] 数据库文件仅写 `memory/sessions/archive.sqlite`
- [ ] 3 个单元测试通过

---

## 7. 风险与注意事项

- SQLite 文件可能变大：FTS5 索引会额外占用空间，初始建议在 `index_pipeline_runs` 中限制索引的 run 数量
- WAL 模式：同时读写安全，但需确保 `db.close()` 被调用
- 旧数据兼容：如果 `work/pipeline_runs/` 目录为空，索引器应返回 `indexed_runs: 0` 而不是报错
- 不修改原始数据源：索引器只读 JSON 文件，不删除不修改
