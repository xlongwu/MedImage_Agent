"""Preprocessing Run Schema — Phase 5B.

Models for creating and executing Python-only preprocessing run workspaces.
No SPM/DPABI/MATLAB. No external tools. No full preprocessing.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


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


class PreprocessingRunExecuteResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    preprocessing_run_id: str = ""
    completed_stages: list[str] = Field(default_factory=list)
    blocked_stages: list[str] = Field(default_factory=list)
    disabled_external_stages: list[str] = Field(default_factory=list)
    stage_statuses: list[PreprocessingStageStatus] = Field(default_factory=list)
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
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
