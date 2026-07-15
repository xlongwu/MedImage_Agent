"""DICOM Conversion Prepare Schema — 实现dcm2nii任务方案.md §13.

Defines the request/response models for the unified prepare endpoint that
orchestrates approval and execution preparation in a single call.

Per §13.3, user confirmations and system validations are separated:
- User confirmations: mappings reviewed, rawdata readonly, research use only,
  no clinical use, external converter, rollback policy, risk acknowledgement,
  confirm execution.
- System validations: output root safety, dcm2niix availability, mapping
  completeness, checksum generation, rollback plan, disk space, env gates.

Schema-only module. No subprocess. No file writes. No dcm2niix.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# ── 1. Literal type aliases ────────────────────────────────────────────────

DicomConversionPrepareStatus = Literal[
    "ready",
    "review_required",
    "blocked",
    "disabled",
    "partial",
    "failed",
]


# ── 2. Operator confirmation model ─────────────────────────────────────────


class DicomConversionPrepareConfirmations(BaseModel):
    """Operator confirmations required before execution.

    Per 实现dcm2nii任务方案.md §13.1, these are user-side acknowledgements.
    System-verifiable fields (output root safety, dcm2niix availability, etc.)
    are NOT included here — the backend validates those automatically.
    """

    mappings_reviewed: bool = False
    rawdata_readonly: bool = False
    research_use_only: bool = False
    no_clinical_use: bool = False
    native_converter: bool = False
    # Deprecated request compatibility; normalized to native_converter.
    external_converter: bool = False
    rollback_policy: bool = False
    risk_acknowledgement: bool = False
    approval_audit: bool = False
    public_endpoint: bool = False
    frontend_execute: bool = False
    spm_dpabi_matlab_disabled: bool = False
    confirm_execution: bool = False

    @model_validator(mode="after")
    def _normalize_legacy_converter_acknowledgement(self) -> "DicomConversionPrepareConfirmations":
        if self.external_converter and not self.native_converter:
            self.native_converter = True
        return self


# ── 3. Prepare request ─────────────────────────────────────────────────────


class DicomConversionPrepareRequest(BaseModel):
    """Request body for POST /api/projects/{project_id}/dicom-conversion/prepare.

    Per 实现dcm2nii任务方案.md §13.1.
    """

    approved_by: str = "operator"
    selected_mapping_ids: list[str] = Field(default_factory=list)
    overwrite_policy: str = "fail_if_exists"
    confirmations: DicomConversionPrepareConfirmations = Field(
        default_factory=DicomConversionPrepareConfirmations
    )


# ── 4. Prepare response ────────────────────────────────────────────────────


class DicomConversionPrepareSystemChecks(BaseModel):
    """System-validated preconditions, computed by the backend.

    Per 实现dcm2nii任务方案.md §13.3, these are NOT user-supplied.
    """

    preflight_ok: bool = False
    conversion_backend: str = "medimage-native"
    native_converter_available: bool = False
    native_converter_version: str | None = None
    native_dependency_versions: dict[str, str] = Field(default_factory=dict)
    # Deprecated compatibility fields. The external converter is not used.
    dcm2niix_available: bool = False
    dcm2niix_path: str | None = None
    dcm2niix_version: str | None = None
    dcm2niix_sha256: str | None = None
    dcm2niix_strategy: str | None = None
    mappings_complete: bool = False
    mapping_count: int = 0
    output_root_safe: bool = False
    output_root: str | None = None
    rawdata_dir: str | None = None
    project_dir: str | None = None
    disk_space_ok: bool = False
    disk_free_bytes: int | None = None
    disk_required_bytes: int | None = None
    checksum_before_exists: bool = False
    checksum_before_path: str | None = None
    rollback_plan_exists: bool = False
    rollback_plan_path: str | None = None
    env_gates_ok: bool = False
    missing_env_flags: list[str] = Field(default_factory=list)


class DicomConversionPrepareResponse(BaseModel):
    """Response from the prepare endpoint.

    Returns the authoritative readiness state, the reserved conversion run,
    and the persisted approval record paths.
    """

    ok: bool = False
    status: DicomConversionPrepareStatus = "blocked"
    project_id: str = ""
    conversion_run_id: str = ""
    approval_id: str = ""
    technical_ready: bool = False
    approval_ready: bool = False
    execution_ready: bool = False
    next_action: str = "review_conversion_plan"
    system_checks: DicomConversionPrepareSystemChecks = Field(
        default_factory=DicomConversionPrepareSystemChecks
    )
    operator_confirmations: DicomConversionPrepareConfirmations = Field(
        default_factory=DicomConversionPrepareConfirmations
    )
    missing_confirmations: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    run_dir: str | None = None
    approval_record_path: str | None = None
    release_approval_id: str = ""
    release_approval_record_path: str | None = None
    release_approval_decision_path: str | None = None
    audit_preview_path: str | None = None
    preflight_snapshot_path: str | None = None
    mapping_snapshot_path: str | None = None
    command_templates_path: str | None = None
    checksum_before_path: str | None = None
    rollback_plan_path: str | None = None
    review_package_path: str | None = None


# ── 5. Pure helper functions ───────────────────────────────────────────────


_CONFIRMATION_LABELS: dict[str, str] = {
    "mappings_reviewed": "Mappings reviewed",
    "rawdata_readonly": "Rawdata read-only acknowledgement",
    "research_use_only": "Research-use-only acknowledgement",
    "no_clinical_use": "No-clinical-use acknowledgement",
    "native_converter": "In-project native converter acknowledgement",
    "rollback_policy": "Rollback policy acknowledgement",
    "risk_acknowledgement": "Risk acknowledgement",
    "approval_audit": "Approval/audit acknowledgement",
    "public_endpoint": "Public endpoint acknowledgement",
    "frontend_execute": "Frontend execute acknowledgement",
    "spm_dpabi_matlab_disabled": "SPM/DPABI/MATLAB disabled acknowledgement",
    "confirm_execution": "Execution confirmation",
}

_REQUIRED_CONFIRMATIONS: frozenset[str] = frozenset({
    "mappings_reviewed",
    "rawdata_readonly",
    "research_use_only",
    "no_clinical_use",
    "native_converter",
    "rollback_policy",
    "risk_acknowledgement",
    "approval_audit",
    "public_endpoint",
    "frontend_execute",
    "spm_dpabi_matlab_disabled",
    "confirm_execution",
})


def validate_prepare_confirmations(
    confirmations: DicomConversionPrepareConfirmations,
) -> tuple[bool, list[str]]:
    """Validate that all operator confirmations are True.

    Returns (ok, missing_labels).
    Pure function — no file I/O, no subprocess.
    """
    missing: list[str] = []
    for field_name in sorted(_REQUIRED_CONFIRMATIONS):
        value = getattr(confirmations, field_name, False)
        if not value:
            missing.append(_CONFIRMATION_LABELS.get(field_name, field_name))
    return len(missing) == 0, missing


def determine_prepare_next_action(
    *,
    technical_ready: bool,
    approval_ready: bool,
    execution_ready: bool,
    dcm2niix_available: bool,
    mapping_count: int,
    output_root_safe: bool,
    env_gates_ok: bool,
) -> str:
    """Determine the next action string for the UI.

    Per 实现dcm2nii任务方案.md §16.4.
    Pure function — no file I/O, no subprocess.
    """
    if not env_gates_ok:
        return "enable_dicom_conversion"
    if not dcm2niix_available:
        return "open_settings"
    if mapping_count == 0:
        return "regenerate_conversion_plan"
    if not output_root_safe:
        return "reset_output_location"
    if not technical_ready:
        return "check_conversion_readiness"
    if not approval_ready:
        return "review_and_approve_mappings"
    if not execution_ready:
        return "convert_dicom_to_nifti"
    return "convert_dicom_to_nifti"


__all__ = [
    "DicomConversionPrepareStatus",
    "DicomConversionPrepareConfirmations",
    "DicomConversionPrepareRequest",
    "DicomConversionPrepareSystemChecks",
    "DicomConversionPrepareResponse",
    "validate_prepare_confirmations",
    "determine_prepare_next_action",
]
