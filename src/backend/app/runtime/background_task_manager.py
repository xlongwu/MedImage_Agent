"""Background task manager -- run tasks asynchronously with status tracking."""
from __future__ import annotations

import json
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


_executor = ThreadPoolExecutor(max_workers=2)
_tasks: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_status(path: Path, record: dict[str, Any]) -> None:
    """Atomic write: write to temp file, then replace the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read_status(path: Path) -> dict[str, Any] | None:
    """Read a status JSON file, handling edge cases gracefully.

    Returns None for missing / empty / corrupted files so callers can
    decide how to handle them without crashing.
    """
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except IOError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def submit_background_task(
    task_type: str,
    func: Callable,
    args: tuple = (),
    kwargs: dict | None = None,
    status_dir: str = "./work/background_tasks",
) -> str:
    task_id = f"{task_type}_{uuid.uuid4().hex[:12]}"
    status_path = Path(status_dir) / f"{task_id}.json"

    task_record = {
        "task_id": task_id,
        "task_type": task_type,
        "status": "PENDING",
        "submitted_at": _now_iso(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }
    _write_status(status_path, task_record)
    _tasks[task_id] = task_record

    def _wrapper():
        task_record["status"] = "RUNNING"
        task_record["started_at"] = _now_iso()
        _write_status(status_path, task_record)
        try:
            result = func(*args, **(kwargs or {}))
            task_record["status"] = "SUCCESS"
            task_record["result"] = result
        except Exception as exc:
            task_record["status"] = "FAILED"
            task_record["error"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        task_record["finished_at"] = _now_iso()
        _write_status(status_path, task_record)

    _executor.submit(_wrapper)
    return task_id


def get_task_status(task_id: str, status_dir: str = "./work/background_tasks") -> dict[str, Any]:
    status_path = Path(status_dir) / f"{task_id}.json"
    record = _read_status(status_path)
    if record is None:
        return {"ok": False, "task_id": task_id, "errors": ["Task not found"]}
    return {"ok": True, **record}


def list_tasks(status_dir: str = "./work/background_tasks", limit: int = 50) -> dict[str, Any]:
    sd = Path(status_dir)
    if not sd.exists():
        return {"ok": True, "tasks": [], "total": 0}
    tasks = []
    for f in sorted(sd.glob("*.json"), key=lambda p: -p.stat().st_mtime)[:limit]:
        record = _read_status(f)
        if record is not None:
            tasks.append(record)
    return {"ok": True, "tasks": tasks, "total": len(tasks)}
