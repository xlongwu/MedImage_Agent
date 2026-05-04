"""Pydantic models for advisor requests."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AdvisorRequest(BaseModel):
    advisor_type: str = Field(..., description="protocol | error | qc-report | parameters | docs-qa")
    input: dict = Field(default_factory=dict)
    save_to_memory: bool = False


class ProtocolRequest(BaseModel):
    modality: str = "rs-fMRI"
    task_goal: str = ""
    tr: float = 2.0
    slice_count: int = 32
    has_fieldmap: bool = False
    available_data: list[str] = Field(default_factory=lambda: ["T1w", "BOLD"])
    constraints: list[str] = Field(default_factory=list)


class ErrorRequest(BaseModel):
    error_message: str = ""
    node_id: str = ""
    backend: str = "python"
    error_category: str = "UNKNOWN_ERROR"
    subject_id: str = ""


class QCReportRequest(BaseModel):
    qc_data: dict = Field(default_factory=dict)
    subjects_total: int = 0
    subjects_passed: int = 0


class ParameterRequest(BaseModel):
    parameters: dict = Field(default_factory=dict)


class DocsQARequest(BaseModel):
    question: str = ""
    context_docs: list[str] = Field(default_factory=list)
