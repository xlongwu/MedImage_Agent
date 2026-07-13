"""Parent-owned persisted progress snapshots for native preprocessing."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.runtime.atomic_file import atomic_write_json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def progress_path(run_dir: Path) -> Path:
    return run_dir / "native_full_progress.json"


def initial_progress(*, project_id: str, run_id: str, run_dir: Path, subject_ids: list[str], resource_decision: dict[str, Any]) -> dict[str, Any]:
    now = now_iso()
    return {
        "project_id": project_id,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "queued",
        "started_at": now,
        "updated_at": now,
        "heartbeat_at": now,
        "finished_at": "",
        "completed_subjects": 0,
        "total_subjects": len(subject_ids),
        "scheduler": resource_decision,
        "subjects": {subject_id: {"status": "queued", "stage_id": "", "heartbeat_at": now} for subject_id in subject_ids},
        "replan_events": [],
        "errors": [],
    }


def write_progress(run_dir: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = now_iso()
    payload["heartbeat_at"] = payload["updated_at"]
    atomic_write_json(progress_path(run_dir), payload, schema_version=1)


def load_progress(run_dir: Path) -> dict[str, Any] | None:
    path = progress_path(run_dir)
    if not path.exists():
        return None
    import json

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else None


__all__ = ["initial_progress", "load_progress", "now_iso", "progress_path", "write_progress"]
