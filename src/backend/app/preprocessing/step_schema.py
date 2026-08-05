from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

BackendType = Literal[
    "python",
    "matlab-spm",
    "matlab-dpabi",
    "python-gpu",
    "report",
]

ParallelLevel = Literal[
    "project",
    "subject",
    "session",
    "run",
    "volume",
]

StepCategory = Literal[
    "data_inspection",
    "spm_preprocessing",
    "dpabi_preprocessing",
    "python_qc",
    "gpu_candidate",
    "reporting",
]


@dataclass(frozen=True)
class PreprocessingStepSpec:
    step_id: str
    name: str
    category: StepCategory
    backend: BackendType
    description: str
    inputs: list[str]
    outputs: list[str]
    parameters: dict[str, Any]
    depends_on: list[str]
    parallel_level: ParallelLevel
    gpu_supported: bool
    matlab_required: bool
    approval_required: bool
    cacheable: bool
    qc_metrics: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    diagnostic_hints: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)


def step_to_dict(step: PreprocessingStepSpec) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "name": step.name,
        "category": step.category,
        "backend": step.backend,
        "description": step.description,
        "inputs": step.inputs,
        "outputs": step.outputs,
        "parameters": step.parameters,
        "depends_on": step.depends_on,
        "parallel_level": step.parallel_level,
        "gpu_supported": step.gpu_supported,
        "matlab_required": step.matlab_required,
        "approval_required": step.approval_required,
        "cacheable": step.cacheable,
        "qc_metrics": step.qc_metrics,
        "failure_modes": step.failure_modes,
        "diagnostic_hints": step.diagnostic_hints,
        "safety_notes": step.safety_notes,
    }
