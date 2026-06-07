"""Pipeline preset schemas — request/response models for preset APIs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PipelinePresetNode(BaseModel):
    id: str
    name: str
    stage: str
    backend: str = "contract"
    requires_approval: bool = False
    executable: bool = False
    description: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    safety_notes: list[str] = Field(default_factory=list)


class PipelinePreset(BaseModel):
    preset_id: str
    name: str
    modality: str
    description: str
    version: str
    nodes: list[PipelinePresetNode]
    non_goals: list[str] = Field(default_factory=list)
    readiness_requirements: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class PipelinePresetInstantiateRequest(BaseModel):
    goal: str | None = None
    include_optional_nodes: bool = False
    subject_scope: Literal["all", "sample"] = "sample"
    dry_run_only: bool = True


class PipelinePresetInstantiateResponse(BaseModel):
    ok: bool
    project_id: str
    preset_id: str
    plan: dict[str, Any]
    validation: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
