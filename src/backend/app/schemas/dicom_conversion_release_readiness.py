"""DICOM Conversion Release Readiness Schema — Phase 4K-0.

Defines release readiness statuses, disk-space check models, runtime
policy models, release readiness report models, and pure helper functions
for evaluating whether the DICOM conversion implementation is ready for
human release review.

Schema-only module.  No subprocess.  No file writes.  No dcm2niix.
No rawdata modification.  No SPM/DPABI/MATLAB.

Reference:
  docs/DICOM_CONVERSION_RELEASE_HARDENING.md
  docs/DICOM_USER_DATA_CONVERSION_GO_NO_GO_REVIEW.md
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# 1. Literal type aliases
# ═══════════════════════════════════════════════════════════════════════

DicomConversionReleaseReadinessStatus = Literal[
    "blocked",
    "warning",
    "ready_internal",
    "ready_for_human_release_review",
]


# ═══════════════════════════════════════════════════════════════════════
# 2. Pydantic models
# ═══════════════════════════════════════════════════════════════════════


class DicomConversionDiskSpaceCheck(BaseModel):
    """Disk space availability check for conversion output root."""

    output_root: str = ""
    free_bytes: int = 0
    estimated_required_bytes: int = 0
    required_multiplier: float = 1.5
    ok: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionRuntimePolicy(BaseModel):
    """Runtime safety policy for conversion execution."""

    timeout_seconds: int = 1800
    cancellation_supported: bool = False
    resume_supported: bool = False
    retry_supported: bool = False
    max_subjects_per_run: int = 50
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionReleaseReadinessReport(BaseModel):
    """Complete release readiness report for a conversion run."""

    ok: bool = False
    status: DicomConversionReleaseReadinessStatus = "blocked"
    project_id: str = ""
    conversion_run_id: str = ""
    gate_status: str = "unknown"
    gates_met: int = 0
    gates_total: int = 32
    disk_space: DicomConversionDiskSpaceCheck = Field(
        default_factory=DicomConversionDiskSpaceCheck
    )
    runtime_policy: DicomConversionRuntimePolicy = Field(
        default_factory=DicomConversionRuntimePolicy
    )
    rollback_ready: bool = False
    approval_audit_ready: bool = False
    public_endpoint_enabled: bool = False
    frontend_execute_enabled: bool = False
    spm_dpabi_matlab_enabled: bool = False
    full_preprocessing_enabled: bool = False
    human_release_approval_required: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# 3. Pure helper functions
# ═══════════════════════════════════════════════════════════════════════

_DEFAULT_DISK_SAFETY_MULTIPLIER: float = 1.5
_DEFAULT_TIMEOUT_SECONDS: int = 1800
_DEFAULT_MAX_SUBJECTS: int = 50


def evaluate_disk_space_check(
    output_root: str = "",
    estimated_required_bytes: int = 0,
    *,
    free_bytes: int | None = None,
    multiplier: float = _DEFAULT_DISK_SAFETY_MULTIPLIER,
) -> DicomConversionDiskSpaceCheck:
    """Evaluate whether disk space is sufficient for conversion.

    Pure function — no file I/O, no subprocess.
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not output_root:
        return DicomConversionDiskSpaceCheck(
            output_root=output_root,
            free_bytes=0,
            estimated_required_bytes=estimated_required_bytes,
            required_multiplier=multiplier,
            ok=False,
            errors=["Output root not specified."],
        )

    if free_bytes is None:
        return DicomConversionDiskSpaceCheck(
            output_root=output_root,
            free_bytes=0,
            estimated_required_bytes=estimated_required_bytes,
            required_multiplier=multiplier,
            ok=False,
            warnings=["Free disk space could not be determined."],
        )

    required = int(estimated_required_bytes * multiplier)
    ok = free_bytes >= required

    if not ok:
        errors.append(
            f"Insufficient disk space: {free_bytes} bytes free, "
            f"{required} bytes required (estimated={estimated_required_bytes}, "
            f"multiplier={multiplier})."
        )

    return DicomConversionDiskSpaceCheck(
        output_root=output_root,
        free_bytes=free_bytes,
        estimated_required_bytes=estimated_required_bytes,
        required_multiplier=multiplier,
        ok=ok,
        warnings=warnings,
        errors=errors,
    )


