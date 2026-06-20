"""FC Sandbox Execution Schema — Phase 5N."""
from __future__ import annotations
from pydantic import BaseModel, Field


class FcSandboxExecutionRequest(BaseModel):
    dry_run_id: str = ""; functional_input_dir: str = ""
    confirm_sandbox_copy: bool = False; confirm_no_rawdata_modification: bool = False
    confirm_previous_stage_readonly: bool = False; confirm_fc_only: bool = False
    confirm_no_group_statistics: bool = False; confirm_no_classification: bool = False
    confirm_no_full_preprocessing: bool = False; confirm_research_use_only: bool = False
    timeout_seconds: int = 600


class FcSandboxExecutionResponse(BaseModel):
    ok: bool = False; status: str = "disabled"; project_id: str = ""
    preprocessing_run_id: str = ""; dry_run_id: str = ""; execution_id: str = ""
    execution_dir: str = ""; sandbox_input_dir: str = ""; sandbox_output_dir: str = ""
    subjects_total: int = 0; subjects_succeeded: int = 0; subjects_failed: int = 0
    fc_plan_path: str = ""; stdout_log_path: str = ""; stderr_log_path: str = ""
    manifest_path: str = ""; provenance_path: str = ""; subject_status_path: str = ""
    # Per-metric status so callers can distinguish "sandbox prepared" from
    # "real matrix produced". ``fc_status`` is one of the ExecutionStatus values
    # (see preprocessing_common). A false ``fc_computed`` means no real matrix.
    fc_computed: bool = False
    fc_status: str = "metadata_only"
    fc_matrix_count: int = 0
    warnings: list[str] = Field(default_factory=list); errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


_FC_REQUIRED_FLAGS = ["MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "MEDIMAGE_ALLOW_SANDBOXED_FC"]


def validate_fc_env(env: dict[str, str]) -> tuple[bool, list[str]]:
    missing = sorted(f for f in _FC_REQUIRED_FLAGS if env.get(f) != "1")
    return len(missing) == 0, missing


def fc_exec_safety_flags() -> dict[str, bool]:
    return {"sandbox_execution_only": True, "rawdata_not_modified": True,
            "previous_stage_outputs_not_modified": True, "no_group_statistics": True,
            "no_classification": True, "no_full_preprocessing": True, "no_dpabi": True,
            "no_shell_execution": True, "python_only": True, "fc_only": True,
            "research_use_only": True, "clinical_use_prohibited": True}
