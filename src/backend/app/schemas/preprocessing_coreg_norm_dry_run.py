"""Coregistration + Normalization Dry-Run Schema — Phase 5G."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CoregNormDryRunRequest(BaseModel):
    registered_stage_output_id: str = ""
    functional_input_dir: str = ""
    confirm_dry_run_only: bool = False
    confirm_no_matlab_execution: bool = False
    confirm_no_image_modification: bool = False
    confirm_rawdata_readonly: bool = False
    confirm_converted_input_readonly: bool = False
    coreg_target: str = "mean_functional"
    normalization_voxel_size: str = "[3,3,3]"
    write_normalized_functional: bool = True
    write_normalized_t1w: bool = True


class CoregNormDryRunResponse(BaseModel):
    ok: bool = False
    status: str = "blocked"
    project_id: str = ""
    preprocessing_run_id: str = ""
    dry_run_id: str = ""
    dry_run_dir: str = ""
    subject_count: int = 0
    planned_subjects: list[str] = Field(default_factory=list)
    blocked_subjects: list[str] = Field(default_factory=list)
    functional_input_count: int = 0
    t1w_count: int = 0
    mean_functional_count: int = 0
    motion_parameter_count: int = 0
    batch_preview_paths: list[str] = Field(default_factory=list)
    planned_output_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


def coreg_norm_safety_flags() -> dict[str, bool]:
    return {
        "dry_run_only": True,
        "no_matlab_executed": True,
        "no_spm_executed": True,
        "no_image_outputs_written": True,
        "rawdata_not_modified": True,
        "converted_input_not_modified": True,
        "sandbox_outputs_not_modified": True,
        "no_external_tools_executed": True,
        "no_full_preprocessing": True,
        "no_dpabi": True,
        "research_use_only": True,
        "clinical_use_prohibited": True,
    }
