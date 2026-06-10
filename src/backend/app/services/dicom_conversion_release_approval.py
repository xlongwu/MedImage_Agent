"""DICOM conversion release approval service — Phase 4L-0.

Records and validates human release approval for DICOM-to-NIfTI
conversion.  Validates approval against release readiness, writes
metadata-only approval records, and never executes conversion.

Does NOT call dcm2niix.  Does NOT modify rawdata.  Does NOT enable
public conversion.  Does NOT add execute endpoints or frontend buttons.

Reference:
  docs/DICOM_CONVERSION_RELEASE_HARDENING.md  (Phase 4L-0)
  src/backend/app/schemas/dicom_conversion_release_approval.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.schemas.dicom_conversion_release_approval import (
    DicomConversionReleaseApprovalDecision,
    DicomConversionReleaseApprovalRecord,
    DicomConversionReleaseApprovalStatus,
    build_release_approval_summary,
    evaluate_release_approval,
    is_release_approval_complete,
    is_release_approval_valid,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: str, data: dict[str, Any]) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def persist_release_approval(
    record: DicomConversionReleaseApprovalRecord,
    *,
    project_dir: str = "",
    conversion_run_id: str = "",
    readiness_status: str = "unknown",
    gates_met: int = 0,
    gates_total: int = 32,
) -> DicomConversionReleaseApprovalDecision:
    """Persist a release approval record and return a decision.

    Validates the record against release readiness, writes the approval
    record and decision as JSON files, and returns the decision.

    Does NOT execute conversion.  Does NOT call dcm2niix.  Does NOT
    modify rawdata.  Does NOT enable public endpoints.

    Returns a ``DicomConversionReleaseApprovalDecision``.
    """
    warnings: list[str] = list(record.warnings)
    errors: list[str] = list(record.errors)

    # ── 1. Determine output paths ──
    output_root = (
        f"{project_dir}/conversion_runs/{conversion_run_id}"
        if project_dir and conversion_run_id
        else ""
    )

    if not output_root:
        return DicomConversionReleaseApprovalDecision(
            ok=False,
            status="blocked",
            approved=False,
            blocked=True,
            errors=["project_dir and conversion_run_id are required to persist approval."],
            safety_flags=_safety_flags(False),
        )

    record_path = f"{output_root}/release_approval_record.json"
    decision_path = f"{output_root}/release_approval_decision.json"

    # ── 2. Load release readiness if available ──
    try:
        from src.backend.app.services.dicom_conversion_release_readiness import (
            evaluate_conversion_release_readiness,
        )
        readiness_report = evaluate_conversion_release_readiness(
            project_id=record.project_id,
            conversion_run_id=conversion_run_id,
            output_root=output_root,
        )
        readiness_status = readiness_report.status
        gates_met = readiness_report.gates_met
        gates_total = readiness_report.gates_total
    except Exception as exc:
        warnings.append(f"Could not load release readiness: {exc}")

    # ── 3. Validate record completeness ──
    if not is_release_approval_complete(record):
        decision = evaluate_release_approval(
            record,
            readiness_status=readiness_status,
            gates_met=gates_met,
            gates_total=gates_total,
            output_root=output_root,
            record_path=record_path,
            decision_path=decision_path,
        )
        # Still write the incomplete record for audit purposes
        _write_json(record_path, {
            **record.model_dump(),
            "persisted_at": _now_iso(),
            "persisted_incomplete": True,
        })
        _write_json(decision_path, decision.model_dump())
        return decision

    # ── 4. Validate against readiness ──
    ok_valid, issues = is_release_approval_valid(
        record,
        readiness_status=readiness_status,
        gates_met=gates_met,
        gates_total=gates_total,
    )

    if not ok_valid:
        decision = DicomConversionReleaseApprovalDecision(
            ok=False,
            status="blocked",
            approved=False,
            blocked=True,
            approval_record_path=record_path,
            decision_path=decision_path,
            blocking_issues=issues,
            warnings=warnings,
            errors=errors,
            safety_flags=_safety_flags(False),
        )
        _write_json(record_path, {
            **record.model_dump(),
            "persisted_at": _now_iso(),
            "persisted_blocked": True,
        })
        _write_json(decision_path, decision.model_dump())
        return decision

    # ── 5. Approve ──
    record.status = "approved"
    record.approved_at = _now_iso()

    _write_json(record_path, {
        **record.model_dump(),
        "persisted_at": record.approved_at,
        "release_readiness_status": readiness_status,
        "gates_met": gates_met,
        "gates_total": gates_total,
    })

    decision = evaluate_release_approval(
        record,
        readiness_status=readiness_status,
        gates_met=gates_met,
        gates_total=gates_total,
        output_root=output_root,
        record_path=record_path,
        decision_path=decision_path,
    )
    _write_json(decision_path, decision.model_dump())

    return decision


def read_release_approval(
    project_id: str = "",
    conversion_run_id: str = "",
    *,
    project_dir: str = "",
) -> DicomConversionReleaseApprovalDecision:
    """Read an existing release approval record and return its decision.

    Does NOT execute conversion.  Does NOT call dcm2niix.
    Does NOT modify rawdata.
    """
    if not project_dir or not conversion_run_id:
        return DicomConversionReleaseApprovalDecision(
            ok=False,
            status="blocked",
            approved=False,
            blocked=True,
            errors=["project_dir and conversion_run_id are required."],
            safety_flags=_safety_flags(False),
        )

    output_root = f"{project_dir}/conversion_runs/{conversion_run_id}"
    decision_path = Path(output_root) / "release_approval_decision.json"

    if not decision_path.exists():
        return DicomConversionReleaseApprovalDecision(
            ok=False,
            status="blocked",
            approved=False,
            blocked=True,
            blocking_issues=["No release approval decision has been recorded yet."],
            safety_flags=_safety_flags(False),
        )

    try:
        data = json.loads(decision_path.read_text(encoding="utf-8"))
        return DicomConversionReleaseApprovalDecision(**data)
    except Exception as exc:
        return DicomConversionReleaseApprovalDecision(
            ok=False,
            status="blocked",
            approved=False,
            blocked=True,
            errors=[f"Failed to read release approval decision: {exc}"],
            safety_flags=_safety_flags(False),
        )


def _safety_flags(approved: bool) -> dict[str, bool]:
    return {
        "public_execution_disabled": True,
        "frontend_execute_disabled": True,
        "spm_dpabi_matlab_disabled": True,
        "full_preprocessing_disabled": True,
        "human_release_approval_recorded": approved,
        "rawdata_read_only": True,
    }


__all__ = [
    "persist_release_approval",
    "read_release_approval",
]
