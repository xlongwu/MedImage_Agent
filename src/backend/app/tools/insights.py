"""Insights engine -- generate operational metrics from SessionDB."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

from src.backend.app.memory.session_db import SessionDB


def build_insights(
    db_path: str = "outputs/memory/sessions/archive.sqlite",
    report_dir: str = "./reports/insights",
) -> dict[str, Any]:
    db = SessionDB(db_path)
    stats = db.stats()

    runs = db.query_runs(limit=200)
    errors = db.query_errors(limit=500)
    error_cats = db.error_categories()

    # Success/failure breakdown
    total = stats["total_runs"]
    success = stats["success_runs"]
    failed = total - success
    success_rate = round(success / total * 100, 1) if total > 0 else 0
    failure_rate = round(failed / total * 100, 1) if total > 0 else 0

    # Duration stats
    durations = [r.get("duration_seconds") for r in runs if r.get("duration_seconds")]
    avg_duration = round(mean(durations), 1) if durations else 0
    median_duration = round(median(durations), 1) if durations else 0
    max_duration = round(max(durations), 1) if durations else 0

    # Node-level aggregation (query all nodes)
    node_stats: dict[str, dict[str, Any]] = {}
    for run in runs:
        nodes = db.query_nodes_by_run(run["run_id"])
        for n in nodes:
            nid = n["node_id"]
            if nid not in node_stats:
                node_stats[nid] = {"total": 0, "success": 0, "failed": 0, "durations": []}
            node_stats[nid]["total"] += 1
            if n.get("ok"):
                node_stats[nid]["success"] += 1
            else:
                node_stats[nid]["failed"] += 1
            if n.get("duration_seconds"):
                node_stats[nid]["durations"].append(n["duration_seconds"])

    slowest_nodes = sorted(
        [{"node_id": k, "avg_duration": round(mean(v["durations"]), 1),
          "count": v["total"], "failure_rate": round(v["failed"] / max(v["total"], 1) * 100, 1)}
         for k, v in node_stats.items() if v["durations"]],
        key=lambda x: -x["avg_duration"],
    )[:5]

    most_failed = sorted(
        [{"node_id": k, "failed": v["failed"], "total": v["total"],
          "failure_rate": round(v["failed"] / max(v["total"], 1) * 100, 1)}
         for k, v in node_stats.items()],
        key=lambda x: -x["failed"],
    )[:5]

    # Recent trend (last 10 runs)
    recent = runs[:10]
    trend = [{"run_id": r["run_id"], "status": r["status"],
              "started_at": r.get("started_at")} for r in recent]

    # Subject failure map
    subject_failures: dict[str, int] = {}
    for run in runs[-50:]:
        nodes = db.query_nodes_by_run(run["run_id"])
        for n in nodes:
            sid = n.get("subject_id", "project")
            if sid != "project" and not n.get("ok"):
                subject_failures[sid] = subject_failures.get(sid, 0) + 1

    insights = {
        "ok": True,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_runs": total,
            "success": success,
            "failed": failed,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "avg_duration_seconds": avg_duration,
            "median_duration_seconds": median_duration,
            "max_duration_seconds": max_duration,
            "total_errors_logged": stats["total_errors"],
        },
        "slowest_nodes": slowest_nodes,
        "most_failed_nodes": most_failed,
        "top_error_categories": error_cats[:5],
        "recent_trend": trend,
        "subject_failure_map": {
            k: v for k, v in sorted(subject_failures.items(), key=lambda x: -x[1])[:20]
        },
    }

    db.close()

    # Write reports
    report_out = Path(report_dir)
    report_out.mkdir(parents=True, exist_ok=True)
    (report_out / "insights_summary.json").write_text(
        json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown report
    lines = [
        "# MedImage Agent Insights Report",
        "",
        f"Generated: {insights['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Total Runs: **{total}**",
        f"- Success Rate: **{success_rate}%**",
        f"- Failure Rate: **{failure_rate}%**",
        f"- Avg Duration: **{avg_duration}s** (median: {median_duration}s, max: {max_duration}s)",
        f"- Total Errors Logged: **{stats['total_errors']}**",
        "",
        "## Slowest Nodes (avg duration)",
        "",
        "| Node | Avg Duration (s) | Count | Failure Rate |",
        "|------|-----------------:|------:|-------------:|",
    ]
    for n in slowest_nodes:
        lines.append(f"| {n['node_id']} | {n['avg_duration']} | {n['count']} | {n['failure_rate']}% |")

    lines += [
        "",
        "## Most Failed Nodes",
        "",
        "| Node | Failed | Total | Failure Rate |",
        "|------|-------:|------:|-------------:|",
    ]
    for n in most_failed:
        lines.append(f"| {n['node_id']} | {n['failed']} | {n['total']} | {n['failure_rate']}% |")

    lines += [
        "",
        "## Top Error Categories",
        "",
        "| Category | Count |",
        "|----------|------:|",
    ]
    for c in error_cats[:5]:
        lines.append(f"| {c['category']} | {c['count']} |")

    lines += ["", "## Safety Note", "",
              "Insights are generated from run history only. No rawdata is accessed."]
    (report_out / "insights_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return insights
