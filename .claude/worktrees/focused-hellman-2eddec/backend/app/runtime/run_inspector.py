from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_available_runs(work_dir: str = "./work") -> dict[str, Any]:
    root = Path(work_dir) / "pipeline_runs"
    if not root.exists():
        return {
            "ok": True,
            "runs": [],
            "warnings": [f"No pipeline_runs directory found: {root}"],
        }

    runs = []
    for item in sorted(root.iterdir()):
        if not item.is_dir():
            continue
        summary_path = item / "summary.json"
        summary = _read_json(summary_path)
        runs.append({
            "run_id": item.name,
            "summary_path": str(summary_path),
            "status": summary.get("status") if summary else "UNKNOWN",
            "pipeline_id": summary.get("pipeline_id") if summary else None,
        })

    return {
        "ok": True,
        "runs": runs,
        "warnings": [],
    }


def inspect_run(run_id: str, work_dir: str = "./work") -> dict[str, Any]:
    warnings: list[str] = []

    summary_path = Path(work_dir) / "pipeline_runs" / run_id / "summary.json"
    summary = _read_json(summary_path)

    if not summary:
        warnings.append(f"Missing or invalid pipeline summary: {summary_path}")
        summary = None

    states_root = Path(work_dir) / "states" / run_id
    project_states = []
    subject_states: dict[str, list[dict[str, Any]]] = {}

    if not states_root.exists():
        warnings.append(f"Missing states directory: {states_root}")
    else:
        for path in sorted(states_root.rglob("*.json")):
            state = _read_json(path)
            if not state:
                warnings.append(f"Invalid state JSON: {path}")
                continue

            relative_path = str(path)
            subject = str(state.get("subject", "project"))

            payload = {
                "path": relative_path,
                "run_id": state.get("run_id"),
                "subject": subject,
                "node": state.get("node"),
                "status": state.get("status"),
                "started_at": state.get("started_at"),
                "ended_at": state.get("ended_at"),
                "outputs": state.get("outputs", []),
                "errors": state.get("errors", []),
                "warnings": state.get("warnings", []),
                "metrics": state.get("metrics", {}),
                "stdout_log": state.get("stdout_log") or state.get("log_path"),
                "stderr_log": state.get("stderr_log"),
                "result_json": state.get("result_json"),
                "returncode": state.get("returncode"),
            }

            if subject == "project":
                project_states.append(payload)
            else:
                subject_states.setdefault(subject, []).append(payload)

    subjects = []
    for subject_id, states in sorted(subject_states.items()):
        statuses = [str(item.get("status")) for item in states]
        if any(status == "FAILED" for status in statuses):
            aggregate_status = "FAILED"
        elif any(status == "NEEDS_REVIEW" for status in statuses):
            aggregate_status = "NEEDS_REVIEW"
        elif states and all(status == "SUCCESS" for status in statuses):
            aggregate_status = "SUCCESS"
        else:
            aggregate_status = "UNKNOWN"

        subjects.append({
            "subject_id": subject_id,
            "status": aggregate_status,
            "nodes": states,
        })

    return {
        "ok": True,
        "run_id": run_id,
        "summary_path": str(summary_path),
        "summary": summary,
        "project_states": project_states,
        "subjects": subjects,
        "warnings": warnings,
    }


def read_state_detail(
    run_id: str,
    state_path: str,
    work_dir: str = "./work",
) -> dict[str, Any]:
    root = Path(work_dir).resolve()
    target = Path(state_path)

    if not target.is_absolute():
        target = Path.cwd() / target

    target = target.resolve()

    try:
        target.relative_to(root.resolve().parent)
    except ValueError:
        return {
            "ok": False,
            "errors": [f"State path escapes repository: {state_path}"],
        }

    if f"states/{run_id}" not in str(target).replace("\\", "/"):
        return {
            "ok": False,
            "errors": [f"State path does not belong to run {run_id}: {state_path}"],
        }

    state = _read_json(target)
    if not state:
        return {
            "ok": False,
            "errors": [f"Missing or invalid state JSON: {target}"],
        }

    return {
        "ok": True,
        "path": str(target),
        "state": state,
    }
