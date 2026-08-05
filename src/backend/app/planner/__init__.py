from __future__ import annotations

__all__ = [
    "draft_pipeline_plan",
    "execute_pipeline_plan",
    "get_planner_history",
    "validate_pipeline_plan",
]


def __getattr__(name: str):
    """Lazily expose legacy planner helpers without import-time registry cycles."""

    if name not in __all__:
        raise AttributeError(name)
    from src.backend.app.planner import pipeline_planner

    return getattr(pipeline_planner, name)
