"""Reviewed preprocessing pipeline execution schemas.

These models describe the reviewed full-preprocessing backend contract. They
do not execute scientific kernels by themselves; execution remains in services
and registered node runners.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.backend.app.schemas.preprocessing_run import PreprocessingStageStatus


PreprocessingPipelineProfile = Literal["fc_minimal", "dparsfa_like", "custom"]
PreprocessingStageMode = Literal["enabled", "disabled", "auto"]
PreprocessingRerunPolicy = Literal["skip_succeeded", "require_explicit", "rerun_new_execution"]


class PreprocessingBackendPolicy(BaseModel):
    motion_correction: str = "spm12"
    normalization: str = "skip"
    nuisance_regression: str = "python"
    temporal_filtering: str = "python"
    functional_connectivity: str = "python"
    alff_falff: str = "python"
    reho: str = "python"


class PreprocessingAtlasConfig(BaseModel):
    atlas_path: str = ""
    labels_path: str = ""
    atlas_space: str = "native_or_matched"
    allow_resample: bool = False


class PreprocessingNuisanceConfig(BaseModel):
    model: str = "friston24"
    include_wm_csf: bool = False
    include_global_signal: bool = False
    include_linear_trend: bool = True
    include_intercept: bool = True


class PreprocessingFilteringConfig(BaseModel):
    low_hz: float = 0.01
    high_hz: float = 0.08
    fallback_tr: float | None = None
    tr: float | None = None


class PreprocessingExecutionLimits(BaseModel):
    preview_limit: int | None = None
    max_subjects: int | None = None


class PreprocessingReviewedConfirmations(BaseModel):
    confirm_rawdata_readonly: bool = False
    confirm_reviewed_execution: bool = False
    confirm_external_tools_if_needed: bool = False
    confirm_research_use_only: bool = False
    confirm_no_clinical_use: bool = False


class PreprocessingPipelineExecuteRequest(BaseModel):
    pipeline_profile: PreprocessingPipelineProfile = "fc_minimal"
    start_from: str = "existing_preprocessing_input"
    backend_policy: PreprocessingBackendPolicy = Field(default_factory=PreprocessingBackendPolicy)
    stages: dict[str, PreprocessingStageMode] = Field(default_factory=dict)
    atlas: PreprocessingAtlasConfig = Field(default_factory=PreprocessingAtlasConfig)
    nuisance: PreprocessingNuisanceConfig = Field(default_factory=PreprocessingNuisanceConfig)
    filtering: PreprocessingFilteringConfig = Field(default_factory=PreprocessingFilteringConfig)
    execution_limits: PreprocessingExecutionLimits = Field(default_factory=PreprocessingExecutionLimits)
    confirmations: PreprocessingReviewedConfirmations = Field(default_factory=PreprocessingReviewedConfirmations)
    approval: dict[str, Any] | None = None
    resume: bool = True
    rerun_policy: PreprocessingRerunPolicy = "skip_succeeded"
    derivatives_dir: str = ""
    generate_report: bool = True
    run_validation: bool = True


class PreprocessingPipelineStageResult(BaseModel):
    stage_id: str
    name: str = ""
    status: str = "not_started"
    enabled: bool = True
    optional: bool = False
    backend: str = ""
    node_id: str = ""
    started_at: str = ""
    ended_at: str = ""
    skipped_reason: str = ""
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    output_artifact_ids: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)


class PreprocessingPipelineExecuteResponse(BaseModel):
    ok: bool = False
    status: str = "blocked"
    project_id: str = ""
    preprocessing_run_id: str = ""
    execution_id: str = ""
    pipeline_profile: str = ""
    manifest_path: str = ""
    artifact_registry_path: str = ""
    report_path: str = ""
    validation_status: str = ""
    completed_stages: list[str] = Field(default_factory=list)
    skipped_stages: list[str] = Field(default_factory=list)
    blocked_stages: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    metadata_only_stages: list[str] = Field(default_factory=list)
    preview_only_stages: list[str] = Field(default_factory=list)
    stage_results: list[PreprocessingPipelineStageResult] = Field(default_factory=list)
    stage_statuses: list[PreprocessingStageStatus] = Field(default_factory=list)
    approval_gate: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


__all__ = [
    "PreprocessingAtlasConfig",
    "PreprocessingBackendPolicy",
    "PreprocessingExecutionLimits",
    "PreprocessingFilteringConfig",
    "PreprocessingNuisanceConfig",
    "PreprocessingPipelineExecuteRequest",
    "PreprocessingPipelineExecuteResponse",
    "PreprocessingPipelineStageResult",
    "PreprocessingReviewedConfirmations",
    "PreprocessingRerunPolicy",
    "PreprocessingStageMode",
]
