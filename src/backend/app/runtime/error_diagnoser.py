from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.tools.error_classifier import classify_error
from src.backend.app.runtime.run_inspector import inspect_run


LOG_READ_LIMIT = 20_000


def _read_text_excerpt(path: str | None) -> str:
    if not path:
        return ""

    p = Path(path)
    normalized = str(p).replace("\\", "/")

    if not normalized.startswith("outputs/logs/") and "/logs/" not in normalized:
        return ""

    if p.suffix.lower() != ".log":
        return ""

    if not p.exists():
        return ""

    text = p.read_text(encoding="utf-8", errors="replace")
    if len(text) <= LOG_READ_LIMIT * 2:
        return text

    return (
        text[:LOG_READ_LIMIT]
        + "\n\n...[LOG TRUNCATED]...\n\n"
        + text[-LOG_READ_LIMIT:]
    )


def _categorize_issue(message: str, matched_errors: list[dict[str, Any]]) -> str:
    text = message.lower()

    for item in matched_errors:
        source = str(item.get("source", "")).lower()
        if source == "matlab":
            return "MATLAB_ERROR"
        if source == "spm":
            return "SPM_ERROR"
        if source == "dpabi":
            return "DPABI_ERROR"
        if source == "python":
            return "PYTHON_DEPENDENCY_ERROR"

    if "matlab" in text:
        return "MATLAB_ERROR"
    if "spm" in text:
        return "SPM_ERROR"
    if "nifti" in text or ".nii" in text:
        return "NIFTI_IO_ERROR"
    if "missing dependency" in text or "importerror" in text:
        return "PYTHON_DEPENDENCY_ERROR"
    if "dataset" in text or "bids" in text:
        return "DATASET_STRUCTURE_ERROR"
    if "qc" in text or "nan_count" in text:
        return "QC_FAILURE"

    return "UNKNOWN_ERROR"


def _retry_recommendation(category: str, matched_errors: list[dict[str, Any]]) -> str:
    if matched_errors:
        retryable_values = {str(item.get("retryable")) for item in matched_errors}
        if "false" in retryable_values:
            return "FIX_CONFIG_THEN_RETRY"
        if "true" in retryable_values:
            return "SAFE_RETRY"

    if category in {"PYTHON_DEPENDENCY_ERROR"}:
        return "FIX_DEPENDENCY_THEN_RETRY"
    if category in {"MATLAB_ERROR", "SPM_ERROR"}:
        return "RERUN_ENVIRONMENT_CHECK"
    if category in {"QC_FAILURE"}:
        return "MANUAL_REVIEW"

    return "MANUAL_REVIEW"


def _collect_issue_from_state(
    issue_id: str,
    state: dict[str, Any],
    scope: str,
) -> dict[str, Any] | None:
    status = state.get("status")
    errors = state.get("errors", []) or []
    warnings = state.get("warnings", []) or []

    if status not in {"FAILED", "NEEDS_REVIEW"} and not errors:
        return None

    stdout_log = state.get("stdout_log") or state.get("log_path")
    stderr_log = state.get("stderr_log")

    stdout_excerpt = _read_text_excerpt(stdout_log)
    stderr_excerpt = _read_text_excerpt(stderr_log)

    messages: list[str] = []
    messages.extend(str(item) for item in errors)
    messages.extend(str(item) for item in warnings)

    if stdout_excerpt:
        messages.append(stdout_excerpt)
    if stderr_excerpt:
        messages.append(stderr_excerpt)

    classified = classify_error("; ".join(messages))
    category = classified.get("category", "UNKNOWN_ERROR")
    retry = "SAFE_RETRY" if classified.get("retryable") else "MANUAL_REVIEW"

    return {
        "issue_id": issue_id,
        "scope": scope,
        "subject_id": state.get("subject"),
        "node": state.get("node"),
        "status": status,
        "category": category,
        "message": "; ".join(str(item) for item in errors[:3]) if errors else f"status={status}",
        "matched_error_ids": [category],
        "probable_causes": classified.get("likely_causes", []),
        "suggested_fixes": classified.get("suggested_fixes", []),
        "retry_recommendation": retry,
        "severity": classified.get("severity", "medium"),
        "classified": classified.get("classified", False),
        "stdout_log": stdout_log,
        "stderr_log": stderr_log,
    }


