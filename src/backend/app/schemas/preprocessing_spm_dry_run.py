"""Preprocessing SPM Dry-Run Schema — Phase 5D."""
from __future__ import annotations
from pydantic import BaseModel, Field


class SliceTimingRealignDryRunRequest(BaseModel):
    tr: float | None = None; num_slices: int | None = None
    slice_order: str = ""; reference_slice: int | None = None
    preprocessing_input_dir: str = ""
    confirm_dry_run_only: bool = False; confirm_no_matlab_execution: bool = False
    confirm_no_image_modification: bool = False; confirm_rawdata_readonly: bool = False


class SliceTimingRealignDryRunResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    preprocessing_run_id: str = ""; dry_run_id: str = ""; dry_run_dir: str = ""
    subject_count: int = 0; planned_subjects: list[str] = Field(default_factory=list)
    blocked_subjects: list[str] = Field(default_factory=list)
    bold_count: int = 0
    batch_preview_paths: list[str] = Field(default_factory=list)
    planned_output_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


def safety_flags_dry_run() -> dict[str, bool]:
    return {"dry_run_only": True, "no_matlab_executed": True, "no_spm_executed": True,
            "no_image_outputs_written": True, "rawdata_not_modified": True,
            "no_external_tools_executed": True, "research_use_only": True,
            "clinical_use_prohibited": True}
