"""DICOM Conversion Approval Schema — Phase 4D.

Defines approval statuses, overwrite policies, approval and audit record
models, approval checklist items, gate decision model, and pure helper
functions for the DICOM conversion approval gate.

Schema-only module.  No subprocess.  No file writes.  No external tool
imports.  No real conversion execution is enabled.

Reference:
  docs/DICOM_CONVERSION_APPROVAL_GATE_DESIGN.md
  docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# 1. Literal type aliases
# ═══════════════════════════════════════════════════════════════════════

DicomConversionApprovalStatus = Literal[
    "missing",
    "incomplete",
    "ready_for_review",
    "approved",
    "rejected",
    "expired",
]

DicomConversionOverwritePolicy = Literal[
    "fail_if_exists",
    "overwrite_derivatives_only",
    "write_new_run_directory",
]

DicomConversionGateDecisionStatus = Literal[
    "blocked",
    "incomplete",
    "ready",
    "approved",
    "rejected",
]

# ═══════════════════════════════════════════════════════════════════════
# 2. Required approval preconditions (17 items)
# ═══════════════════════════════════════════════════════════════════════

_REQUIRED_APPROVAL_FIELDS: frozenset[str] = frozenset({
    "approved",
    "approved_by",
    "mappings_reviewed",
    "output_root_confirmed",
    "output_root_under_project",
    "output_root_not_rawdata",
    "rawdata_read_only_confirmed",
    "command_templates_reviewed",
    "no_shell_string_confirmed",
    "dcm2niix_availability_confirmed",
    "env_flags_confirmed",
    "overwrite_policy",
    "rollback_policy_acknowledged",
    "clinical_use_prohibited_acknowledged",
    "external_tool_acknowledgement",
    "risk_acknowledgement",
    "confirm_execution",
})

# ═══════════════════════════════════════════════════════════════════════
# 3. Pydantic models
# ═══════════════════════════════════════════════════════════════════════


class DicomConversionApprovalRecord(BaseModel):
    """Approval record for DICOM-to-NIfTI conversion.

    All 17 required fields must be satisfied for the record to be
    considered complete.  Missing any field → status = "incomplete".
    """

    approval_id: str = ""
    project_id: str = ""
    reviewed_plan_id: str | None = None
    status: DicomConversionApprovalStatus = "missing"

    # Operator identity
    approved: bool = False
    approved_by: str | None = None
    approved_at: str | None = None

    # Mapping review
    mapping_ids: list[str] = Field(default_factory=list)
    mappings_reviewed: bool = False

    # Output safety
    output_root: str | None = None
    output_root_confirmed: bool = False
    output_root_under_project: bool = False
    output_root_not_rawdata: bool = False
    overwrite_policy: DicomConversionOverwritePolicy = "fail_if_exists"

    # Safety acknowledgements
    rawdata_read_only_confirmed: bool = False
    command_templates_reviewed: bool = False
    no_shell_string_confirmed: bool = False
    dcm2niix_availability_confirmed: bool = False
    dcm2niix_version: str | None = None
    env_flags_confirmed: bool = False
    missing_env_flags: list[str] = Field(default_factory=list)

    # Risk and policy
    rollback_policy_acknowledged: bool = False
    clinical_use_prohibited_acknowledged: bool = False
    external_tool_acknowledgement: bool = False
    risk_acknowledgement: bool = False

    # Execution gate
    confirm_execution: bool = False

    # Metadata
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionAuditRecord(BaseModel):
    """Pre-execution audit record for DICOM conversion.

    Must be persisted BEFORE any dcm2niix invocation.
    """

    audit_id: str = ""
    approval_id: str = ""
    project_id: str = ""
    reviewed_plan_id: str | None = None
    preflight_hash: str | None = None
    command_template_hashes: list[str] = Field(default_factory=list)
    input_dicom_checksum: str | None = None
    output_root: str | None = None
    env_fingerprint: str | None = None
    dcm2niix_version: str | None = None
    persisted_at: str | None = None

    # Post-execution (populated after conversion)
    output_manifest_sha256: str | None = None
    provenance_sha256: str | None = None
    execution_return_code: int | None = None
    rawdata_unchanged_confirmed: bool | None = None


class DicomConversionApprovalChecklist(BaseModel):
    """Structured checklist of all approval preconditions."""

    items: list[dict[str, Any]] = Field(default_factory=list)
    total_count: int = 17
    checked_count: int = 0
    all_checked: bool = False


class DicomConversionGateDecision(BaseModel):
    """Result of evaluating the DICOM conversion approval gate."""

    ok: bool = False
    status: DicomConversionGateDecisionStatus = "blocked"
    approval_complete: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ready_for_execution: bool = False


# ═══════════════════════════════════════════════════════════════════════
# 4. Pure helper functions
# ═══════════════════════════════════════════════════════════════════════


def build_conversion_approval_checklist(
    record: DicomConversionApprovalRecord,
) -> DicomConversionApprovalChecklist:
    """Build a structured checklist from an approval record.

    Pure function — no file I/O, no subprocess.
    """
    field_labels: dict[str, str] = {
        "approved": "Approved flag set",
        "approved_by": "Approved-by name provided",
        "mappings_reviewed": "Conversion mappings reviewed",
        "output_root_confirmed": "Output root confirmed",
        "output_root_under_project": "Output root under project directory",
        "output_root_not_rawdata": "Output root not inside rawdata",
        "rawdata_read_only_confirmed": "Rawdata read-only acknowledged",
        "command_templates_reviewed": "Command templates reviewed",
        "no_shell_string_confirmed": "No shell string acknowledged",
        "dcm2niix_availability_confirmed": "dcm2niix availability confirmed",
        "env_flags_confirmed": "Environment flags confirmed",
        "overwrite_policy": "Overwrite policy set",
        "rollback_policy_acknowledged": "Rollback policy acknowledged",
        "clinical_use_prohibited_acknowledged": "Clinical use prohibited acknowledged",
        "external_tool_acknowledgement": "External tool acknowledged",
        "risk_acknowledgement": "Risk acknowledged",
        "confirm_execution": "Execution confirmed",
    }

    items: list[dict[str, Any]] = []
    checked = 0
    for field in sorted(_REQUIRED_APPROVAL_FIELDS):
        value = getattr(record, field, None)
        is_checked = bool(value)
        if isinstance(value, str):
            is_checked = bool(value.strip())
        if is_checked:
            checked += 1
        items.append({
            "field": field,
            "label": field_labels.get(field, field),
            "checked": is_checked,
        })

    return DicomConversionApprovalChecklist(
        items=items,
        total_count=len(_REQUIRED_APPROVAL_FIELDS),
        checked_count=checked,
        all_checked=checked == len(_REQUIRED_APPROVAL_FIELDS),
    )


def is_conversion_approval_complete(
    record: DicomConversionApprovalRecord,
) -> bool:
    """Return True if all required approval fields are satisfied."""
    for field in _REQUIRED_APPROVAL_FIELDS:
        value = getattr(record, field, None)
        if not value:
            return False
        if isinstance(value, str) and not value.strip():
            return False
    return True


def evaluate_conversion_approval_gate(
    record: DicomConversionApprovalRecord,
    preflight_ok: bool = False,
) -> DicomConversionGateDecision:
    """Evaluate whether the approval gate allows conversion to proceed.

    Checks all 17 required fields, validates output root safety
    invariants, and confirms preflight readiness.

    Pure function — no subprocess, no file I/O, no dcm2niix call.
    """
    missing: list[str] = []
    blocking: list[str] = []

    # Check all required fields
    for field in sorted(_REQUIRED_APPROVAL_FIELDS):
        value = getattr(record, field, None)
        is_set = bool(value)
        if isinstance(value, str):
            is_set = bool(value.strip())
        if not is_set:
            missing.append(field)

    # Output root safety invariants
    if record.output_root_confirmed:
        if not record.output_root_under_project:
            blocking.append(
                "Output root is not confirmed to be under the project directory."
            )
        if not record.output_root_not_rawdata:
            blocking.append(
                "Output root is not confirmed to be outside the rawdata directory."
            )

    # Overwrite policy
    if not record.overwrite_policy:
        blocking.append("Overwrite policy is not set.")

    # Preflight must be OK
    if not preflight_ok:
        blocking.append("Conversion preflight did not pass.")

    # Determine status
    if not record.approved:
        status: DicomConversionGateDecisionStatus = "rejected"
    elif missing and not blocking:
        status = "incomplete"
    elif blocking:
        status = "blocked"
    elif missing:
        status = "incomplete"
    else:
        status = "approved"

    return DicomConversionGateDecision(
        ok=(status == "approved"),
        status=status,
        approval_complete=len(missing) == 0,
        missing_fields=missing,
        blocking_issues=blocking,
        ready_for_execution=(status == "approved"),
    )


def requires_new_run_directory(
    policy: DicomConversionOverwritePolicy,
) -> bool:
    """Return True if the policy requires a fresh run directory."""
    return policy == "write_new_run_directory"


def is_safe_overwrite_policy(
    policy: DicomConversionOverwritePolicy,
) -> bool:
    """Return True if *policy* is considered safe."""
    return policy in {"fail_if_exists", "write_new_run_directory"}
