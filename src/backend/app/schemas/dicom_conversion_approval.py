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

    # Phase 4H-2: Rawdata checksum
    rawdata_checksum_snapshot_path: str | None = None
    rawdata_checksum_fingerprint: str | None = None
    rawdata_checksum_confirmed: bool = False
    pre_conversion_checksum_required: bool = True
    post_conversion_checksum_required: bool = True
    checksum_mismatch_policy: str = "block"
    rollback_plan_path: str | None = None
    rollback_plan_confirmed: bool = False
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


# ═══════════════════════════════════════════════════════════════════════
# 5. Phase 4E-0 — Run reservation and plan persistence
# ═══════════════════════════════════════════════════════════════════════

DicomConversionPersistenceStatus = Literal[
    "reserved",
    "blocked",
    "already_exists",
    "invalid",
    "disabled",
    "failed",
]


class DicomConversionRunReservation(BaseModel):
    """A reserved conversion run directory with planned artifact paths."""

    project_id: str = ""
    conversion_run_id: str = ""
    run_dir: str | None = None
    output_root: str | None = None
    approval_record_path: str | None = None
    audit_preview_path: str | None = None
    preflight_snapshot_path: str | None = None
    mapping_snapshot_path: str | None = None
    command_templates_path: str | None = None
    planned_manifest_path: str | None = None
    planned_provenance_path: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    created_at: str | None = None
    overwrite_policy: DicomConversionOverwritePolicy = "fail_if_exists"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionPersistedPlan(BaseModel):
    """A complete persisted conversion plan with all snapshots."""

    project_id: str = ""
    conversion_run_id: str = ""
    approval_record: DicomConversionApprovalRecord = Field(
        default_factory=DicomConversionApprovalRecord
    )
    gate_decision: DicomConversionGateDecision = Field(
        default_factory=DicomConversionGateDecision
    )
    preflight_snapshot: dict[str, Any] = Field(default_factory=dict)
    mappings: list[dict[str, Any]] = Field(default_factory=list)
    command_templates: list[dict[str, Any]] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
    reservation: DicomConversionRunReservation = Field(
        default_factory=DicomConversionRunReservation
    )


class DicomConversionPlanPersistenceResponse(BaseModel):
    """Response from persisting a conversion plan."""

    ok: bool = False
    status: DicomConversionPersistenceStatus = "blocked"
    project_id: str = ""
    conversion_run_id: str | None = None
    reservation: DicomConversionRunReservation | None = None
    gate_decision: DicomConversionGateDecision = Field(
        default_factory=DicomConversionGateDecision
    )
    written_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# 6. Phase 4E-0 — Pure helpers
# ═══════════════════════════════════════════════════════════════════════


def build_conversion_run_id(
    project_id: str,
    mapping_hash: str = "",
    timestamp: str | None = None,
) -> str:
    """Build a deterministic conversion run ID.

    Pure function — no file I/O, no subprocess.
    """
    import hashlib
    from datetime import datetime, timezone

    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    seed = f"{project_id}:{mapping_hash}:{ts}"
    short = hashlib.sha256(seed.encode()).hexdigest()[:12]
    return f"conv-{short}"


def build_conversion_run_paths(
    project_dir: str,
    conversion_run_id: str,
) -> dict[str, str]:
    """Build the planned file paths for a conversion run reservation.

    Pure function — no file I/O, no path creation.
    """
    run_dir = f"{project_dir}/conversion_runs/{conversion_run_id}"
    logs_dir = f"{run_dir}/logs"
    return {
        "run_dir": run_dir,
        "output_root": run_dir,
        "approval_record_path": f"{run_dir}/approval_record.json",
        "audit_preview_path": f"{run_dir}/audit_preview.json",
        "preflight_snapshot_path": f"{run_dir}/preflight_snapshot.json",
        "mapping_snapshot_path": f"{run_dir}/mapping_snapshot.json",
        "command_templates_path": f"{run_dir}/command_templates.json",
        "planned_manifest_path": f"{run_dir}/planned_output_manifest.json",
        "planned_provenance_path": f"{run_dir}/planned_execution_provenance.json",
        "stdout_log_path": f"{logs_dir}/stdout.log",
        "stderr_log_path": f"{logs_dir}/stderr.log",
        "readme_path": f"{run_dir}/README.md",
        # Phase 4H-1 / 4J-0 / 4J-1
        "rawdata_checksum_before_path": f"{run_dir}/rawdata_checksum_before.json",
        "rawdata_checksum_after_path": f"{run_dir}/rawdata_checksum_after.json",
        "rawdata_checksum_comparison_path": f"{run_dir}/rawdata_checksum_comparison.json",
        "rollback_plan_dry_run_path": f"{run_dir}/rollback_plan_dry_run.json",
        "rollback_result_path": f"{run_dir}/rollback_result.json",
        "audit_execution_start_path": f"{run_dir}/audit_execution_start.json",
        "audit_execution_final_path": f"{run_dir}/audit_execution_final.json",
    }


