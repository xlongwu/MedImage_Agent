"""Query interface for SessionDB."""
from __future__ import annotations

from typing import Any

from src.backend.app.memory.session_db import SessionDB


def query_sessions(
    q: str | None = None,
    status: str | None = None,
    subject_id: str | None = None,
    category: str | None = None,
    limit: int = 50,
    db_path: str = "outputs/memory/sessions/archive.sqlite",
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
