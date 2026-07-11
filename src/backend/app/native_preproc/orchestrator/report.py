"""Minimal native preprocessing report helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.native_preproc import NativePreprocQC


def run_group_summary(
    output_dir: str | Path,
    *,
    subject_summaries: list[dict[str, Any]],
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    """Write a metadata-only group summary without fitting group statistics."""

    stage_id = "group_summary"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    warnings = ["group_summary_is_metadata_only_no_group_statistical_model"]
    errors: list[str] = []
    subject_count = len(subject_summaries)
    completed_subjects = sum(1 for item in subject_summaries if item.get("status") in {"succeeded", "warning"})
    blocked_subjects = sum(1 for item in subject_summaries if item.get("status") in {"blocked", "failed"})
    payload = {
        "summary_type": "native_preproc_group_summary",
        "subject_count": subject_count,
        "completed_subject_count": completed_subjects,
        "blocked_subject_count": blocked_subjects,
        "subject_summaries": subject_summaries,
        "limitations": [
            "No group-level statistical model is fitted.",
            "Golden/reference validation remains a later phase.",
        ],
    }
    try:
        report_path = context.stage_artifact_dir(stage_id) / "native_group_summary.json"
        atomic_write_json(report_path, payload, schema_version=1)
        output_ref = build_artifact_ref(
            report_path,
            artifact_type="final_report",
            metadata={
                "summary_type": payload["summary_type"],
                "subject_count": subject_count,
                "completed_subject_count": completed_subjects,
                "blocked_subject_count": blocked_subjects,
            },
        )
        qc = NativePreprocQC(
            status="warning",
            metrics={
                "subject_count": subject_count,
                "completed_subject_count": completed_subjects,
                "blocked_subject_count": blocked_subjects,
                "group_statistics_model": "not_run",
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={"summary_type": payload["summary_type"]},
            status="metadata_only",
            capability_level="metadata_only",
            qc=qc,
            output_artifacts=[output_ref],
            warnings=warnings,
            errors=errors,
        )
    except Exception as exc:
        errors.append(str(exc))
        qc = NativePreprocQC(status="fail", warnings=warnings, errors=errors)
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={"summary_type": payload["summary_type"]},
            status="blocked",
            capability_level="metadata_only",
            qc=qc,
            warnings=warnings,
            errors=errors,
        )
