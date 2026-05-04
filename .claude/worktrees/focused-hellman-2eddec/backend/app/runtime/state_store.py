from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def determine_status_from_result(result: dict[str, Any]) -> str:
    return "SUCCESS" if result.get("ok") else "FAILED"


def write_node_state(
    run_id: str,
    node_id: str,
    subject: str,
    status: str,
    started_at: str,
    ended_at: str,
    result: dict[str, Any],
    work_dir: str,
) -> Path:
    # For subject-level nodes, store in subject subdirectory
    if subject != "project":
        state_dir = Path(work_dir) / "states" / run_id / subject
    else:
        state_dir = Path(work_dir) / "states" / run_id
    state_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "run_id": run_id,
        "subject": subject,
        "node": node_id,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "log_path": result.get("stdout_log"),
        "stderr_log": result.get("stderr_log"),
        "outputs": result.get("outputs", result.get("expected_outputs", [])),
        "metrics": result.get("metrics", {}),
        "warnings": result.get("warnings", []),
        "errors": result.get("errors", []),
        "result_json": result.get("result_json"),
        "returncode": result.get("returncode"),
    }

    state_path = state_dir / f"{node_id}.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state_path


def write_pipeline_summary(
    run_id: str,
    pipeline_id: str,
    status: str,
    started_at: str,
    ended_at: str,
    node_states: list[str],
    node_results: list[dict[str, Any]],
    errors: list[str],
    work_dir: str,
    scheduler: dict[str, Any] | None = None,
    duration_seconds: float = 0.0,
) -> Path:
    summary_dir = Path(work_dir) / "pipeline_runs" / run_id
    summary_dir.mkdir(parents=True, exist_ok=True)

    nodes_total = len(node_results)
    nodes_success = sum(1 for r in node_results if r.get("ok"))
    nodes_failed = nodes_total - nodes_success

    summary: dict[str, Any] = {
        "run_id": run_id,
        "pipeline_id": pipeline_id,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration_seconds,
        "nodes_total": nodes_total,
        "nodes_success": nodes_success,
        "nodes_failed": nodes_failed,
        "nodes_skipped": 0,
        "node_states": node_states,
        "errors": errors,
    }

    if scheduler:
        summary["scheduler"] = scheduler

    summary_path = summary_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_path
