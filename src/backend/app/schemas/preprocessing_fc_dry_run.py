"""FC Dry-Run Schema — Phase 5M."""
from __future__ import annotations
from pydantic import BaseModel, Field


class FcDryRunRequest(BaseModel):
    filtered_stage_output_id: str = ""; functional_input_dir: str = ""
    atlas_name: str = ""; atlas_path: str = ""; correlation_method: str = "pearson"
    fisher_z: bool = True
    confirm_dry_run_only: bool = False; confirm_no_image_modification: bool = False
    confirm_no_external_tools: bool = False; confirm_previous_outputs_readonly: bool = False


class FcDryRunResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    preprocessing_run_id: str = ""; dry_run_id: str = ""; dry_run_dir: str = ""
    subject_count: int = 0; planned_subjects: list[str] = Field(default_factory=list)
    blocked_subjects: list[str] = Field(default_factory=list)
    functional_input_count: int = 0; atlas_status: str = "none"
    fc_plan_paths: list[str] = Field(default_factory=list)
    planned_output_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list); errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


def fc_safety_flags() -> dict[str, bool]:
    return {"dry_run_only": True, "no_external_tools_executed": True, "no_fc_executed": True,
            "no_image_outputs_written": True, "previous_stage_outputs_not_modified": True,
            "no_full_preprocessing": True, "no_dpabi": True,
            "research_use_only": True, "clinical_use_prohibited": True}
