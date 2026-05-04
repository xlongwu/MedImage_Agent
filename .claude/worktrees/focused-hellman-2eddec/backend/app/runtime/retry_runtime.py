from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.runtime.agent_plan import _load_project_config
from backend.app.runtime.node_registry import (
    NodeExecutionContext,
    get_node_runner,
)
from backend.app.runtime.pipeline_executor import (
    get_complete_subjects,
    load_dataset_index,
)
from backend.app.runtime.state_store import (
    determine_status_from_result,
    now_iso,
    write_node_state,
)


EXECUTABLE_ACTIONS = {"RERUN_ENVIRONMENT_CHECK", "SAFE_RETRY"}
ALLOWLISTED_RETRY_NODES = {
    "environment_check",
    "spm_smooth_subject",
    "subject_qc",
    "dataset_evaluation",
}


def _default_retry_run_id(run_id: str) -> str:
    return f"retry_{run_id}_001"


def load_retry_plan(run_id: str, work_dir: str = "./work") -> dict[str, Any]:
    path = Path(work_dir) / "diagnosis" / run_id / "retry_plan.json"
    if not path.exists():
        return {
            "ok": False,
            "errors": [f"Retry plan not found: {path}"],
            "path": str(path),
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Failed to parse retry plan: {exc}"],
            "path": str(path),
        }

    data["ok"] = True
    data["path"] = str(path)
    return data


def _classify_retry_step(step: dict[str, Any]) -> dict[str, Any]:
    action = str(step.get("action", ""))
    node = step.get("node")
    subject_id = step.get("subject_id")

    executable = False
    reason = ""

    if action not in EXECUTABLE_ACTIONS:
        executable = False
        reason = f"Action is advisory-only in MVP: {action}"
    elif action == "RERUN_ENVIRONMENT_CHECK":
        executable = True
        node = "environment_check"
        reason = "Environment check can be safely rerun."
    elif action == "SAFE_RETRY":
        if node not in ALLOWLISTED_RETRY_NODES:
            executable = False
            reason = f"Node is not allowlisted for retry: {node}"
        else:
            executable = True
            reason = "Step is allowlisted for safe retry."
    else:
        executable = False
        reason = f"Unsupported retry action: {action}"

    return {
        "step_id": step.get("step_id"),
        "action": action,
        "node": node,
        "subject_id": subject_id,
        "executable": executable,
        "reason": reason,
        "original_step": step,
    }


def dry_run_retry_plan(
    run_id: str,
    retry_run_id: str | None = None,
    work_dir: str = "./work",
) -> dict[str, Any]:
    retry_run_id = retry_run_id or _default_retry_run_id(run_id)
    plan = load_retry_plan(run_id, work_dir)

    out_dir = Path(work_dir) / "retry_runs" / retry_run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not plan.get("ok"):
        summary = {
            "ok": False,
            "mode": "DRY_RUN",
            "run_id": run_id,
            "retry_run_id": retry_run_id,
            "steps": [],
            "errors": plan.get("errors", []),
        }
    else:
        steps = [_classify_retry_step(step) for step in plan.get("steps", [])]
        summary = {
            "ok": True,
            "mode": "DRY_RUN",
            "run_id": run_id,
            "retry_run_id": retry_run_id,
            "steps_total": len(steps),
            "steps_executable": sum(1 for step in steps if step["executable"]),
            "steps_skipped": sum(1 for step in steps if not step["executable"]),
            "steps": steps,
            "errors": [],
            "warnings": [],
        }

    path = out_dir / "dry_run_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["dry_run_summary_path"] = str(path)
    return summary


def _load_subject_record(subject_id: str, work_dir: str) -> dict[str, Any] | None:
    dataset_index_path = Path(work_dir) / "dataset_index" / "dataset_index.json"
    dataset_index = load_dataset_index(dataset_index_path)
    for subject in get_complete_subjects(dataset_index):
        if subject.get("subject_id") == subject_id:
            return subject
    return None


def _build_context(
    retry_run_id: str,
    project_config: dict[str, Any],
    subject_id: str | None = None,
    subject_record: dict[str, Any] | None = None,
    previous_subject_results: dict[str, dict[str, Any]] | None = None,
) -> NodeExecutionContext:
    runtime = project_config.get("runtime", {})
    third_party = project_config.get("third_party", {})

    return NodeExecutionContext(
        run_id=retry_run_id,
        project_config=project_config,
        work_dir=runtime.get("work_dir", "./work"),
        log_dir=runtime.get("log_dir", "./logs"),
        matlab_command=runtime.get("matlab_command", "matlab"),
        spm_dir=third_party.get("spm_dir", "./third_party/spm12"),
        dpabi_dir=third_party.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
        derivatives_dir=runtime.get("derivatives_dir", "./derivatives"),
        subject_id=subject_id,
        subject_record=subject_record,
        previous_subject_results=previous_subject_results or {},
    )


def _minimal_node(node_id: str, params: dict[str, Any] | None = None):
    from backend.app.schemas.pipeline_schema import PipelineNode

    return PipelineNode(
        id=node_id,
        name=node_id,
        agent="retry-runtime",
        backend="python",
        depends_on=[],
        inputs=[],
        outputs=[],
        params=params or {},
        parallel_level="subject" if node_id in {"spm_smooth_subject", "subject_qc"} else "project",
        gpu_supported=False,
        cache=False,
    )


