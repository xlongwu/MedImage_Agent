"""Spawn-safe subject worker.  It owns only one subject output directory."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from threading import Event, Thread
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _set_thread_budget(threads: int) -> None:
    value = str(max(1, threads))
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[key] = value


def execute_subject_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute one request; all payload fields are spawn/pickle safe."""
    _set_thread_budget(int(payload["threads_per_worker"]))
    from src.backend.app.native_preproc.orchestrator import runner
    from src.backend.app.schemas.native_preproc_api import NativeFullPreprocRequest

    events = payload.get("events")
    subject_id = str(payload["subject_id"])
    stop = Event()

    def emit(kind: str, **extra: Any) -> None:
        if events is not None:
            events.put({"kind": kind, "subject_id": subject_id, "at": _now(), **extra})

    def heartbeat() -> None:
        while not stop.wait(5):
            emit("heartbeat")

    thread = Thread(target=heartbeat, daemon=True)
    thread.start()
    emit("subject_started", worker_pid=os.getpid())
    runner.set_native_preproc_progress_callback(lambda stage_id, status: emit("stage", stage_id=stage_id, stage_status=status))
    try:
        request = NativeFullPreprocRequest.model_validate(payload["request"])
        response = runner.execute_native_full_preproc(str(payload["project_id"]), request, project_dir=str(payload["project_dir"]))
        emit("subject_finished", status=response.status)
        return {"subject_id": subject_id, "response": response.model_dump(mode="json")}
    except Exception as exc:
        emit("subject_failed", error=str(exc))
        return {"subject_id": subject_id, "error": str(exc)}
    finally:
        runner.set_native_preproc_progress_callback(None)
        stop.set()
        thread.join(timeout=0.1)


__all__ = ["execute_subject_worker"]
