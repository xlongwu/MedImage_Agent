"""DICOM Conversion Public Execution Schema — Phase 4L-2.

Defines Pydantic models, Literal types, and pure helper functions for the
public DICOM-to-NIfTI conversion execute endpoint.

**Phase 4L-2: endpoint is implemented behind env flags.**  All preconditions
must pass before real dcm2niix execution is reached.  No frontend button exists.

Reference:
  docs/DICOM_PUBLIC_EXECUTE_ENDPOINT_DESIGN.md
  docs/DICOM_CONVERSION_RELEASE_HARDENING.md
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── 1. Literal type aliases ────────────────────────────────────────────────

DicomConversionPublicExecutionStatus = Literal[
    "disabled",
    "blocked",
    "ready",
    "succeeded",
    "partial",
    "warning",
    "failed",
    "safety_violation",
]

DicomConversionPublicExecutionDecision = Literal[
    "blocked",
    "proceed",
    "design_only_allowed",
]
"""

Phase 4L-2 decisions:
- ``"blocked"`` — one or more preconditions failed; execution is NOT permitted.
- ``"proceed"`` — all preconditions met; execution may proceed.
"""


# backcompat alias
DicPublicExecDecision = DicomConversionPublicExecutionDecision
"""Short alias for ``DicomConversionPublicExecutionDecision``."""


# ── 2. Pydantic models ────────────────────────────────────────────────────


class DicomConversionPublicExecutionRequest(BaseModel):
    """Request submitted by an operator to execute public DICOM conversion.

    All ``confirm_*`` fields must be ``True`` — missing any one blocks execution.
    """

    # Required identifiers
    conversion_run_id: str = ""
    release_approval_id: str = ""

    # Required operator confirmations (all must be True)
    confirm_user_data_conversion: bool = False
    confirm_rawdata_readonly: bool = False
    confirm_research_use_only: bool = False
    confirm_no_clinical_use: bool = False
    confirm_rollback_available: bool = False
    confirm_disk_space_checked: bool = False
    confirm_public_execution_risk: bool = False

    # Request metadata
    requested_by: str = ""
    reason: str = ""

    # Execution options
    dry_run_first: bool = True
    rollback_mode_on_failure: str = "quarantine"


class DicomConversionPublicExecutionSafetyFlags(BaseModel):
    """Safety flags returned with every conversion execute response."""

    conversion_disabled_by_default: bool = True
    env_flags_missing: bool = True
    public_execution_allowed: bool = False
    release_approval_obtained: bool = False
    release_readiness_ready: bool = False
    gates_32_of_32: bool = False
    approval_audit_package_present: bool = False
    rawdata_checksum_before_exists: bool = False
    rollback_plan_exists: bool = False
    disk_space_passed: bool = False
    output_root_safe: bool = False
    rawdata_read_only: bool = True
    spm_dpabi_matlab_disabled: bool = True
    full_preprocessing_disabled: bool = True
    human_release_approval_required: bool = True
    no_shell_execution: bool = True


class DicomConversionPublicExecutionResponse(BaseModel):
    """Response returned after public DICOM conversion execution."""

    ok: bool = False
    status: DicomConversionPublicExecutionStatus = "disabled"
    project_id: str = ""
    conversion_run_id: str = ""
    execution_id: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    output_root: str = ""
    output_manifest_path: str | None = None
    execution_provenance_path: str | None = None
    audit_execution_start_path: str | None = None
    audit_execution_final_path: str | None = None
    checksum_before_path: str | None = None
    checksum_after_path: str | None = None
    checksum_comparison_path: str | None = None
    checksum_verified: bool = False
    rollback_plan_path: str | None = None
    rollback_result_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    safety_flags: DicomConversionPublicExecutionSafetyFlags = Field(
        default_factory=DicomConversionPublicExecutionSafetyFlags
    )


class DicomConversionPublicExecutionPreconditions(BaseModel):
    """Snapshot of all preconditions for public conversion execution."""

    # Env flags
    env_allow_user_data_conversion: bool = False
    env_enable_dicom_conversion: bool = False
    env_enable_reviewed_execution: bool = False
    env_enable_real_preprocessing: bool = False
    env_allow_public_dicom_conversion_endpoint: bool = False

    # Release approval
    release_approval_exists: bool = False
    release_approval_status: str = "missing"
    release_approval_not_expired: bool = False

    # Release readiness
    release_readiness_status: str = "unknown"
    release_readiness_ready: bool = False

    # Gates
    gates_met: int = 0
    gates_total: int = 32
    gates_all_met: bool = False

    # Approval/audit package
    approval_audit_package_present: bool = False

    # Checksum
    rawdata_checksum_before_exists: bool = False

    # Rollback
    rollback_plan_exists: bool = False

    # Disk space
    disk_space_passed: bool = False

    # Safety invariants
    output_root_safe: bool = False
    spm_dpabi_matlab_disabled: bool = True
    full_preprocessing_disabled: bool = True
    rawdata_read_only: bool = True

    # Blockers
    missing: list[str] = Field(default_factory=list)
    blocking: list[str] = Field(default_factory=list)


class DicomConversionPublicExecutionGateDecision(BaseModel):
    """Result of evaluating all public execution preconditions."""

    ok: bool = False
    decision: DicomConversionPublicExecutionDecision = "blocked"
    preconditions: DicomConversionPublicExecutionPreconditions = Field(
        default_factory=DicomConversionPublicExecutionPreconditions
    )
    missing_confirmations: list[str] = Field(default_factory=list)
    missing_env_flags: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: DicomConversionPublicExecutionSafetyFlags = Field(
        default_factory=DicomConversionPublicExecutionSafetyFlags
    )


# ── 3. Constants ──────────────────────────────────────────────────────────

_REQUIRED_CONFIRMATION_FIELDS: frozenset[str] = frozenset({
    "confirm_user_data_conversion",
    "confirm_rawdata_readonly",
    "confirm_research_use_only",
    "confirm_no_clinical_use",
    "confirm_rollback_available",
    "confirm_disk_space_checked",
    "confirm_public_execution_risk",
})

_REQUIRED_ENV_FLAGS: frozenset[str] = frozenset({
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION",
    "MEDIMAGE_ENABLE_DICOM_CONVERSION",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
    "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
    "MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT",
})

_CONSISTENCY_ENV_FLAGS: frozenset[str] = frozenset({
    "MEDIMAGE_MATLAB_ENABLED",
    "MEDIMAGE_SPM_SMOKE_ENABLED",
})

_CONFIRMATION_LABELS: dict[str, str] = {
    "confirm_user_data_conversion": "User data conversion confirmation",
    "confirm_rawdata_readonly": "Rawdata read-only acknowledgement",
    "confirm_research_use_only": "Research-use-only acknowledgement",
    "confirm_no_clinical_use": "No-clinical-use acknowledgement",
    "confirm_rollback_available": "Rollback availability acknowledgement",
    "confirm_disk_space_checked": "Disk space check acknowledgement",
    "confirm_public_execution_risk": "Public execution risk acknowledgement",
}

_RELEASE_APPROVAL_VALID_STATUSES: frozenset[str] = frozenset({"approved"})
_APPROVAL_EXPIRY_DAYS: int = 180
_RELEASE_READINESS_EXECUTABLE_STATUSES: frozenset[str] = frozenset({
    "ready_for_human_release_review",
    "warning",
})


# ── 4. Pure helper functions ──────────────────────────────────────────────


def validate_public_execution_request_acknowledgements(
    request: DicomConversionPublicExecutionRequest,
) -> tuple[bool, list[str]]:
    """Validate that all operator confirmations are True.

    Returns ``(ok, missing_labels)``.
    Pure function — no file I/O, no subprocess.
    """
    missing: list[str] = []
    for field in _REQUIRED_CONFIRMATION_FIELDS:
        value = getattr(request, field, False)
        if not value:
            missing.append(_CONFIRMATION_LABELS.get(field, field))
    return len(missing) == 0, missing


def validate_public_execution_env_flags(
    env: dict[str, str] | None = None,
) -> tuple[bool, list[str]]:
    """Check that all required env flags are set to ``"1"``.

    Returns ``(ok, missing_flags)``.
    Pure function — no file I/O, no subprocess, no os.environ access.
    """
    env = env or {}
    missing = sorted(f for f in _REQUIRED_ENV_FLAGS if env.get(f) != "1")
    return len(missing) == 0, missing


def is_release_approval_acceptable(
    status: str = "missing",
    approved_at: str | None = None,
) -> tuple[bool, list[str]]:
    """Check whether a release approval record status is acceptable.

    Pure function — no file I/O, no subprocess.
    """
    issues: list[str] = []
    if status not in _RELEASE_APPROVAL_VALID_STATUSES:
        issues.append(
            f"Release approval status is '{status}', "
            f"must be one of: {_RELEASE_APPROVAL_VALID_STATUSES}."
        )
    # Expiry check is best-effort without datetime parsing
    # The actual expiry check is done in the service layer
    return len(issues) == 0, issues


def evaluate_public_execution_preconditions(
    *,
    env_flags_ok: bool = False,
    missing_env_flags: list[str] | None = None,
    request_confirmations_ok: bool = False,
    missing_confirmations: list[str] | None = None,
    release_approval_status: str = "missing",
    release_approval_not_expired: bool = False,
    release_readiness_status: str = "unknown",
    gates_met: int = 0,
    gates_total: int = 32,
    approval_audit_package_present: bool = False,
    rawdata_checksum_before_exists: bool = False,
    rollback_plan_exists: bool = False,
    disk_space_passed: bool = False,
    output_root_safe: bool = False,
    spm_dpabi_matlab_disabled: bool = True,
    full_preprocessing_disabled: bool = True,
) -> DicomConversionPublicExecutionGateDecision:
    """Evaluate all preconditions for public conversion execution.

    Returns a ``DicomConversionPublicExecutionGateDecision`` indicating
    whether the endpoint should allow execution or block it.

    Pure function — no file I/O, no subprocess, no dcm2niix.
    In Phase 4L-1, the decision is always ``"design_only_allowed"``
    because no public endpoint exists.
    """
    missing: list[str] = []
    blocking: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    missing = list(missing_confirmations or [])
    missing_env = list(missing_env_flags or [])

    # ── Env flags ──
    if not env_flags_ok:
        blocking.append(
            f"Required env flags missing: {', '.join(missing_env)}. "
            f"All required flags: {', '.join(sorted(_REQUIRED_ENV_FLAGS))}."
        )

    # ── Operator confirmations ──
    if not request_confirmations_ok:
        blocking.append(
            f"Operator confirmations missing: {', '.join(missing)}."
        )

    # ── Release approval ──
    if release_approval_status not in _RELEASE_APPROVAL_VALID_STATUSES:
        blocking.append(
            f"Release approval status is '{release_approval_status}', "
            f"not an approved status."
        )
    if not release_approval_not_expired:
        blocking.append("Release approval is expired or has no valid timestamp.")

    # ── Release readiness ──
    if release_readiness_status not in _RELEASE_READINESS_EXECUTABLE_STATUSES:
        blocking.append(
            f"Release readiness is '{release_readiness_status}', "
            f"must be one of {sorted(_RELEASE_READINESS_EXECUTABLE_STATUSES)}."
        )

    # ── Gates ──
    all_gates = gates_met >= gates_total
    if not all_gates:
        blocking.append(
            f"Not all safety gates met: {gates_met}/{gates_total}."
        )

    # ── Approval/audit package ──
    if not approval_audit_package_present:
        blocking.append("Approval/audit package is not present.")

    # ── Checksum ──
    if not rawdata_checksum_before_exists:
        blocking.append("Rawdata checksum-before snapshot does not exist.")

    # ── Rollback ──
    if not rollback_plan_exists:
        blocking.append("Rollback plan does not exist.")

    # ── Disk space ──
    if not disk_space_passed:
        blocking.append("Disk space check failed.")

    # ── Output root safety ──
    if not output_root_safe:
        blocking.append("Output root is not safe (under rawdata or outside project).")

    # ── Safety invariants ──
    if not spm_dpabi_matlab_disabled:
        warnings.append("SPM/DPABI/MATLAB execution appears enabled — should be disabled.")

    if not full_preprocessing_disabled:
        warnings.append("Full preprocessing appears enabled — should be disabled.")

    # ── Determine decision ──
    all_ok = (
        env_flags_ok
        and request_confirmations_ok
        and release_approval_status in _RELEASE_APPROVAL_VALID_STATUSES
        and release_approval_not_expired
        and release_readiness_status in _RELEASE_READINESS_EXECUTABLE_STATUSES
        and all_gates
        and approval_audit_package_present
        and rawdata_checksum_before_exists
        and rollback_plan_exists
        and disk_space_passed
        and output_root_safe
    )

    # In Phase 4L-2, the endpoint exists behind env flags.  Decision is
    # "proceed" when ALL preconditions are met, "blocked" otherwise.
    decision: DicomConversionPublicExecutionDecision = (
        "proceed" if all_ok else "blocked"
    )

    preconditions = DicomConversionPublicExecutionPreconditions(
        env_allow_user_data_conversion=env_flags_ok,
        release_approval_status=release_approval_status,
        release_approval_not_expired=release_approval_not_expired,
        release_readiness_status=release_readiness_status,
        release_readiness_ready=(
            release_readiness_status in _RELEASE_READINESS_EXECUTABLE_STATUSES
        ),
        gates_met=gates_met,
        gates_total=gates_total,
        gates_all_met=all_gates,
        approval_audit_package_present=approval_audit_package_present,
        rawdata_checksum_before_exists=rawdata_checksum_before_exists,
        rollback_plan_exists=rollback_plan_exists,
        disk_space_passed=disk_space_passed,
        output_root_safe=output_root_safe,
        spm_dpabi_matlab_disabled=spm_dpabi_matlab_disabled,
        full_preprocessing_disabled=full_preprocessing_disabled,
        rawdata_read_only=True,
        missing=missing,
        blocking=blocking,
    )

    return DicomConversionPublicExecutionGateDecision(
        ok=all_ok,
        decision=decision,
        preconditions=preconditions,
        missing_confirmations=missing,
        missing_env_flags=missing_env,
        blocking_issues=blocking,
        warnings=warnings,
        errors=errors,
        safety_flags=DicomConversionPublicExecutionSafetyFlags(
            conversion_disabled_by_default=not all_ok,
            env_flags_missing=not env_flags_ok,
            public_execution_allowed=all_ok,  # Phase 4L-2: reflects actual gates
            release_approval_obtained=(
                release_approval_status in _RELEASE_APPROVAL_VALID_STATUSES
            ),
            release_readiness_ready=(
                release_readiness_status in _RELEASE_READINESS_EXECUTABLE_STATUSES
            ),
            gates_32_of_32=all_gates,
            approval_audit_package_present=approval_audit_package_present,
            rawdata_checksum_before_exists=rawdata_checksum_before_exists,
            rollback_plan_exists=rollback_plan_exists,
            disk_space_passed=disk_space_passed,
            output_root_safe=output_root_safe,
            rawdata_read_only=True,
            spm_dpabi_matlab_disabled=spm_dpabi_matlab_disabled,
            full_preprocessing_disabled=full_preprocessing_disabled,
            human_release_approval_required=True,
            no_shell_execution=True,
        ),
    )


def is_public_execution_design_only() -> bool:
    """Return False — public execution endpoint is implemented in Phase 4L-2.

    The endpoint is behind env flags and all gating preconditions.
    Returns False to reflect Phase 4L-2 state.

    Pure function — no file I/O, no subprocess.
    """
    return False


def summarize_public_execution_blockers(
    decision: DicomConversionPublicExecutionGateDecision,
) -> dict[str, Any]:
    """Summarize blockers from a public execution gate decision.

    Pure function — no file I/O, no subprocess.
    """
    return {
        "ok": decision.ok,
        "decision": decision.decision,
        "blocking_count": len(decision.blocking_issues),
        "warning_count": len(decision.warnings),
        "error_count": len(decision.errors),
        "missing_confirmations": decision.missing_confirmations,
        "missing_env_flags": decision.missing_env_flags,
        "blockers": decision.blocking_issues,
        "warnings": decision.warnings,
        "gates": f"{decision.preconditions.gates_met}/{decision.preconditions.gates_total}",
        "release_approval_status": decision.preconditions.release_approval_status,
        "release_readiness": decision.preconditions.release_readiness_status,
        "public_execution_allowed": decision.safety_flags.public_execution_allowed,
    }


__all__ = [
    "DicomConversionPublicExecutionRequest",
    "DicomConversionPublicExecutionResponse",
    "DicomConversionPublicExecutionSafetyFlags",
    "DicomConversionPublicExecutionPreconditions",
    "DicomConversionPublicExecutionGateDecision",
    "validate_public_execution_request_acknowledgements",
    "validate_public_execution_env_flags",
    "is_release_approval_acceptable",
    "evaluate_public_execution_preconditions",
    "is_public_execution_design_only",
    "summarize_public_execution_blockers",
]
