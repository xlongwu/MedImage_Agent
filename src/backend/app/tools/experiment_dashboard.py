from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from src.backend.app.tools.experiment_tracker import build_run_index


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _normalize_status(status: Any) -> str:
    value = str(status or "UNKNOWN").upper()
    if value in {"SUCCESS", "OK", "COMPLETED"}:
        return "SUCCESS"
    if value in {"FAILED", "ERROR"}:
        return "FAILED"
    if value in {"PARTIAL", "WARNING"}:
        return "PARTIAL"
    if value in {"INVALID"}:
        return "INVALID"
    return "UNKNOWN"


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items(), key=lambda x: x[0]))


def _trend_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for index, run in enumerate(reversed(runs)):
        status = _normalize_status(run.get("status"))
        rows.append({
            "index": index + 1,
            "run_id": run.get("run_id"),
            "run_type": run.get("run_type"),
            "pipeline_id": run.get("pipeline_id"),
            "status": status,
            "success": 1 if status == "SUCCESS" else 0,
            "failed": 1 if status == "FAILED" else 0,
            "partial": 1 if status == "PARTIAL" else 0,
            "duration_seconds": _safe_number(run.get("duration_seconds")),
            "nodes_total": int(_safe_number(run.get("nodes_total"))),
            "nodes_success": int(_safe_number(run.get("nodes_success"))),
            "nodes_failed": int(_safe_number(run.get("nodes_failed"))),
            "outputs_count": int(_safe_number(run.get("outputs_count"))),
            "warnings_count": int(_safe_number(run.get("warnings_count"))),
            "errors_count": int(_safe_number(run.get("errors_count"))),
            "scheduler_mode": run.get("scheduler_mode") or "unknown",
        })

    return rows


def build_experiment_dashboard(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    refresh_index: bool = True,
) -> dict[str, Any]:
    work = Path(work_dir)
    reports = Path(report_dir)

    experiments_dir = work / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)

    report_out = reports / "experiments"
    report_out.mkdir(parents=True, exist_ok=True)

    if refresh_index:
        index = build_run_index(work_dir=work_dir, report_dir=report_dir)
    else:
        index = _read_json(experiments_dir / "run_index.json")
        if not index:
            index = build_run_index(work_dir=work_dir, report_dir=report_dir)

    runs = index.get("runs", []) if index else []
    trend = _trend_rows(runs)

    durations = [
        row["duration_seconds"]
        for row in trend
        if row["duration_seconds"] is not None
    ]

    statuses = [_normalize_status(run.get("status")) for run in runs]

    success_total = sum(1 for item in statuses if item == "SUCCESS")
    failed_total = sum(1 for item in statuses if item == "FAILED")
    partial_total = sum(1 for item in statuses if item == "PARTIAL")
    invalid_total = sum(1 for item in statuses if item == "INVALID")
    unknown_total = sum(1 for item in statuses if item == "UNKNOWN")

    total_outputs = sum(row["outputs_count"] for row in trend)
    total_warnings = sum(row["warnings_count"] for row in trend)
    total_errors = sum(row["errors_count"] for row in trend)

    status_distribution: dict[str, int] = {}
    for status in statuses:
        status_distribution[status] = status_distribution.get(status, 0) + 1

    pipeline_distribution = _count_by(runs, "pipeline_id")
    scheduler_distribution = _count_by(runs, "scheduler_mode")
    run_type_distribution = _count_by(runs, "run_type")

    dashboard = {
        "ok": True,
        "node_id": "experiment_dashboard",
        "backend": "python",
        "runs_total": len(runs),
        "success_total": success_total,
        "failed_total": failed_total,
        "partial_total": partial_total,
        "invalid_total": invalid_total,
        "unknown_total": unknown_total,
        "mean_duration_seconds": mean(durations) if durations else None,
        "median_duration_seconds": median(durations) if durations else None,
        "max_duration_seconds": max(durations) if durations else None,
        "total_outputs": total_outputs,
        "total_warnings": total_warnings,
        "total_errors": total_errors,
        "status_distribution": status_distribution,
        "pipeline_distribution": pipeline_distribution,
        "scheduler_distribution": scheduler_distribution,
        "run_type_distribution": run_type_distribution,
        "duration_trend": [
            {
                "index": row["index"],
                "run_id": row["run_id"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
            }
            for row in trend
        ],
        "error_warning_trend": [
            {
                "index": row["index"],
                "run_id": row["run_id"],
                "warnings_count": row["warnings_count"],
                "errors_count": row["errors_count"],
            }
            for row in trend
        ],
        "output_trend": [
            {
                "index": row["index"],
                "run_id": row["run_id"],
                "outputs_count": row["outputs_count"],
            }
            for row in trend
        ],
        "runs": trend,
        "artifacts": index.get("artifacts", []) if index else [],
        "warnings": index.get("warnings", []) if index else [],
        "errors": index.get("errors", []) if index else [],
    }

    json_path = experiments_dir / "dashboard_data.json"
    csv_path = experiments_dir / "dashboard_data.csv"
    report_path = report_out / "dashboard_report.md"

    json_path.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "index",
        "run_id",
        "run_type",
        "pipeline_id",
        "status",
        "duration_seconds",
        "scheduler_mode",
        "nodes_total",
        "nodes_success",
        "nodes_failed",
        "outputs_count",
        "warnings_count",
        "errors_count",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in trend:
            writer.writerow({key: row.get(key) for key in fieldnames})

    lines = []
    lines.append("# Experiment Dashboard Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Runs total: {dashboard['runs_total']}")
    lines.append(f"- Success: {success_total}")
    lines.append(f"- Failed: {failed_total}")
    lines.append(f"- Partial: {partial_total}")
    lines.append(f"- Invalid: {invalid_total}")
    lines.append(f"- Unknown: {unknown_total}")
    lines.append(f"- Mean duration seconds: {dashboard['mean_duration_seconds']}")
    lines.append(f"- Total outputs: {total_outputs}")
    lines.append(f"- Total warnings: {total_warnings}")
    lines.append(f"- Total errors: {total_errors}")
    lines.append("")
    lines.append("## Status Distribution")
    lines.append("")
    for key, value in status_distribution.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Pipeline Distribution")
    lines.append("")
    for key, value in pipeline_distribution.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Latest Runs")
    lines.append("")
    if trend:
        lines.append("| Index | Run ID | Pipeline | Status | Duration | Errors | Warnings |")
        lines.append("|---:|---|---|---|---:|---:|---:|")
        for row in trend[-10:]:
            lines.append(
                f"| {row['index']} | {row['run_id']} | {row['pipeline_id']} | "
                f"{row['status']} | {row['duration_seconds']} | "
                f"{row['errors_count']} | {row['warnings_count']} |"
            )
    else:
        lines.append("No runs found.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This dashboard only summarizes existing artifacts. It does not execute pipelines or MATLAB.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    dashboard["outputs"] = [str(json_path), str(csv_path), str(report_path)]
    return dashboard
