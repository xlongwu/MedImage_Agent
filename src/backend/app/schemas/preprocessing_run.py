"""Preprocessing Run Schema — Phase 6C.

Models for creating and executing preprocessing run workspaces with full
stage state machine: not_started → planned → dry_run_ready → running →
succeeded / failed / blocked / metadata_only.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ── Phase 6C stage statuses ──
STAGE_STATUS_VALUES = [
    "not_started", "planned", "dry_run_ready", "running",
    "succeeded", "failed", "metadata_only", "blocked", "disabled_external",
]


class PreprocessingRunCreateRequest(BaseModel):
    plan_id: str = ""
    preprocessing_input_dir: str = ""
    run_name: str = ""
    confirm_use_converted_input: bool = False
    confirm_no_rawdata_modification: bool = False
    confirm_python_only_execution: bool = False
    confirm_no_spm_matlab: bool = False


class PreprocessingRunCreateResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    preprocessing_run_id: str = ""; run_dir: str = ""
    preprocessing_input_dir: str = ""
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
    stage_statuses: list[PreprocessingStageStatus] = Field(default_factory=list)
    overall_progress: float = 0.0  # 0.0-1.0
    input_inventory_path: str = ""; qc_preflight_summary_path: str = ""
    manifest_path: str = ""
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
    overall_progress: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
