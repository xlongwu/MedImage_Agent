from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from backend.app.runtime.memory_store import (
    append_run_history,
    ensure_memory_layout,
    match_error_patterns,
)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"YAML file not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run_background_review(
    agent_run_id: str,
    project_config_path: str,
    agent_summary_path: str | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    ensure_memory_layout(".")

    project_config = _load_yaml(project_config_path)
    project_name = project_config.get("project", {}).get("name", "default_project")
    runtime = project_config.get("runtime", {})
    work_dir = runtime.get("work_dir", "./work")
    report_dir = runtime.get("report_dir", "./reports")

    agent_run_dir = Path(work_dir) / "agent_runs" / agent_run_id
    agent_run_dir.mkdir(parents=True, exist_ok=True)

    if agent_summary_path:
        summary_path = Path(agent_summary_path)
    else:
        summary_path = agent_run_dir / "agent_summary.json"

    agent_summary = _read_json(summary_path)
    if not agent_summary:
        warnings.append(f"Missing or invalid agent summary: {summary_path}")
        agent_summary = {}

    pipeline_summary_path = agent_summary.get("pipeline_summary_path")
    pipeline_summary = _read_json(Path(pipeline_summary_path)) if pipeline_summary_path else None
    if not pipeline_summary:
        warnings.append("Missing or invalid pipeline summary.")
        pipeline_summary = {}

    dataset_summary_path = Path(report_dir) / "dataset_evaluation" / "dataset_summary.json"
    dataset_summary = _read_json(dataset_summary_path)
    if not dataset_summary:
        warnings.append(f"Missing dataset summary: {dataset_summary_path}")
        dataset_summary = {}

    exclusion_path = Path(report_dir) / "dataset_evaluation" / "exclusion_recommendations.csv"
    exclusion_rows = _read_csv_rows(exclusion_path)

    all_errors: list[str] = []
    for source in [agent_summary, pipeline_summary, dataset_summary]:
        value = source.get("errors", [])
        if isinstance(value, list):
            all_errors.extend(str(x) for x in value)
        elif value:
            all_errors.append(str(value))

    matched_errors = match_error_patterns(all_errors, ".")

    pipeline_status = pipeline_summary.get("status") or agent_summary.get("pipeline_status")
    dataset_quality_score = dataset_summary.get("dataset_quality_score")
    subjects_total = dataset_summary.get("subjects_total")
    subjects_include = dataset_summary.get("subjects_include")
    subjects_manual_review = dataset_summary.get("subjects_manual_review")
    subjects_exclude = dataset_summary.get("subjects_exclude")

    review_lines: list[str] = []
    review_lines.append("# Background Review Summary")
    review_lines.append("")
    review_lines.append(f"- Agent run ID: {agent_run_id}")
    review_lines.append(f"- Project: {project_name}")
    review_lines.append(f"- Pipeline status: {pipeline_status}")
    review_lines.append(f"- Dataset quality score: {dataset_quality_score}")
    review_lines.append(f"- Total subjects: {subjects_total}")
    review_lines.append(f"- Include: {subjects_include}")
    review_lines.append(f"- Manual review: {subjects_manual_review}")
    review_lines.append(f"- Exclude: {subjects_exclude}")
    review_lines.append("")
    review_lines.append("## Warnings")
    review_lines.append("")
    if warnings:
        for item in warnings:
            review_lines.append(f"- {item}")
    else:
        review_lines.append("- None")
    review_lines.append("")
    review_lines.append("## Errors")
    review_lines.append("")
    if all_errors:
        for item in all_errors:
            review_lines.append(f"- {item}")
    else:
        review_lines.append("- None")
    review_lines.append("")
    review_lines.append("## Matched Error Knowledge")
    review_lines.append("")
    if matched_errors:
        for item in matched_errors:
            review_lines.append(f"- {item.get('id')}: {item.get('pattern')}")
            fixes = item.get("suggested_fixes", [])
            for fix in fixes:
                review_lines.append(f"  - Suggested fix: {fix}")
    else:
        review_lines.append("- None")
    review_lines.append("")
    review_lines.append("## Subjects Requiring Attention")
    review_lines.append("")
    if exclusion_rows:
        for row in exclusion_rows:
            review_lines.append(
                f"- {row.get('subject_id')}: {row.get('recommendation')} — {row.get('reasons')}"
            )
    else:
        review_lines.append("- None")

    review_summary_path = agent_run_dir / "review_summary.md"
    review_summary_path.write_text("\n".join(review_lines) + "\n", encoding="utf-8")

    patch_lines: list[str] = []
    patch_lines.append("# Proposed Memory Patch")
    patch_lines.append("")
    patch_lines.append("This file is a proposal only. Review before merging into MEMORY.md or LESSONS.md.")
    patch_lines.append("")
    patch_lines.append("## Proposed Project Lesson")
    patch_lines.append("")
    patch_lines.append(f"- Run `{agent_run_id}` finished with pipeline status `{pipeline_status}`.")
    if dataset_quality_score is not None:
        patch_lines.append(f"- Dataset quality score was `{dataset_quality_score}`.")
    if subjects_exclude:
        patch_lines.append(f"- `{subjects_exclude}` subject(s) were recommended for exclusion.")
    if subjects_manual_review:
        patch_lines.append(f"- `{subjects_manual_review}` subject(s) require manual review.")
    if matched_errors:
        patch_lines.append("")
        patch_lines.append("## Proposed Error KB Updates")
        patch_lines.append("")
        patch_lines.append("Matched known errors; no new error pattern is automatically added.")
    patch_lines.append("")
    patch_lines.append("## Safety Note")
    patch_lines.append("")
    patch_lines.append("Do not store PHI or raw imaging data in memory.")

    proposed_patch_path = agent_run_dir / "proposed_memory_patch.md"
    proposed_patch_path.write_text("\n".join(patch_lines) + "\n", encoding="utf-8")

    history_record = {
        "agent_run_id": agent_run_id,
        "project_name": project_name,
        "pipeline_status": pipeline_status,
        "dataset_quality_score": dataset_quality_score,
        "subjects_total": subjects_total,
        "subjects_include": subjects_include,
        "subjects_manual_review": subjects_manual_review,
        "subjects_exclude": subjects_exclude,
        "warnings_count": len(warnings),
        "errors_count": len(all_errors),
        "matched_error_patterns": [e.get("id") for e in matched_errors],
    }

    history_path = append_run_history(project_name, history_record, ".")

    return {
        "ok": True,
        "agent_run_id": agent_run_id,
        "project_name": project_name,
        "pipeline_status": pipeline_status,
        "review_summary_path": str(review_summary_path),
        "proposed_patch_path": str(proposed_patch_path),
        "history_path": str(history_path),
        "warnings": warnings,
        "errors": all_errors,
        "matched_errors": matched_errors,
    }
