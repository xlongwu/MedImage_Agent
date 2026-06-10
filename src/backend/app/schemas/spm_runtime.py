"""SPM Runtime Schema — Phase 5C."""
from __future__ import annotations
from pydantic import BaseModel, Field


class SpmRuntimePreflightResponse(BaseModel):
    ok: bool = False; status: str = "disabled"; project_id: str = ""
    matlab_available: bool = False; matlab_executable: str = ""
    matlab_version: str = ""
    spm_available: bool = False; spm_path: str = ""; spm_version: str = ""
    required_env_flags: list[str] = Field(default_factory=list)
    missing_env_flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class SpmSyntheticSmokeRequest(BaseModel):
    confirm_synthetic_only: bool = False
    confirm_no_user_rawdata: bool = False
    confirm_no_full_preprocessing: bool = False
    confirm_research_use_only: bool = False
    matlab_executable: str = "matlab"
    spm_path: str = ""


class SpmSyntheticSmokeResponse(BaseModel):
    ok: bool = False; status: str = "disabled"; project_id: str = ""
    smoke_run_id: str = ""; smoke_dir: str = ""
    synthetic_input_path: str = ""; synthetic_output_dir: str = ""
    command_template_path: str = ""; batch_script_path: str = ""
    stdout_log_path: str = ""; stderr_log_path: str = ""
    manifest_path: str = ""; provenance_path: str = ""
    completed_steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


_REQUIRED_SYNTHETIC_SPM_FLAGS = [
    "MEDIMAGE_MATLAB_ENABLED", "MEDIMAGE_SPM_SMOKE_ENABLED",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
    "MEDIMAGE_ALLOW_SYNTHETIC_SPM_PREPROCESSING_SMOKE",
]


def validate_synthetic_spm_env(env: dict[str, str]) -> tuple[bool, list[str]]:
    missing = sorted(f for f in _REQUIRED_SYNTHETIC_SPM_FLAGS if env.get(f) != "1")
    return len(missing) == 0, missing


def safety_flags_spm() -> dict[str, bool]:
    return {"spm_execution_disabled_by_default": True, "matlab_execution_disabled_by_default": True,
            "synthetic_only": True, "no_user_rawdata_execution": True,
            "no_full_preprocessing": True, "no_dpabi_execution": True,
            "rawdata_not_modified": True, "research_use_only": True, "clinical_use_prohibited": True}
