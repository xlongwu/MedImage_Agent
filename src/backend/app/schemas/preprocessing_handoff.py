"""Preprocessing Handoff Schema — Phase 5A."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class PreprocessingInputRegistrationRequest(BaseModel):
    conversion_run_id: str = ""
    converted_bids_dir: str | None = None
    mode: str = "reference"
    confirm_rawdata_readonly: bool = False
    confirm_use_converted_outputs: bool = False


class PreprocessingInputRegistrationResponse(BaseModel):
    ok: bool = False; status: str = "blocked"; project_id: str = ""
    conversion_run_id: str = ""; preprocessing_input_dir: str = ""; rawdata_dir: str = ""
    subject_count: int = 0; bold_count: int = 0; t1w_count: int = 0
    nifti_count: int = 0; sidecar_count: int = 0
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


class PreprocessingPlanPreviewResponse(BaseModel):
    ok: bool = False; status: str = "preview_only"; project_id: str = ""
    stages: list[PreprocessingStagePreview] = Field(default_factory=list)
    stage_count: int = 0; enabled_stage_count: int = 0
    execution_disabled: bool = True; preprocessing_input_registered: bool = False
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


_DPARSFA_STAGES: list[dict[str, Any]] = [
    {"stage_id": "input_validation", "name": "Input Validation", "backend": "python", "requires_external_tool": False, "optional": False},
    {"stage_id": "dummy_scan_removal", "name": "Dummy Scan Removal", "backend": "python", "requires_external_tool": False, "optional": False},
    {"stage_id": "slice_timing", "name": "Slice Timing Correction", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "realignment", "name": "Realignment", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "t1_coregistration", "name": "T1 Coregistration", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "segmentation", "name": "T1 Segmentation", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "normalization", "name": "Normalization to MNI", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "nuisance_regression", "name": "Nuisance Regression", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "temporal_filtering", "name": "Temporal Filtering", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "spatial_smoothing", "name": "Spatial Smoothing", "backend": "matlab", "requires_external_tool": True, "optional": False},
    {"stage_id": "alff_falff", "name": "ALFF / fALFF", "backend": "matlab", "requires_external_tool": True, "optional": True},
    {"stage_id": "reho", "name": "ReHo", "backend": "matlab", "requires_external_tool": True, "optional": True},
    {"stage_id": "functional_connectivity", "name": "Functional Connectivity", "backend": "matlab", "requires_external_tool": True, "optional": True},
    {"stage_id": "subject_qc", "name": "Subject QC", "backend": "python", "requires_external_tool": False, "optional": False},
    {"stage_id": "group_summary", "name": "Group Summary", "backend": "python", "requires_external_tool": False, "optional": False},
]


def build_default_dparsfa_style_plan(project_id: str = "", input_registered: bool = False) -> PreprocessingPlanPreviewResponse:
    stages: list[PreprocessingStagePreview] = []
    for s in _DPARSFA_STAGES:
        enabled = not s["requires_external_tool"]
        stages.append(PreprocessingStagePreview(stage_id=s["stage_id"], name=s["name"], backend=s["backend"], subject_level=True, requires_external_tool=s["requires_external_tool"], enabled=enabled, optional=s.get("optional", False), description=s.get("description", "")))
    enabled_count = sum(1 for s in stages if s.enabled)
    w = [] if input_registered else ["Preprocessing input has not been registered."]
    return PreprocessingPlanPreviewResponse(ok=True, status="preview_only", project_id=project_id, stages=stages, stage_count=len(stages), enabled_stage_count=enabled_count, execution_disabled=True, preprocessing_input_registered=input_registered, warnings=w, next_actions=["Register converted BIDS as preprocessing input.", "Enable MATLAB/SPM for external-tool stages."], safety_flags={"preview_only": True, "no_preprocessing_executed": True, "no_external_tools_executed": True, "spm_dpabi_matlab_disabled": True, "rawdata_read_only": True, "research_use_only": True})
