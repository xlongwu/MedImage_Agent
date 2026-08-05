"""Preprocessing Pipeline Report Schema — Phase 5N."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PipelineReportResponse(BaseModel):
    ok: bool = False
    status: str = ""
    project_id: str = ""
    preprocessing_run_id: str = ""
    report_id: str = ""
    report_path: str = ""
    summary: str = ""
    artifact_registry_path: str = ""
    lineage_summary: dict[str, int] = Field(default_factory=dict)
    stage_statuses: list[dict] = Field(default_factory=list)
    registered_outputs: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
