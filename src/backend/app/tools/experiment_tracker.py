from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import (
    is_safe_artifact_id,
    read_json_artifact,
    write_json_artifact,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _count_node_status(summary: dict[str, Any]) -> dict[str, int]:
    nodes = summary.get("nodes", []) or summary.get("node_results", []) or []
    total = len(nodes)
    success = 0
    failed = 0

    for node in nodes:
        status = str(node.get("status", "")).upper()
        ok = node.get("ok")
        if ok is True or status in {"SUCCESS", "COMPLETED", "OK"}:
            success += 1
        elif ok is False or status in {"FAILED", "ERROR"}:
            failed += 1

    return {
        "nodes_total": total,
        "nodes_success": success,
        "nodes_failed": failed,
    }


def _count_outputs(summary: dict[str, Any]) -> int:
    count = 0
    nodes = summary.get("nodes", []) or summary.get("node_results", []) or []
    for node in nodes:
        outputs = node.get("outputs", [])
        if isinstance(outputs, list):
            count += len(outputs)
    return count


def _count_messages(summary: dict[str, Any], key: str) -> int:
    count = 0

    direct = summary.get(key, [])
    if isinstance(direct, list):
        count += len(direct)

    nodes = summary.get("nodes", []) or summary.get("node_results", []) or []
    for node in nodes:
        messages = node.get(key, [])
        if isinstance(messages, list):
            count += len(messages)

    return count


def _summarize_pipeline_run(path: Path) -> dict[str, Any] | None:
    summary = read_json_artifact(path)
    if not summary:
        return None

    node_counts = _count_node_status(summary)
    scheduler = summary.get("scheduler", {}) or {}

    run_id = (
        summary.get("run_id")
        or summary.get("execution", {}).get("run_id")
        or path.parent.name
    )

    return {
        "run_id": run_id,
        "run_type": "pipeline_run",
        "pipeline_id": summary.get("pipeline_id"),
        "status": summary.get("status"),
        "started_at": summary.get("started_at"),
        "ended_at": summary.get("ended_at"),
        "duration_seconds": summary.get("duration_seconds"),
        "scheduler_mode": scheduler.get("mode") or summary.get("scheduler_mode"),
        "max_workers": scheduler.get("max_workers") or summary.get("max_workers"),
        "matlab_max_workers": scheduler.get("matlab_max_workers") or summary.get("matlab_max_workers"),
        "summary_path": str(path),
        "nodes_total": node_counts["nodes_total"],
        "nodes_success": node_counts["nodes_success"],
        "nodes_failed": node_counts["nodes_failed"],
        "outputs_count": _count_outputs(summary),
        "warnings_count": _count_messages(summary, "warnings"),
        "errors_count": _count_messages(summary, "errors"),
    }


def _summarize_template_instance(path: Path) -> dict[str, Any] | None:
    payload = read_json_artifact(path)
    if not payload:
        return None

    instance_id = path.parent.name
    pipeline_summary = payload.get("pipeline_summary", {}) or {}

    return {
        "run_id": instance_id,
        "run_type": "dpabi_template_instance",
        "pipeline_id": pipeline_summary.get("pipeline_id"),
        "status": pipeline_summary.get("status"),
        "started_at": pipeline_summary.get("started_at"),
        "ended_at": pipeline_summary.get("ended_at"),
        "duration_seconds": pipeline_summary.get("duration_seconds"),
        "scheduler_mode": pipeline_summary.get("scheduler", {}).get("mode"),
        "max_workers": pipeline_summary.get("scheduler", {}).get("max_workers"),
        "matlab_max_workers": pipeline_summary.get("scheduler", {}).get("matlab_max_workers"),
        "summary_path": str(path),
        "nodes_total": _count_node_status(pipeline_summary)["nodes_total"],
        "nodes_success": _count_node_status(pipeline_summary)["nodes_success"],
        "nodes_failed": _count_node_status(pipeline_summary)["nodes_failed"],
        "outputs_count": _count_outputs(pipeline_summary),
        "warnings_count": _count_messages(pipeline_summary, "warnings"),
        "errors_count": _count_messages(pipeline_summary, "errors"),
    }


def build_run_index(
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    work = Path(work_dir)
    reports = Path(report_dir)
    out_dir = work / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, Any]] = []

    pipeline_runs_root = work / "pipeline_runs"
    if pipeline_runs_root.exists():
        for summary_path in sorted(pipeline_runs_root.glob("*/summary.json")):
            item = _summarize_pipeline_run(summary_path)
            if item:
                runs.append(item)
            else:
                warnings.append(f"Invalid pipeline summary: {summary_path}")

    template_instances_root = work / "dpabi" / "template_instances"
    if template_instances_root.exists():
        for execution_path in sorted(template_instances_root.glob("*/execution_summary.json")):
            item = _summarize_template_instance(execution_path)
            if item:
                runs.append(item)
            else:
                warnings.append(f"Invalid template instance summary: {execution_path}")

    report_artifacts = {
        "dataset_evaluation": reports / "dataset_evaluation" / "dataset_summary.json",
        "gpu_benchmark": reports / "gpu_benchmark" / "gpu_benchmark_summary.json",
        "dpabi_subject_wrapper": reports / "dpabi" / "dpabi_subject_wrapper_summary.json",
        "dpabi_wrapper_validation": work / "dpabi" / "dpabi_wrapper_compatibility_matrix.json",
        "validation": reports / "validation" / "validation_summary.json",
    }

    artifacts: list[dict[str, Any]] = []
    for name, path in report_artifacts.items():
        exists = path.exists()
        artifacts.append({
            "name": name,
            "exists": exists,
            "path": str(path),
        })

    runs = sorted(
        runs,
        key=lambda item: str(item.get("started_at") or item.get("run_id") or ""),
        reverse=True,
    )

    payload = {
        "ok": True,
        "node_id": "experiment_run_index",
        "backend": "python",
        "generated_at": _now_iso(),
        "runs_total": len(runs),
        "runs": runs,
        "artifacts": artifacts,
        "warnings": warnings,
        "errors": errors,
    }

    index_path = out_dir / "run_index.json"
    write_json_artifact(index_path, payload)

    payload["outputs"] = [str(index_path)]
    return payload


