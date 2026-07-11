"""DICOM Conversion Release Approval Schema — Phase 4L-0.

Defines release approval statuses, approval record models, approval
decision models, and pure helper functions for recording and validating
human release approval for DICOM-to-NIfTI conversion.

Schema-only module.  No subprocess.  No file writes.  No dcm2niix.
No rawdata modification.  No SPM/DPABI/MATLAB.

Reference:
  docs/预处理与科学计算/DICOM转换/发布加固.md  (Phase 4L-0)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# 1. Literal type aliases
# ═══════════════════════════════════════════════════════════════════════

DicomConversionReleaseApprovalStatus = Literal[
    "missing",
    "draft",
    "approved",
    "rejected",
    "revoked",
    "expired",
]

DicomConversionReleaseApprovalDecisionStatus = Literal[
    "blocked",
    "incomplete",
    "approved",
    "rejected",
    "no_release_readiness",
]


# ═══════════════════════════════════════════════════════════════════════
# 2. Pydantic models
# ═══════════════════════════════════════════════════════════════════════


class DicomConversionReleaseApprovalRecord(BaseModel):
    """Human release approval record for DICOM conversion.

    Must be completed by a project maintainer before public conversion
    can be enabled.  Recording this approval does NOT automatically
    enable public conversion.
    """

    approval_id: str = ""
    project_id: str = ""
    conversion_run_id: str = ""
    status: DicomConversionReleaseApprovalStatus = "missing"

    # Maintainer identity
    approved_by: str = ""
    approved_at: str | None = None
    expires_at: str | None = None

    # Evidence links
    go_no_go_review_id: str = ""
    release_readiness_status: str = "unknown"
    gates_met: int = 0
    gates_total: int = 32

    # Human approval statement (free-text, must be non-empty)
    human_approval_statement: str = ""

    # Safety acknowledgements
    rawdata_readonly_acknowledged: bool = False
    no_clinical_use_acknowledged: bool = False
    rollback_acknowledged: bool = False
    approval_audit_acknowledged: bool = False
    public_endpoint_acknowledged: bool = False
    frontend_execute_acknowledged: bool = False
    spm_dpabi_matlab_disabled_acknowledged: bool = False

    # Metadata
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionReleaseApprovalDecision(BaseModel):
    """Result of evaluating a release approval record against readiness."""

    ok: bool = False
    status: DicomConversionReleaseApprovalDecisionStatus = "blocked"
    approved: bool = False
    blocked: bool = True
    approval_record_path: str | None = None
    decision_path: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# 3. Constants
# ═══════════════════════════════════════════════════════════════════════

_REQUIRED_RELEASE_APPROVAL_FIELDS: frozenset[str] = frozenset({
    "approved_by",
    "human_approval_statement",
    "rawdata_readonly_acknowledged",
    "no_clinical_use_acknowledged",
    "rollback_acknowledged",
    "approval_audit_acknowledged",
    "public_endpoint_acknowledged",
    "frontend_execute_acknowledged",
    "spm_dpabi_matlab_disabled_acknowledged",
})

_REQUIRED_SAFETY_ACKNOWLEDGEMENTS: frozenset[str] = frozenset({
    "rawdata_readonly_acknowledged",
    "no_clinical_use_acknowledged",
    "rollback_acknowledged",
    "approval_audit_acknowledged",
    "public_endpoint_acknowledged",
    "frontend_execute_acknowledged",
    "spm_dpabi_matlab_disabled_acknowledged",
})

_DEFAULT_APPROVAL_EXPIRY_DAYS: int = 180
_ACCEPTABLE_RELEASE_READINESS_STATUSES: frozenset[str] = frozenset({
    "ready_for_human_release_review",
    "warning",
})


# ═══════════════════════════════════════════════════════════════════════
# 4. Pure helper functions
# ═══════════════════════════════════════════════════════════════════════


def is_release_approval_complete(
    record: DicomConversionReleaseApprovalRecord,
) -> bool:
    """Return True if all required release approval fields are non-empty/True.

    Pure function — no file I/O, no subprocess.
    """
    for field in _REQUIRED_RELEASE_APPROVAL_FIELDS:
        value = getattr(record, field, None)
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, bool) and not value:
            return False
    return True


def is_release_approval_valid(
    record: DicomConversionReleaseApprovalRecord,
    *,
    readiness_status: str = "unknown",
    gates_met: int = 0,
    gates_total: int = 32,
) -> tuple[bool, list[str]]:
    """Validate a release approval record against readiness evidence.

    Returns ``(ok, issues)``.  Pure function — no file I/O.
    """
    issues: list[str] = []

    # ── Gate count ──
    if gates_met < gates_total:
        issues.append(
            f"Not all safety gates met: {gates_met}/{gates_total}. "
            f"All {gates_total} gates must be met before release approval."
        )

    # ── Release readiness ──
    if readiness_status not in _ACCEPTABLE_RELEASE_READINESS_STATUSES:
        issues.append(
            f"Release readiness is not ready for human review: "
            f"status={readiness_status}.  Must be one of "
            f"{sorted(_ACCEPTABLE_RELEASE_READINESS_STATUSES)}."
        )

    # ── Maintainer identity ──
    if not record.approved_by.strip():
        issues.append("Maintainer identity (approved_by) is required.")

    # ── Human approval statement ──
    if not record.human_approval_statement.strip():
        issues.append("Human approval statement is required.")

    # ── Safety acknowledgements ──
    ack_labels: dict[str, str] = {
        "rawdata_readonly_acknowledged": "Rawdata read-only",
        "no_clinical_use_acknowledged": "No clinical use",
        "rollback_acknowledged": "Rollback policy",
        "approval_audit_acknowledged": "Approval/audit integration",
        "public_endpoint_acknowledged": "Public endpoint status",
        "frontend_execute_acknowledged": "Frontend execute button status",
        "spm_dpabi_matlab_disabled_acknowledged": "SPM/DPABI/MATLAB disabled",
    }
    for field, label in ack_labels.items():
        if not getattr(record, field, False):
            issues.append(f"Safety acknowledgement missing: {label} ({field}).")

    return len(issues) == 0, issues


def evaluate_release_approval(
    record: DicomConversionReleaseApprovalRecord,
    *,
    readiness_status: str = "unknown",
    gates_met: int = 0,
    gates_total: int = 32,
    output_root: str = "",
    record_path: str = "",
    decision_path: str = "",
) -> DicomConversionReleaseApprovalDecision:
    """Evaluate a release approval record and produce a decision.

    Pure function — no file I/O, no subprocess, no dcm2niix.
    """
    warnings: list[str] = list(record.warnings)
    errors: list[str] = list(record.errors)
    blocking: list[str] = []

    # ── Check approval completeness ──
    if not is_release_approval_complete(record):
        missing = [
            f for f in _REQUIRED_RELEASE_APPROVAL_FIELDS
            if not _field_is_set(record, f)
        ]
        blocking.append(
            f"Release approval record is incomplete. "
            f"Missing fields: {missing}."
        )

    # ── Validate against readiness ──
    ok_valid, validation_issues = is_release_approval_valid(
        record,
        readiness_status=readiness_status,
        gates_met=gates_met,
        gates_total=gates_total,
    )
    if not ok_valid:
        blocking.extend(validation_issues)

    # ── Determine status ──
    if record.status == "rejected":
        decision_status: DicomConversionReleaseApprovalDecisionStatus = "rejected"
    elif record.status == "revoked":
        decision_status = "rejected"
    elif blocking:
        decision_status = "blocked"
    elif not is_release_approval_complete(record):
        decision_status = "incomplete"
    elif readiness_status not in _ACCEPTABLE_RELEASE_READINESS_STATUSES:
        decision_status = "no_release_readiness"
    else:
        decision_status = "approved"

    approved = decision_status == "approved"

    return DicomConversionReleaseApprovalDecision(
        ok=len(blocking) == 0 and len(errors) == 0,
        status=decision_status,
        approved=approved,
        blocked=not approved,
        approval_record_path=record_path or (
            f"{output_root}/release_approval_record.json" if output_root else None
        ),
        decision_path=decision_path or (
            f"{output_root}/release_approval_decision.json" if output_root else None
        ),
        missing_fields=[f for f in _REQUIRED_RELEASE_APPROVAL_FIELDS if not _field_is_set(record, f)],
        blocking_issues=blocking,
        warnings=warnings,
        errors=errors,
        safety_flags={
            "public_execution_disabled": True,
            "frontend_execute_disabled": True,
            "spm_dpabi_matlab_disabled": True,
            "full_preprocessing_disabled": True,
            "human_release_approval_recorded": approved,
            "rawdata_read_only": True,
        },
    )


def build_release_approval_summary(
    record: DicomConversionReleaseApprovalRecord,
) -> dict[str, Any]:
    """Build a human-readable summary of a release approval record.

    Pure function — no file I/O, no subprocess.
    """
    complete = is_release_approval_complete(record)
    return {
        "approval_id": record.approval_id,
        "project_id": record.project_id,
        "status": record.status,
        "complete": complete,
        "approved_by": record.approved_by,
        "approved_at": record.approved_at,
        "gates": f"{record.gates_met}/{record.gates_total}",
        "release_readiness": record.release_readiness_status,
        "acknowledgements": {
            "rawdata_readonly": record.rawdata_readonly_acknowledged,
            "no_clinical_use": record.no_clinical_use_acknowledged,
            "rollback": record.rollback_acknowledged,
            "approval_audit": record.approval_audit_acknowledged,
            "public_endpoint": record.public_endpoint_acknowledged,
            "frontend_execute": record.frontend_execute_acknowledged,
            "spm_dpabi_matlab_disabled": record.spm_dpabi_matlab_disabled_acknowledged,
        },
        "human_approval_statement": record.human_approval_statement[:200] if record.human_approval_statement else "",
        "warnings": record.warnings,
        "errors": record.errors,
    }


def _field_is_set(record: DicomConversionReleaseApprovalRecord, field: str) -> bool:
    """Check if a field is non-empty on the record."""
    value = getattr(record, field, None)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return value
    return bool(value)
