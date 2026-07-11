"""API schemas for the native full preprocessing workflow."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


NativeFullRunStatus = Literal[
    "planned",
    "succeeded",
    "partial",
    "blocked",
    "failed",
]


class NativeFullPreprocConfirmations(BaseModel):
    confirm_reviewed_native_execution: bool = False
    confirm_rawdata_readonly: bool = False
    confirm_no_external_tools: bool = False
    confirm_research_use_only: bool = False
    confirm_no_clinical_use: bool = False


class NativeFullPreprocRequest(BaseModel):
    run_id: str = ""
    subject_id: str = ""
    session_id: str = ""
    output_dir: str = ""

    input_bold: str = ""
    sidecar_json: str = ""
    t1w: str = ""
    template: str = ""
    atlas: str = ""
    atlas_labels: str = ""
    conversion_run_id: str = ""
    dparsf_config: dict[str, Any] = Field(default_factory=dict)
    stage_overrides: dict[str, bool] = Field(default_factory=dict)

    remove_first: int = 0
    enable_slice_timing: bool = True
    reference_time: float | None = None
    reference_slice_index: int | None = None
    reference_volume_index: int = 0
    fd_threshold_mm: float = 0.5
    head_radius_mm: float = 50.0
    fwhm_mm: float | list[float] = 6.0
    include_wm: bool = True
    include_csf: bool = True
    include_global_signal: bool = False
    polynomial_order: int = 1
    temporal_filter_type: str = "band-pass"
    low_hz: float | None = 0.01
    high_hz: float | None = 0.08
    tr: float | None = None
    filtering_method: str = "fft"
    reho_neighborhood: int = 27
    atlas_name: str = "custom"

    confirmations: NativeFullPreprocConfirmations = Field(
        default_factory=NativeFullPreprocConfirmations
    )


class NativeFullStageApiResult(BaseModel):
    stage_id: str
    display_name: str = ""
    node_id: str = ""
    status: str
    capability_level: str = ""
    validation_status: str = ""
    backend: str = "native_python"
    input_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    output_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)


class NativeFullPreprocResponse(BaseModel):
    ok: bool = False
    status: NativeFullRunStatus = "blocked"
    dry_run: bool = False
    project_id: str = ""
    run_id: str = ""
    run_dir: str = ""
    backend: str = "native_python"
    stage_graph: list[dict[str, Any]] = Field(default_factory=list)
    stage_results: list[NativeFullStageApiResult] = Field(default_factory=list)
    completed_stages: list[str] = Field(default_factory=list)
    blocked_stages: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    skipped_stages: list[str] = Field(default_factory=list)
    metadata_only_stages: list[str] = Field(default_factory=list)
    warning_stages: list[str] = Field(default_factory=list)
    artifact_count: int = 0
    manifest_path: str = ""
    validation_report_path: str = ""
    final_report_path: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


__all__ = [
    "NativeFullPreprocConfirmations",
    "NativeFullPreprocRequest",
    "NativeFullPreprocResponse",
    "NativeFullRunStatus",
    "NativeFullStageApiResult",
]
