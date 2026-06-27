"""DICOM Conversion Execution Schema — Phase 4B.

Defines conversion modes, statuses, output kinds, command templates,
conversion mappings, preflight models, execution request/response models,
safety flags, and pure helper functions for the safe, auditable,
disabled-by-default DICOM-to-NIfTI conversion wrapper.

Schema-only module.  No subprocess.  No file writes.  No external tool
imports.  No real dcm2niix execution is enabled.

Reference:
  docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md
  docs/REAL_PREPROCESSING_EXECUTION_CONTRACT.md
"""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# 1. Literal type aliases
# ═══════════════════════════════════════════════════════════════════════

DicomConversionMode = Literal[
    "dry_run",
    "preflight",
    "execute_disabled",
    "execute",
]

# Note: The task plan (§12) mentions an `unavailable` state. It is represented
# here by `blocked` (when dcm2niix is missing/unknown) or `disabled` (when the
# feature flag is off). See `_map_availability_to_conversion_status` in
# dicom_conversion_execution.py for the canonical mapping.
DicomConversionStatus = Literal[
    "pending",
    "running",
    "ready",
    "review_required",
    "blocked",
    "warning",
    "disabled",
    "failed",
    "partial",
    "succeeded",
]

DicomConversionTool = Literal[
    "dcm2niix",
    "unknown",
]

DicomConversionOutputKind = Literal[
    "nifti",
    "json_sidecar",
    "bval",
    "bvec",
    "log",
    "stdout_log",
    "stderr_log",
    "manifest",
    "provenance",
    "node_state",
    "directory",
]

# ═══════════════════════════════════════════════════════════════════════
# 2. Required environment flags for real execution
# ═══════════════════════════════════════════════════════════════════════
#
# Per 实现dcm2nii任务方案.md §11.1, DICOM→NIfTI conversion must NOT be
# blocked by MATLAB/SPM/real-preprocessing flags. Those flags belong to
# the downstream preprocessing module only. The minimal required flags
# for DICOM conversion are:
#   - MEDIMAGE_ENABLE_DICOM_CONVERSION
#   - MEDIMAGE_ENABLE_REVIEWED_EXECUTION
#   - MEDIMAGE_ALLOW_USER_DATA_CONVERSION
#
# MEDIMAGE_MATLAB_ENABLED, MEDIMAGE_SPM_SMOKE_ENABLED and
# MEDIMAGE_ENABLE_REAL_PREPROCESSING are intentionally NOT required here.
# "MATLAB/SPM not enabled" is a safe state and must not block conversion.
_REQUIRED_CONVERSION_ENV_FLAGS: frozenset[str] = frozenset({
    "MEDIMAGE_ENABLE_DICOM_CONVERSION",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION",
})

# ═══════════════════════════════════════════════════════════════════════
# 3. Pydantic models
# ═══════════════════════════════════════════════════════════════════════


class Dcm2niixCommandTemplate(BaseModel):
    """A validated dcm2niix command template.

    ``command_preview`` is display-only.  Future execution must use
    the structured fields to build an argv list, never a shell string.
    """

    tool: DicomConversionTool = "dcm2niix"
    executable: str = "dcm2niix"
    input_dir: str = ""
    output_dir: str = ""
    filename_pattern: str = "%p_%s"
    compress: str = "y"
    bids_sidecar: bool = True
    create_bids: bool = True
    additional_flags: list[str] = Field(default_factory=list)
    command_preview: str = ""

    model_config = {"extra": "forbid"}


class DicomConversionMapping(BaseModel):
    """A single DICOM → NIfTI mapping derived from the dry-run planner."""

    source_path: str = ""
    source_type: str = "dicom_series"
    subject_id: str | None = None
    session_id: str | None = None
    modality: str = "func"
    suffix: str | None = None
    task: str | None = None
    suggested_relative_path: str | None = None
    output_dir: str | None = None
    output_filename: str | None = None
    confidence: str = "high"
    enabled: bool = True
    warnings: list[str] = Field(default_factory=list)
    status: str | None = None  # execution status per mapping: succeeded / failed / running


