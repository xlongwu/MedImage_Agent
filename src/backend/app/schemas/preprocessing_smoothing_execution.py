"""Smoothing Sandbox Execution Schema — Phase 5J."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SmoothingSandboxExecutionRequest(BaseModel):
    dry_run_id: str = ""
    functional_input_dir: str = ""
    confirm_sandbox_copy: bool = False
    confirm_no_rawdata_modification: bool = False
    confirm_no_converted_input_modification: bool = False
    confirm_previous_stage_readonly: bool = False
    confirm_smoothing_only: bool = False
    confirm_no_full_preprocessing: bool = False
    confirm_research_use_only: bool = False
    matlab_executable: str = "matlab"
    spm_path: str = ""
    timeout_seconds: int = 600


class SmoothingSandboxExecutionResponse(BaseModel):
    ok: bool = False
    status: str = "disabled"
    project_id: str = ""
    preprocessing_run_id: str = ""
    dry_run_id: str = ""
    execution_id: str = ""
    execution_dir: str = ""
    sandbox_input_dir: str = ""
    sandbox_output_dir: str = ""
    subjects_total: int = 0
    subjects_succeeded: int = 0
    subjects_failed: int = 0
    command_template_path: str = ""
    batch_script_path: str = ""
    stdout_log_path: str = ""
    stderr_log_path: str = ""
    manifest_path: str = ""
    provenance_path: str = ""
    subject_status_path: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


_SMOOTHING_REQUIRED_FLAGS = [
    "MEDIMAGE_MATLAB_ENABLED",
    "MEDIMAGE_SPM_SMOKE_ENABLED",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
    "MEDIMAGE_ALLOW_SANDBOXED_SPM_PREPROCESSING",
    "MEDIMAGE_ALLOW_SANDBOXED_SPM_SMOOTHING",
]


def validate_smoothing_env(env: dict[str, str]) -> tuple[bool, list[str]]:
    missing = sorted(f for f in _SMOOTHING_REQUIRED_FLAGS if env.get(f) != "1")
    return len(missing) == 0, missing


def smoothing_safety_flags() -> dict[str, bool]:
    return {
        "sandbox_execution_only": True,
        "rawdata_not_modified": True,
        "converted_input_not_modified": True,
        "previous_stage_outputs_not_modified": True,
        "no_full_preprocessing": True,
        "no_dpabi": True,
        "no_shell_execution": True,
        "argv_list_only": True,
        "smoothing_only": True,
        "research_use_only": True,
        "clinical_use_prohibited": True,
    }
