"""Preprocessing Run Schema — Phase 6C.

Models for creating and executing preprocessing run workspaces with full
stage state machine shared with preprocessing_stage_catalog.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

from src.backend.app.schemas.preprocessing_stage_catalog import (
    PREPROCESSING_STAGE_STATUS_VALUES,
)


# ── Phase 6C stage statuses ──
STAGE_STATUS_VALUES = list(PREPROCESSING_STAGE_STATUS_VALUES)


class PreprocessingRunCreateRequest(BaseModel):
    plan_id: str = ""
    preprocessing_input_dir: str = ""
    input_registry_path: str = ""
    source_kind: str = ""
    conversion_run_id: str = ""
    run_name: str = ""
    confirm_use_converted_input: bool = False
    confirm_no_rawdata_modification: bool = False
    confirm_python_only_execution: bool = False
    confirm_no_spm_matlab: bool = False


class PreprocessingRunCreateResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    preprocessing_run_id: str = ""; run_dir: str = ""
    preprocessing_input_dir: str = ""
    artifact_registry_path: str = ""
    input_inventory: dict[str, Any] = Field(default_factory=dict)
    stage_count: int = 0; python_stage_count: int = 0
    external_blocked_count: int = 0; planned_stage_count: int = 0
    disabled_external_stage_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class PreprocessingStageStatus(BaseModel):
    stage_id: str = ""; name: str = ""; status: str = "not_started"
    backend: str = "python"; requires_external_tool: bool = False
    enabled: bool = True; optional: bool = False
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
    # Phase 6C: execution metadata
    input_manifest: dict[str, Any] = Field(default_factory=dict)
    output_manifest: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float | None = None
    error_message: str | None = None
    registered_at: str | None = None


class PreprocessingRunExecuteResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    preprocessing_run_id: str = ""
    completed_stages: list[str] = Field(default_factory=list)
    blocked_stages: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    disabled_external_stages: list[str] = Field(default_factory=list)
    metadata_only_stages: list[str] = Field(default_factory=list)
    preview_only_stages: list[str] = Field(default_factory=list)
    stage_statuses: list[PreprocessingStageStatus] = Field(default_factory=list)
    overall_progress: float = 0.0  # 0.0-1.0
    input_inventory_path: str = ""; qc_preflight_summary_path: str = ""
    manifest_path: str = ""
    artifact_registry_path: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class PreprocessingRunStatusResponse(BaseModel):
    ok: bool = False; project_id: str = ""; preprocessing_run_id: str = ""
    run_dir: str = ""; preprocessing_input_dir: str = ""
    status: str = "unknown"; created_at: str = ""
    stage_statuses: list[PreprocessingStageStatus] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    artifact_registry_path: str = ""
    input_inventory: dict[str, Any] = Field(default_factory=dict)
    overall_progress: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