class DicomConversionSafetyFlags(BaseModel):
    """Safety flags for DICOM conversion execution.

    All default to the safest possible values.  Real execution requires
    explicit opt-in via environment flags, approval, and audit.
    """

    rawdata_read_only: bool = True
    output_under_project: bool = True
    no_shell_string: bool = True
    command_template_only: bool = True
    approval_required: bool = True
    audit_required: bool = True
    conversion_disabled_by_default: bool = True
    env_flags_missing: bool = True
    no_spm_dpabi_matlab: bool = True
    clinical_use_prohibited: bool = True
    research_use_only: bool = True


class DicomConversionPreflight(BaseModel):
    """Result of pre-execution conversion readiness check."""

    ok: bool = True
    status: DicomConversionStatus = "disabled"
    mode: DicomConversionMode = "preflight"
    conversion_disabled_by_default: bool = True
    tool_available: bool = False
    executable_path: str | None = None
    tool_version: str | None = None
    env_enabled: bool = False
    missing_env_flags: list[str] = Field(default_factory=list)
    approval_required: bool = True
    audit_required: bool = True
    output_dir_safe: bool = False
    output_root_preview: str | None = None
    rawdata_readonly: bool = True
    mapping_count: int = 0
    mappings: list[DicomConversionMapping] = Field(default_factory=list)
    command_templates: list[Dcm2niixCommandTemplate] = Field(default_factory=list)
    planned_manifest_path: str | None = None
    planned_provenance_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    safety_flags: DicomConversionSafetyFlags = Field(
        default_factory=DicomConversionSafetyFlags
    )


class DicomConversionExecutionRequest(BaseModel):
    """Request to execute DICOM conversion.

    When ``mode`` is ``"execute_disabled"``, the response will confirm
    that execution is blocked.  When ``mode`` is ``"execute"``, all gating
    conditions (env flags, approval, audit, output safety) must be satisfied.
    """

    project_id: str = ""
    reviewed_plan_id: str | None = None
    mode: DicomConversionMode = "execute_disabled"
    confirm_execution: bool = False
    approval_id: str | None = None
    audit_id: str | None = None
    output_root: str | None = None
    overwrite_policy: str = "fail_if_exists"
    mapping_ids: list[str] = Field(default_factory=list)
    mappings: list[DicomConversionMapping] = Field(default_factory=list)
    actor: str = "frontend-user"


class DicomConversionExecutionResponse(BaseModel):
    """Response from a DICOM conversion execution attempt."""

    ok: bool = True
    status: DicomConversionStatus = "disabled"
    mode: DicomConversionMode = "execute_disabled"
    project_id: str = ""
    dry_run: bool = False
    conversion_disabled: bool = True
    execution_blocked: bool = True
    mappings: list[DicomConversionMapping] = Field(default_factory=list)
    command_templates: list[Dcm2niixCommandTemplate] = Field(default_factory=list)
    output_root: str | None = None
    manifest_path: str | None = None
    provenance_path: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    safety_flags: DicomConversionSafetyFlags = Field(
        default_factory=DicomConversionSafetyFlags
    )


class DicomConversionFailureRecord(BaseModel):
    """Record of a DICOM conversion failure."""

    stage: str = "dicom_to_nifti"
    status: str = "failed"
    message: str = ""
    mapping_index: int | None = None
    subject_id: str | None = None
    executable: str | None = None
    return_code: int | None = None
    retryable: bool = False
    rolled_back: bool = False
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# 4. Pure helper functions
# ═══════════════════════════════════════════════════════════════════════