def _run_single_retry_step(
    retry_run_id: str,
    project_config: dict[str, Any],
    classified_step: dict[str, Any],
) -> dict[str, Any]:
    action = classified_step["action"]
    node_id = classified_step["node"]
    subject_id = classified_step.get("subject_id")

    if not classified_step["executable"]:
        return {
            "ok": True,
            "status": "SKIPPED",
            "step_id": classified_step.get("step_id"),
            "node": node_id,
            "subject_id": subject_id,
            "reason": classified_step.get("reason"),
            "outputs": [],
            "errors": [],
        }

    if action == "RERUN_ENVIRONMENT_CHECK":
        node_id = "environment_check"
        context = _build_context(retry_run_id, project_config)
        node = _minimal_node("environment_check")
    else:
        if node_id in {"spm_smooth_subject", "subject_qc"}:
            if not subject_id or subject_id == "project":
                return {
                    "ok": False,
                    "status": "FAILED",
                    "step_id": classified_step.get("step_id"),
                    "node": node_id,
                    "subject_id": subject_id,
                    "errors": ["Subject-level retry requires subject_id."],
                }

            subject_record = _load_subject_record(subject_id, project_config.get("runtime", {}).get("work_dir", "./work"))
            if not subject_record:
                return {
                    "ok": False,
                    "status": "FAILED",
                    "step_id": classified_step.get("step_id"),
                    "node": node_id,
                    "subject_id": subject_id,
                    "errors": [f"Subject record not found or not COMPLETE: {subject_id}"],
                }

            context = _build_context(
                retry_run_id=retry_run_id,
                project_config=project_config,
                subject_id=subject_id,
                subject_record=subject_record,
            )
            node = _minimal_node(node_id, params={"fwhm": [4, 4, 4]})
        elif node_id == "dataset_evaluation":
            context = _build_context(retry_run_id, project_config)
            node = _minimal_node(
                "dataset_evaluation",
                params={"dataset_index": "./work/dataset_index/dataset_index.json"},
            )
        else:
            return {
                "ok": False,
                "status": "FAILED",
                "step_id": classified_step.get("step_id"),
                "node": node_id,
                "subject_id": subject_id,
                "errors": [f"Unsupported allowlisted retry node: {node_id}"],
            }

    started_at = now_iso()

    try:
        runner = get_node_runner(node_id)
        result = runner(context, node)
    except Exception as exc:
        result = {
            "ok": False,
            "node_id": node_id,
            "subject_id": subject_id or "project",
            "outputs": [],
            "errors": [f"Retry runner failed: {exc}"],
        }

    ended_at = now_iso()
    status = determine_status_from_result(result)
    subject_for_state = subject_id if subject_id and subject_id != "project" else "project"

    state_path = write_node_state(
        run_id=retry_run_id,
        node_id=node_id,
        subject=subject_for_state,
        status=status,
        started_at=started_at,
        ended_at=ended_at,
        result=result,
        work_dir=project_config.get("runtime", {}).get("work_dir", "./work"),
    )

    return {
        "ok": result.get("ok", False),
        "status": status,
        "step_id": classified_step.get("step_id"),
        "node": node_id,
        "subject_id": subject_for_state,
        "state_path": str(state_path),
        "result": result,
        "errors": result.get("errors", []),
    }


def execute_retry_plan(
    run_id: str,
    project_config_path: str,
    retry_run_id: str | None = None,
    approved: bool = False,
    work_dir: str = "./work",
) -> dict[str, Any]:
    retry_run_id = retry_run_id or _default_retry_run_id(run_id)

    if not approved:
        return {
            "ok": False,
            "mode": "EXECUTE",
            "run_id": run_id,
            "retry_run_id": retry_run_id,
            "errors": ["Retry execution requires approved=true."],
        }

    project_config = _load_project_config(project_config_path)
    dry_run = dry_run_retry_plan(run_id, retry_run_id, work_dir)

    out_dir = Path(work_dir) / "retry_runs" / retry_run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run.get("ok"):
        return dry_run

    results = []
    for step in dry_run.get("steps", []):
        result = _run_single_retry_step(
            retry_run_id=retry_run_id,
            project_config=project_config,
            classified_step=step,
        )
        results.append(result)

    failed = [item for item in results if item.get("status") == "FAILED"]
    executed = [item for item in results if item.get("status") != "SKIPPED"]

    summary = {
        "ok": len(failed) == 0,
        "mode": "EXECUTE",
        "run_id": run_id,
        "retry_run_id": retry_run_id,
        "approved": approved,
        "steps_total": len(results),
        "steps_executed": len(executed),
        "steps_failed": len(failed),
        "steps_skipped": sum(1 for item in results if item.get("status") == "SKIPPED"),
        "results": results,
        "errors": [err for item in failed for err in item.get("errors", [])],
        "warnings": [],
    }

    path = out_dir / "retry_execution_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["retry_execution_summary_path"] = str(path)
    return summary