def create_experiment_record(
    experiment_id: str,
    name: str,
    run_ids: list[str],
    tags: list[str] | None = None,
    notes: str = "",
    work_dir: str = "./work",
) -> dict[str, Any]:
    if not is_safe_artifact_id(experiment_id):
        return {
            "ok": False,
            "errors": ["Invalid experiment_id."],
            "warnings": [],
        }

    index = build_run_index(work_dir=work_dir)
    available = {item.get("run_id"): item for item in index.get("runs", [])}

    missing = [run_id for run_id in run_ids if run_id not in available]

    record = {
        "ok": len(missing) == 0,
        "experiment_id": experiment_id,
        "name": name,
        "run_ids": run_ids,
        "tags": tags or [],
        "notes": notes,
        "created_at": _now_iso(),
        "missing_run_ids": missing,
        "runs": [available[run_id] for run_id in run_ids if run_id in available],
        "warnings": [f"Missing run_id: {item}" for item in missing],
        "errors": [],
    }

    out_dir = Path(work_dir) / "experiments" / "records"
    out_dir.mkdir(parents=True, exist_ok=True)

    record_path = out_dir / f"{experiment_id}.json"
    write_json_artifact(record_path, record)

    record["outputs"] = [str(record_path)]
    return record


def compare_experiment_runs(
    experiment_id: str,
    run_ids: list[str],
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict[str, Any]:
    if not is_safe_artifact_id(experiment_id):
        return {
            "ok": False,
            "errors": ["Invalid experiment_id."],
            "warnings": [],
        }

    index = build_run_index(work_dir=work_dir, report_dir=report_dir)
    runs = index.get("runs", [])

    if not run_ids:
        run_ids = [item.get("run_id") for item in runs[:5] if item.get("run_id")]

    selected = [item for item in runs if item.get("run_id") in set(run_ids)]
    missing = [run_id for run_id in run_ids if run_id not in {item.get("run_id") for item in selected}]

    comparison_rows = []
    for item in selected:
        comparison_rows.append({
            "run_id": item.get("run_id"),
            "run_type": item.get("run_type"),
            "pipeline_id": item.get("pipeline_id"),
            "status": item.get("status"),
            "duration_seconds": item.get("duration_seconds"),
            "scheduler_mode": item.get("scheduler_mode"),
            "max_workers": item.get("max_workers"),
            "matlab_max_workers": item.get("matlab_max_workers"),
            "nodes_total": item.get("nodes_total"),
            "nodes_success": item.get("nodes_success"),
            "nodes_failed": item.get("nodes_failed"),
            "outputs_count": item.get("outputs_count"),
            "warnings_count": item.get("warnings_count"),
            "errors_count": item.get("errors_count"),
            "summary_path": item.get("summary_path"),
        })

    out_dir = Path(report_dir) / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)

    comparison_json = out_dir / f"{experiment_id}_comparison.json"
    comparison_md = out_dir / f"{experiment_id}_comparison_report.md"

    payload = {
        "ok": len(selected) > 0,
        "experiment_id": experiment_id,
        "generated_at": _now_iso(),
        "run_ids": run_ids,
        "runs_compared": len(selected),
        "missing_run_ids": missing,
        "rows": comparison_rows,
        "warnings": [f"Missing run_id: {item}" for item in missing],
        "errors": [] if selected else ["No runs selected for comparison."],
    }

    write_json_artifact(comparison_json, payload)

    lines = []
    lines.append("# Experiment Run Comparison Report")
    lines.append("")
    lines.append(f"- Experiment ID: {experiment_id}")
    lines.append(f"- Runs compared: {len(selected)}")
    lines.append(f"- Missing run IDs: {missing}")
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    if comparison_rows:
        lines.append("| Run ID | Type | Pipeline | Status | Duration | Scheduler | Nodes OK/Total | Errors | Warnings |")
        lines.append("|---|---|---|---|---:|---|---:|---:|---:|")
        for row in comparison_rows:
            lines.append(
                f"| {row['run_id']} | {row['run_type']} | {row['pipeline_id']} | "
                f"{row['status']} | {row['duration_seconds']} | {row['scheduler_mode']} | "
                f"{row['nodes_success']}/{row['nodes_total']} | {row['errors_count']} | "
                f"{row['warnings_count']} |"
            )
    else:
        lines.append("No runs available for comparison.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This comparison only reads existing artifacts and does not execute pipelines or MATLAB.")

    comparison_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload["outputs"] = [str(comparison_json), str(comparison_md)]
    return payload