def build_dcm2niix_command_template(
    *,
    input_dir: str,
    output_dir: str,
    filename_pattern: str = "%p_%s",
    executable: str = "dcm2niix",
    compress: str = "y",
    bids_sidecar: bool = True,
    create_bids: bool = True,
    additional_flags: list[str] | None = None,
) -> Dcm2niixCommandTemplate:
    """Build a validated dcm2niix command template from structured fields.

    Returns a ``Dcm2niixCommandTemplate`` with a display-only
    ``command_preview``.  No subprocess is called.  No file I/O is
    performed.

    ``command_preview`` is for human inspection only.  Future execution
    should construct argv from the structured fields, NOT from this string.
    """
    flags = list(additional_flags or [])
    argv_parts: list[str] = [executable]

    if compress:
        argv_parts.extend(["-z", compress])
    if filename_pattern:
        argv_parts.extend(["-f", filename_pattern])
    if bids_sidecar:
        argv_parts.extend(["-b", "y"])
    if create_bids:
        argv_parts.extend(["-ba", "y"])

    argv_parts.extend(flags)
    argv_parts.extend(["-o", f'"{output_dir}"', f'"{input_dir}"'])

    command_preview = " ".join(argv_parts)

    return Dcm2niixCommandTemplate(
        tool="dcm2niix",
        executable=executable,
        input_dir=input_dir,
        output_dir=output_dir,
        filename_pattern=filename_pattern,
        compress=compress,
        bids_sidecar=bids_sidecar,
        create_bids=create_bids,
        additional_flags=list(additional_flags or []),
        command_preview=command_preview,
    )


def build_disabled_conversion_response(
    *,
    project_id: str = "",
    reason: str = "DICOM conversion execution is disabled by default.",
    missing_env_flags: list[str] | None = None,
) -> DicomConversionExecutionResponse:
    """Build a standard disabled-response for conversion execution.

    Pure function — no subprocess, no file I/O.  Always returns
    ``conversion_disabled=true``, ``execution_blocked=true``.
    """
    flags = DicomConversionSafetyFlags(
        conversion_disabled_by_default=True,
        env_flags_missing=bool(missing_env_flags),
    )
    return DicomConversionExecutionResponse(
        ok=True,
        status="disabled",
        mode="execute_disabled",
        project_id=project_id,
        dry_run=False,
        conversion_disabled=True,
        execution_blocked=True,
        blocking_issues=[
            reason,
            *[f"Missing env flag: {f}" for f in (missing_env_flags or [])],
        ],
        safety_flags=flags,
    )


def is_conversion_execution_enabled(
    env: Mapping[str, str],
) -> tuple[bool, list[str]]:
    """Check whether all required env flags are set for real conversion.

    Returns ``(all_set, missing)``.  All flags in
    ``_REQUIRED_CONVERSION_ENV_FLAGS`` must be ``"1"``.

    Pure function — no subprocess, no file I/O.
    """
    missing = sorted(
        f for f in _REQUIRED_CONVERSION_ENV_FLAGS if env.get(f) != "1"
    )
    return len(missing) == 0, missing


def validate_output_root_under_project(
    output_root: str,
    project_dir: str,
) -> bool:
    """Return True if *output_root* resolves inside *project_dir*.

    Pure function — no filesystem access.  Uses path resolution to
    detect traversal attempts.  Works with both POSIX and Windows paths.
    """
    if not output_root or not project_dir:
        return False

    # Normalise path separators
    def _normalise(p: str) -> str:
        return p.replace("\\", "/").rstrip("/")

    norm_out = _normalise(output_root)
    norm_proj = _normalise(project_dir)

    # Reject path traversal
    parts = [part for part in norm_out.split("/") if part and part != ".."]
    if ".." in norm_out.split("/"):
        return False

    reconstructed = "/" + "/".join(parts) if norm_out.startswith("/") else "/".join(parts)
    reconstructed_proj = (
        "/" + "/".join(p for p in norm_proj.split("/") if p and p != "..")
        if norm_proj.startswith("/")
        else "/".join(p for p in norm_proj.split("/") if p and p != "..")
    )

    return reconstructed.startswith(reconstructed_proj)


def validate_output_root_not_under_rawdata(
    output_root: str,
    rawdata_dir: str,
) -> bool:
    """Return True if *output_root* does NOT resolve inside *rawdata_dir*.

    Pure function — no filesystem access.
    """
    if not output_root or not rawdata_dir:
        return True  # Can't validate, assume safe
    return not validate_output_root_under_project(output_root, rawdata_dir)