def validate_conversion_run_paths(
    paths: dict[str, str],
    project_dir: str,
    rawdata_dir: str = "",
) -> tuple[bool, list[str]]:
    """Validate that all run paths are under project_dir and not under rawdata.

    Returns ``(ok, issues)``.  Pure function — no file I/O.
    """
    issues: list[str] = []
    for key, path in paths.items():
        if key == "output_root":
            continue
        if path and not path.startswith(project_dir):
            issues.append(f"{key}: {path} is not under project_dir")
        if path and rawdata_dir and path.startswith(rawdata_dir):
            issues.append(f"{key}: {path} is under rawdata_dir")
    return len(issues) == 0, issues


def is_reserved_run_directory_safe(
    reservation: DicomConversionRunReservation,
    project_dir: str,
    rawdata_dir: str = "",
) -> bool:
    """Return True if all reserved paths are safe."""
    paths = {
        "run_dir": reservation.run_dir or "",
        "approval_record_path": reservation.approval_record_path or "",
        "output_root": reservation.output_root or "",
    }
    ok, _ = validate_conversion_run_paths(paths, project_dir, rawdata_dir)
    return ok


def summarize_persisted_conversion_plan(
    plan: DicomConversionPersistedPlan,
) -> dict[str, Any]:
    """Aggregate summary of a persisted conversion plan."""
    return {
        "project_id": plan.project_id,
        "conversion_run_id": plan.conversion_run_id,
        "approval_status": plan.approval_record.status,
        "gate_status": plan.gate_decision.status,
        "mapping_count": len(plan.mappings),
        "template_count": len(plan.command_templates),
        "run_dir": plan.reservation.run_dir,
    }


# ═══════════════════════════════════════════════════════════════════════
# Phase 4J-1 — Audit execution integration
# ═══════════════════════════════════════════════════════════════════════

DicomConversionAuditExecutionState = Literal[
    "planned",
    "preflight_checked",
    "execution_started",
    "execution_succeeded",
    "execution_failed",
    "rollback_planned",
    "rollback_completed",
    "blocked",
]


class DicomConversionExecutionAuditUpdate(BaseModel):
    """Audit state tracking for a conversion execution."""

    project_id: str = ""
    conversion_run_id: str = ""
    audit_state: DicomConversionAuditExecutionState = "planned"
    started_at: str | None = None
    finished_at: str | None = None
    approval_record_path: str | None = None
    audit_record_path: str | None = None
    preflight_snapshot_path: str | None = None
    mapping_snapshot_path: str | None = None
    command_templates_path: str | None = None
    checksum_before_path: str | None = None
    checksum_after_path: str | None = None
    checksum_comparison_path: str | None = None
    rollback_plan_path: str | None = None
    rollback_result_path: str | None = None
    output_manifest_path: str | None = None
    execution_provenance_path: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    dcm2niix_version: str | None = None
    dcm2niix_expected_version: str | None = None
    dcm2niix_executable_path: str | None = None
    dcm2niix_binary_sha256: str | None = None
    dcm2niix_detection_strategy: str | None = None
    return_code: int | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def validate_execution_approval_package(
    approval_path: str,
    audit_path: str,
    checksum_path: str,
    rollback_path: str,
) -> tuple[bool, list[str]]:
    """Check that all required approval/audit files exist."""
    from pathlib import Path as _Path
    issues: list[str] = []
    for label, p in [
        ("approval", approval_path),
        ("audit", audit_path),
        ("checksum", checksum_path),
        ("rollback", rollback_path),
    ]:
        if not p or not _Path(p).exists():
            issues.append(f"Missing {label}: {p}")
    return len(issues) == 0, issues


def build_execution_audit_update(
    project_id: str,
    conversion_run_id: str,
    output_root: str,
    state: DicomConversionAuditExecutionState = "execution_started",
    **kwargs: Any,
) -> DicomConversionExecutionAuditUpdate:
    """Build an audit update with the given state and metadata.

    Default paths are set only when the caller does not override them via kwargs.
    """
    defaults: dict[str, Any] = {
        "approval_record_path": f"{output_root}/approval_record.json",
        "audit_record_path": f"{output_root}/audit_preview.json",
        "checksum_before_path": f"{output_root}/rawdata_checksum_before.json",
        "rollback_plan_path": f"{output_root}/rollback_plan_dry_run.json",
        "output_manifest_path": f"{output_root}/output_manifest.json",
        "execution_provenance_path": f"{output_root}/execution_provenance.json",
    }
    # Let kwargs override defaults
    merged = {**defaults, **kwargs}
    return DicomConversionExecutionAuditUpdate(
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        audit_state=state,
        **merged,
    )


def is_audit_ready_for_execution(
    audit: DicomConversionExecutionAuditUpdate,
) -> bool:
    """Return True if the audit state allows execution."""
    return audit.audit_state in {"planned", "preflight_checked"}


def is_audit_finalized(
    audit: DicomConversionExecutionAuditUpdate,
) -> bool:
    """Return True if the audit has reached a terminal state."""
    return audit.audit_state in {
        "execution_succeeded", "execution_failed", "rollback_completed", "blocked",
    }
