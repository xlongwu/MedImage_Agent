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
    offset: int = 0,
    db_path: str = "outputs/memory/sessions/archive.sqlite",
) -> dict[str, Any]:
    db = SessionDB(db_path)

    result: dict[str, Any] = {"ok": True, "query": {}}

    fetch_limit = offset + limit

    if q:
        result["query"]["search"] = q
        result["results"] = db.search(q, limit=fetch_limit)
    elif subject_id:
        result["query"]["subject_id"] = subject_id
        result["results"] = db.query_nodes_by_subject(subject_id)[:fetch_limit]
    elif category:
        result["query"]["error_category"] = category
        result["results"] = db.query_errors(category=category, limit=fetch_limit)
    elif status:
        result["query"]["run_status"] = status
        result["results"] = db.query_runs(status=status, limit=fetch_limit)
    else:
        result["results"] = db.query_runs(limit=fetch_limit)

    result["total_results"] = len(result["results"])
    result["results"] = result["results"][offset:offset + limit]
    result["offset"] = offset
    result["limit"] = limit
    result["stats"] = db.stats()
    result["error_categories"] = db.error_categories()
    db.close()
    return result