def summarize_conversion_mappings(
    mappings: list[DicomConversionMapping],
) -> dict[str, Any]:
    """Aggregate summary statistics for a list of conversion mappings.

    Pure function — no file I/O.
    """
    if not mappings:
        return {
            "total_count": 0,
            "func_count": 0,
            "anat_count": 0,
            "subject_ids": [],
            "confidence_high": 0,
            "enabled_count": 0,
        }
    return {
        "total_count": len(mappings),
        "func_count": sum(1 for m in mappings if m.modality == "func"),
        "anat_count": sum(1 for m in mappings if m.modality == "anat"),
        "subject_ids": sorted(
            {m.subject_id for m in mappings if m.subject_id}
        ),
        "confidence_high": sum(1 for m in mappings if m.confidence == "high"),
        "enabled_count": sum(1 for m in mappings if m.enabled),
    }


# ═══════════════════════════════════════════════════════════════════════
# 5. Phase 4C-0 — Availability and Sandbox models
# ═══════════════════════════════════════════════════════════════════════

Dcm2niixAvailabilityStatus = Literal[
    "available",
    "missing",
    "version_failed",
    "disabled",
    "unknown",
]

DicomConversionSandboxMode = Literal[
    "fake_outputs",
    "mock_subprocess",
    "disabled",
]


class Dcm2niixAvailabilityCheck(BaseModel):
    """Result of a dcm2niix availability and version check."""

    ok: bool = True
    status: Dcm2niixAvailabilityStatus = "unknown"
    executable: str = "dcm2niix"
    executable_path: str | None = None
    version: str | None = None
    binary_sha256: str | None = None
    detection_strategy: str | None = None
    expected_version: str | None = None
    env_enabled: bool = False
    missing_env_flags: list[str] = Field(default_factory=list)
    checked_at: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionSandboxResult(BaseModel):
    """Result of a fake/sandbox conversion run.

    No real dcm2niix is called.  Artifact paths are placeholders unless
    the test environment explicitly creates files under ``output_root``.
    """

    ok: bool = True
    status: DicomConversionStatus = "disabled"
    mode: DicomConversionSandboxMode = "disabled"
    project_id: str = ""
    output_root: str | None = None
    mapping_count: int = 0
    command_template_count: int = 0
    created_artifact_count: int = 0
    manifest_path: str | None = None
    provenance_path: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    safety_flags: DicomConversionSafetyFlags = Field(
        default_factory=DicomConversionSafetyFlags
    )


# ═══════════════════════════════════════════════════════════════════════
# 6. Phase 4C-0 — Pure helper functions
# ═══════════════════════════════════════════════════════════════════════


def is_dcm2niix_availability_ready(
    check: Dcm2niixAvailabilityCheck,
) -> bool:
    """Return True if the availability check passes all gating conditions."""
    return (
        check.ok
        and check.status == "available"
        and check.env_enabled
        and check.executable_path is not None
    )


def requires_fake_or_sandbox_mode(
    mode: DicomConversionSandboxMode,
) -> bool:
    """Return True if *mode* is a non-disabled sandbox mode."""
    return mode in {"fake_outputs", "mock_subprocess"}


def summarize_sandbox_artifacts(
    artifacts: list[str],
) -> dict[str, int]:
    """Count artifact types from a sandbox result."""
    return {"total_count": len(artifacts)}


def build_disabled_sandbox_result(
    *,
    project_id: str = "",
    reason: str = "Sandbox conversion is disabled by default.",
) -> DicomConversionSandboxResult:
    """Build a standard disabled sandbox result."""
    return DicomConversionSandboxResult(
        ok=True,
        status="disabled",
        mode="disabled",
        project_id=project_id,
        blocking_issues=[reason],
        safety_flags=DicomConversionSafetyFlags(),
    )


def parse_dcm2niix_version(stdout: str) -> str | None:
    """Parse dcm2niix version from ``dcm2niix --version`` stdout.

    Pure function — no subprocess.  Extracts a version string like
    ``"v1.0.20230411"`` from the first line of output.
    """
    if not stdout:
        return None
    first_line = stdout.strip().split("\n")[0]
    # Look for "version vX.Y.Z" or "vX.Y.Z" pattern
    import re

    match = re.search(r"v(\d+\.\d+\.\d+)", first_line)
    if match:
        return match.group(0)
    return first_line.strip()[:80] if first_line.strip() else None


def redact_command_preview(preview: str) -> str:
    """Redact potentially sensitive paths from a command preview string.

    Currently a pass-through.  Extend when path-safety redaction is needed.
    """
    return preview