def evaluate_runtime_policy(
    *,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    cancellation_supported: bool = False,
    resume_supported: bool = False,
    retry_supported: bool = False,
    max_subjects_per_run: int = _DEFAULT_MAX_SUBJECTS,
) -> DicomConversionRuntimePolicy:
    """Evaluate runtime safety policy.

    Pure function — no file I/O, no subprocess.
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not cancellation_supported:
        warnings.append("Cancellation is not supported — long-running conversions cannot be stopped.")
    if not resume_supported:
        warnings.append("Resume is not supported — interrupted conversions must be restarted.")
    if not retry_supported:
        warnings.append("Retry is not supported — failed conversions require a fresh run.")

    return DicomConversionRuntimePolicy(
        timeout_seconds=timeout_seconds,
        cancellation_supported=cancellation_supported,
        resume_supported=resume_supported,
        retry_supported=retry_supported,
        max_subjects_per_run=max_subjects_per_run,
        warnings=warnings,
        errors=errors,
    )


def evaluate_release_readiness(
    *,
    gates_met: int = 0,
    gates_total: int = 32,
    gate_status: str = "unknown",
    disk_space_ok: bool = False,
    rollback_ready: bool = False,
    approval_audit_ready: bool = False,
    public_endpoint_enabled: bool = False,
    frontend_execute_enabled: bool = False,
    spm_dpabi_matlab_enabled: bool = False,
    full_preprocessing_enabled: bool = False,
    cancellation_supported: bool = False,
    resume_supported: bool = False,
    runtime_warnings: list[str] | None = None,
    disk_warnings: list[str] | None = None,
    disk_errors: list[str] | None = None,
    extra_blockers: list[str] | None = None,
) -> DicomConversionReleaseReadinessReport:
    """Evaluate overall release readiness.

    Returns blocked if any safety invariant is violated.
    Returns warning if non-critical features are missing.
    Returns ready_for_human_release_review if all gates met and no blockers.

    Pure function — no file I/O, no subprocess, no dcm2niix.
    """
    warnings: list[str] = list(runtime_warnings or [])
    errors: list[str] = []
    blocking: list[str] = list(extra_blockers or [])

    # ── Critical blockers ──
    all_gates_met = gates_met >= gates_total

    if not all_gates_met:
        blocking.append(
            f"Not all safety gates met: {gates_met}/{gates_total}. "
            f"Gate status: {gate_status}."
        )

    if public_endpoint_enabled:
        blocking.append(
            "Public /conversion/execute endpoint is enabled — must remain "
            "disabled until human release approval."
        )

    if frontend_execute_enabled:
        blocking.append(
            "Frontend execute button is enabled — must remain hidden "
            "until human release approval."
        )

    if spm_dpabi_matlab_enabled:
        blocking.append(
            "SPM/DPABI/MATLAB execution is enabled — must remain disabled."
        )

    if full_preprocessing_enabled:
        blocking.append(
            "Full preprocessing is enabled — must remain disabled."
        )

    # ── Non-critical warnings ──
    if not rollback_ready:
        warnings.append("Rollback is not ready.")

    if not approval_audit_ready:
        warnings.append("Approval/audit execution integration is not ready.")

    if not cancellation_supported:
        warnings.append("Cancellation is not supported.")

    if not resume_supported:
        warnings.append("Resume is not supported.")

    if not disk_space_ok:
        for e in (disk_errors or []):
            blocking.append(f"Disk space: {e}")
        for w in (disk_warnings or []):
            warnings.append(f"Disk space: {w}")

    # ── Determine status ──
    if blocking:
        status: DicomConversionReleaseReadinessStatus = "blocked"
    elif warnings:
        status = "warning"
    elif all_gates_met:
        status = "ready_for_human_release_review"
    else:
        status = "ready_internal"

    return DicomConversionReleaseReadinessReport(
        ok=len(blocking) == 0 and len(errors) == 0,
        status=status,
        gate_status=gate_status,
        gates_met=gates_met,
        gates_total=gates_total,
        disk_space=DicomConversionDiskSpaceCheck(ok=disk_space_ok),
        runtime_policy=DicomConversionRuntimePolicy(
            cancellation_supported=cancellation_supported,
            resume_supported=resume_supported,
        ),
        rollback_ready=rollback_ready,
        approval_audit_ready=approval_audit_ready,
        public_endpoint_enabled=public_endpoint_enabled,
        frontend_execute_enabled=frontend_execute_enabled,
        spm_dpabi_matlab_enabled=spm_dpabi_matlab_enabled,
        full_preprocessing_enabled=full_preprocessing_enabled,
        human_release_approval_required=True,
        warnings=warnings,
        errors=errors,
        blocking_issues=blocking,
        safety_flags={
            "public_endpoint_disabled": not public_endpoint_enabled,
            "frontend_execute_disabled": not frontend_execute_enabled,
            "spm_dpabi_matlab_disabled": not spm_dpabi_matlab_enabled,
            "full_preprocessing_disabled": not full_preprocessing_enabled,
            "human_release_approval_required": True,
            "rawdata_read_only": True,
        },
    )


def summarize_release_blockers(
    report: DicomConversionReleaseReadinessReport,
) -> dict[str, Any]:
    """Summarize the blockers and warnings from a release readiness report.

    Pure function — no file I/O, no subprocess.
    """
    return {
        "ok": report.ok,
        "status": report.status,
        "gates": f"{report.gates_met}/{report.gates_total}",
        "blocking_count": len(report.blocking_issues),
        "warning_count": len(report.warnings),
        "error_count": len(report.errors),
        "blockers": report.blocking_issues,
        "warnings": report.warnings,
        "human_release_approval_required": report.human_release_approval_required,
    }