def _build_retry_plan(run_id: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    steps = []
    safe_to_auto_retry = True

    for index, issue in enumerate(issues, start=1):
        recommendation = issue.get("retry_recommendation", "MANUAL_REVIEW")

        if recommendation != "SAFE_RETRY":
            safe_to_auto_retry = False

        steps.append({
            "step_id": f"retry_{index:03d}",
            "action": recommendation,
            "reason": issue.get("message"),
            "scope": issue.get("scope"),
            "subject_id": issue.get("subject_id"),
            "node": issue.get("node"),
            "requires_user_action": recommendation != "SAFE_RETRY",
            "matched_error_ids": issue.get("matched_error_ids", []),
            "suggested_fixes": issue.get("suggested_fixes", []),
        })

    return {
        "run_id": run_id,
        "safe_to_auto_retry": safe_to_auto_retry and bool(issues),
        "requires_approval": True,
        "steps": steps,
    }


def _write_markdown_report(
    path: Path,
    run_id: str,
    diagnosis: dict[str, Any],
    retry_plan: dict[str, Any],
) -> None:
    lines: list[str] = []
    lines.append("# Error Diagnosis Report")
    lines.append("")
    lines.append(f"- Run ID: {run_id}")
    lines.append(f"- Pipeline status: {diagnosis.get('status')}")
    lines.append(f"- Issues total: {diagnosis.get('issues_total')}")
    lines.append("")
    lines.append("## Issues")
    lines.append("")

    issues = diagnosis.get("issues", [])
    if not issues:
        lines.append("No failed or suspicious nodes were detected.")
    else:
        for issue in issues:
            lines.append(f"### {issue.get('issue_id')} · {issue.get('node')}")
            lines.append("")
            lines.append(f"- Scope: {issue.get('scope')}")
            lines.append(f"- Subject: {issue.get('subject_id')}")
            lines.append(f"- Status: {issue.get('status')}")
            lines.append(f"- Category: {issue.get('category')}")
            lines.append(f"- Retry recommendation: {issue.get('retry_recommendation')}")
            lines.append(f"- Message: {issue.get('message')}")
            lines.append("")
            if issue.get("matched_error_ids"):
                lines.append("Matched known errors:")
                for item in issue.get("matched_error_ids", []):
                    lines.append(f"- {item}")
                lines.append("")
            if issue.get("suggested_fixes"):
                lines.append("Suggested fixes:")
                for fix in issue.get("suggested_fixes", []):
                    lines.append(f"- {fix}")
                lines.append("")

    lines.append("## Retry Plan")
    lines.append("")
    lines.append(f"- Requires approval: {retry_plan.get('requires_approval')}")
    lines.append(f"- Safe to auto retry: {retry_plan.get('safe_to_auto_retry')}")
    lines.append("")

    steps = retry_plan.get("steps", [])
    if not steps:
        lines.append("No retry steps are required.")
    else:
        for step in steps:
            lines.append(
                f"- {step.get('step_id')}: {step.get('action')} "
                f"for {step.get('subject_id')} / {step.get('node')}"
            )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This retry plan is advisory only. It does not execute retries automatically.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def diagnose_run(
    run_id: str,
    work_dir: str = "./work",
    log_dir: str = "./logs",
    memory_root: str = ".",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    inspection = inspect_run(run_id=run_id, work_dir=work_dir)
    summary = inspection.get("summary") or {}
    pipeline_status = summary.get("status", "UNKNOWN")

    issues: list[dict[str, Any]] = []

    counter = 1

    for state in inspection.get("project_states", []):
        issue = _collect_issue_from_state(
            issue_id=f"issue_{counter:03d}",
            state=state,
            scope="project",
        )
        if issue:
            issues.append(issue)
            counter += 1

    for subject in inspection.get("subjects", []):
        for state in subject.get("nodes", []):
            issue = _collect_issue_from_state(
                issue_id=f"issue_{counter:03d}",
                state=state,
                scope="subject",
            )
            if issue:
                issues.append(issue)
                counter += 1

    out_dir = Path(work_dir) / "diagnosis" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    retry_plan = _build_retry_plan(run_id, issues)

    diagnosis_path = out_dir / "diagnosis.json"
    diagnosis_report_path = out_dir / "diagnosis_report.md"
    retry_plan_path = out_dir / "retry_plan.json"
    retry_plan_md_path = out_dir / "retry_plan.md"

    diagnosis = {
        "ok": True,
        "run_id": run_id,
        "status": pipeline_status,
        "issues_total": len(issues),
        "issues": issues,
        "retry_plan_path": str(retry_plan_path),
        "outputs": [
            str(diagnosis_path),
            str(diagnosis_report_path),
            str(retry_plan_path),
            str(retry_plan_md_path),
        ],
        "warnings": warnings + inspection.get("warnings", []),
        "errors": errors,
    }

    diagnosis_path.write_text(
        json.dumps(diagnosis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    retry_plan_path.write_text(
        json.dumps(retry_plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_markdown_report(
        path=diagnosis_report_path,
        run_id=run_id,
        diagnosis=diagnosis,
        retry_plan=retry_plan,
    )

    retry_lines = [
        "# Retry Plan",
        "",
        f"- Run ID: {run_id}",
        f"- Requires approval: {retry_plan.get('requires_approval')}",
        f"- Safe to auto retry: {retry_plan.get('safe_to_auto_retry')}",
        "",
        "## Steps",
        "",
    ]

    if retry_plan.get("steps"):
        for step in retry_plan["steps"]:
            retry_lines.append(f"### {step.get('step_id')}")
            retry_lines.append("")
            retry_lines.append(f"- Action: {step.get('action')}")
            retry_lines.append(f"- Subject: {step.get('subject_id')}")
            retry_lines.append(f"- Node: {step.get('node')}")
            retry_lines.append(f"- Reason: {step.get('reason')}")
            retry_lines.append(f"- Requires user action: {step.get('requires_user_action')}")
            retry_lines.append("")
    else:
        retry_lines.append("No retry required.")

    retry_lines.append("")
    retry_lines.append("This file is advisory only. It does not execute commands.")

    retry_plan_md_path.write_text("\n".join(retry_lines) + "\n", encoding="utf-8")

    return diagnosis
