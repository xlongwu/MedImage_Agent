"""SessionDB and run-history route handlers."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

router = APIRouter()


@router.post("/api/sessions/index")
async def sessions_index():
    """Index all existing run histories into SessionDB."""
    from src.backend.app.tools.session_indexer import index_pipeline_runs, index_demo_runs

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
    offset: int = Query(0),
):
    """Query SessionDB with optional filters or FTS search."""
    from src.backend.app.tools.session_query import query_sessions

    return query_sessions(q=q, status=status, subject_id=subject_id,
                          category=category, limit=limit, offset=offset)

@router.get("/api/sessions/runs")
async def sessions_runs(status: str | None = None, limit: int = 50):
    """List runs from SessionDB."""
    from src.backend.app.memory.session_db import SessionDB

    db = SessionDB()
    runs = db.query_runs(status=status, limit=limit)
    db.close()
    return {"ok": True, "runs": runs, "total": len(runs)}

@router.get("/api/sessions/nodes")
async def sessions_nodes(run_id: str = Query(...)):
    """List nodes for a run from SessionDB."""
    from src.backend.app.memory.session_db import SessionDB

    db = SessionDB()
    nodes = db.query_nodes(run_id=run_id)
    db.close()
    return {"ok": True, "nodes": nodes, "total": len(nodes)}

@router.get("/api/sessions/search")
async def sessions_search(q: str = Query(...), limit: int = 30):
    """Full-text search across indexed documents."""
    from src.backend.app.memory.session_db import SessionDB

    db = SessionDB()
    results = db.fts_search(query=q, limit=limit)
    db.close()
    return {"ok": True, "results": results, "total": len(results)}


# ── Run history endpoints ─────────────────────────────────────────────────

@router.get("/api/history/runs")
def api_history_runs(limit: int = Query(20)) -> dict[str, Any]:
    from src.backend.app.tools.run_history_cli import get_recent_run_history

    return {"ok": True, "runs": get_recent_run_history(limit)}


# ── DPABI template library endpoints ──────────────────────────────────────
