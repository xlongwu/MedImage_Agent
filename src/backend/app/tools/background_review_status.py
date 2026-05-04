"""Background review status query tool — check and list async review tasks."""
from __future__ import annotations

from typing import Any

from src.backend.app.runtime.background_task_manager import get_task_status, list_tasks


def get_background_review_status(task_id: str) -> dict[str, Any]:
    """Get status of a background review task by ID."""
    return get_task_status(task_id)


def list_background_reviews(limit: int = 20) -> dict[str, Any]:
    """List recent background review tasks."""
    all_tasks = list_tasks(limit=limit)
    reviews = [t for t in all_tasks.get("tasks", []) if t.get("task_type") == "background_review"]
    return {
        "ok": True,
        "reviews": reviews,
        "total": len(reviews),
    }


def get_latest_background_review() -> dict[str, Any]:
    """Get the latest completed background review."""
    all_tasks = list_tasks(limit=50)
    for t in all_tasks.get("tasks", []):
        if t.get("task_type") == "background_review" and t.get("status") == "SUCCESS":
            return {"ok": True, "latest": t}
    return {"ok": False, "errors": ["No completed background review found"]}
