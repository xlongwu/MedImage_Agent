"""Preprocessing Handoff Schema — Phase 5A."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

from src.backend.app.schemas.preprocessing_stage_catalog import (
    build_legacy_dparsfa_stages,
    iter_preprocessing_stage_specs,
)


class PreprocessingInputRegistrationRequest(BaseModel):
    conversion_run_id: str = ""
    converted_bids_dir: str | None = None
    manifest_path: str | None = None
    provenance_path: str | None = None
    checksum_verified: bool = False
    mode: str = "reference"
    confirm_rawdata_readonly: bool = False
    confirm_use_converted_outputs: bool = False


class PreprocessingInputRegistrationResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    conversion_run_id: str = ""; preprocessing_input_dir: str = ""; rawdata_dir: str = ""
    subject_count: int = 0; bold_count: int = 0; t1w_count: int = 0
    nifti_count: int = 0; sidecar_count: int = 0
    artifact_registry_path: str = ""; artifact_count: int = 0
    artifacts_by_type: dict[str, int] = Field(default_factory=dict)
    missing_sidecar_pairings: list[dict[str, str]] = Field(default_factory=list)
    bids_entities: list[dict[str, Any]] = Field(default_factory=list)
    missing_t1w_subjects: list[str] = Field(default_factory=list)
    missing_bold_subjects: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list); errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class PreprocessingStagePreview(BaseModel):
    stage_id: str = ""; name: str = ""; backend: str = "python"
    subject_level: bool = True; requires_external_tool: bool = False
    enabled: bool = True; optional: bool = False; description: str = ""
    category: str = ""; default_enabled: bool = True
    required_for_fc: bool = False
    input_artifact_types: list[str] = Field(default_factory=list)
    output_artifact_types: list[str] = Field(default_factory=list)
    supported_backends: list[str] = Field(default_factory=list)
    default_backend: str = "python"; requires_approval: bool = False
    requires_env_flags: list[str] = Field(default_factory=list)
    can_run_in_ci: bool = True
    scientific_status: str = "metadata_only"
    validation_status: str = ""


class PreprocessingPlanPreviewResponse(BaseModel):
    ok: bool = False; status: str = "preview_only"; project_id: str = ""
    stages: list[PreprocessingStagePreview] = Field(default_factory=list)
    stage_count: int = 0; enabled_stage_count: int = 0
    execution_disabled: bool = True; preprocessing_input_registered: bool = False
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


_DPARSFA_STAGES: list[dict[str, Any]] = build_legacy_dparsfa_stages()


def build_default_dparsfa_style_plan(project_id: str = "", input_registered: bool = False) -> PreprocessingPlanPreviewResponse:
    stages: list[PreprocessingStagePreview] = []
    for spec in iter_preprocessing_stage_specs():
        stages.append(PreprocessingStagePreview(
            stage_id=spec.stage_id,
            name=spec.display_name,
            backend=spec.default_backend,
            subject_level=spec.subject_level,
            requires_external_tool=spec.requires_external_tool,
            enabled=spec.default_enabled,
            optional=spec.optional,
            description=spec.description,
            category=spec.category,
            default_enabled=spec.default_enabled,
            required_for_fc=spec.required_for_fc,
            input_artifact_types=list(spec.input_artifact_types),
            output_artifact_types=list(spec.output_artifact_types),
            supported_backends=list(spec.supported_backends),
            default_backend=spec.default_backend,
            requires_approval=spec.requires_approval,
            requires_env_flags=list(spec.requires_env_flags),
            can_run_in_ci=spec.can_run_in_ci,
            scientific_status=spec.scientific_status,
            validation_status=spec.validation_status,
        ))
    enabled_count = sum(1 for s in stages if s.enabled)
    w = [] if input_registered else ["Preprocessing input has not been registered."]
    return PreprocessingPlanPreviewResponse(ok=True, status="preview_only", project_id=project_id, stages=stages, stage_count=len(stages), enabled_stage_count=enabled_count, execution_disabled=True, preprocessing_input_registered=input_registered, warnings=w, next_actions=["Register converted BIDS as preprocessing input.", "Review blocked SPM/MATLAB stages before any external-tool execution.", "Keep preview_only and metadata_only stages distinct from succeeded outputs."], safety_flags={"preview_only": True, "no_preprocessing_executed": True, "no_external_tools_executed": True, "spm_dpabi_matlab_disabled": True, "rawdata_read_only": True, "research_use_only": True})
