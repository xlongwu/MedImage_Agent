"""Preprocessing Pipeline Validation Schema — Phase 5O."""
from __future__ import annotations
from pydantic import BaseModel, Field


class PipelineValidationResponse(BaseModel):
    ok: bool = False; status: str = "not_started"; project_id: str = ""
    preprocessing_run_id: str = ""
    artifact_registry_path: str = ""
    stage_summary: list[dict] = Field(default_factory=list)
    completed_stages: list[str] = Field(default_factory=list)
    dry_run_only_stages: list[str] = Field(default_factory=list)
    sandbox_executed_stages: list[str] = Field(default_factory=list)
    registered_outputs: list[str] = Field(default_factory=list)
    metadata_only_stages: list[str] = Field(default_factory=list)
    preview_only_stages: list[str] = Field(default_factory=list)
    blocked_stages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


def validation_safety_flags() -> dict[str, bool]:
    return {"rawdata_not_modified": True, "converted_bids_not_modified": True,
            "no_dpabi_execution": True, "no_group_statistics": True,
            "no_classification": True, "no_clinical_diagnosis": True,
            "sandbox_execution_only": True, "research_use_only": True,
            "clinical_use_prohibited": True}
