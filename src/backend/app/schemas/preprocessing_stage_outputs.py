"""Preprocessing Stage Output Registration Schema — Phase 5F."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StageOutputRegistrationRequest(BaseModel):
    execution_id: str = ""
    confirm_sandbox_outputs: bool = False
    confirm_rawdata_readonly: bool = False
    confirm_converted_input_readonly: bool = False
    confirm_no_additional_execution: bool = False
    confirm_use_as_next_stage_input: bool = False


class StageOutputRegistrationResponse(BaseModel):
    ok: bool = False
    status: str = "blocked"
    project_id: str = ""
    preprocessing_run_id: str = ""
    execution_id: str = ""
    registered_stage_output_id: str = ""
    stage_output_dir: str = ""
    next_stage_input_dir: str = ""
    subject_count: int = 0
    registered_bold_outputs: list[str] = Field(default_factory=list)
    missing_subject_outputs: list[str] = Field(default_factory=list)
    motion_files: list[str] = Field(default_factory=list)
    mean_images: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


def registration_safety_flags() -> dict[str, bool]:
    return {
        "rawdata_not_modified": True,
        "converted_input_not_modified": True,
        "sandbox_outputs_referenced": True,
        "no_additional_execution": True,
        "no_matlab_executed": True,
        "no_spm_executed": True,
        "no_full_preprocessing": True,
        "no_dpabi": True,
        "research_use_only": True,
        "clinical_use_prohibited": True,
    }
