"""ALFF/ReHo Sandbox Execution Schema — Phase 5M."""
from __future__ import annotations
from pydantic import BaseModel, Field


class AlffRehoSandboxExecutionRequest(BaseModel):
    dry_run_id: str = ""; functional_input_dir: str = ""
    confirm_sandbox_copy: bool = False; confirm_no_rawdata_modification: bool = False
    confirm_previous_stage_readonly: bool = False; confirm_alff_reho_only: bool = False
    confirm_no_fc_execution: bool = False; confirm_no_full_preprocessing: bool = False
    confirm_research_use_only: bool = False
    preview_limit: int | None = Field(default=None, ge=1)
    timeout_seconds: int = 600


class AlffRehoSandboxExecutionResponse(BaseModel):
    ok: bool = False; status: str = "disabled"; project_id: str = ""
    preprocessing_run_id: str = ""; dry_run_id: str = ""; execution_id: str = ""
    execution_dir: str = ""; sandbox_input_dir: str = ""; sandbox_output_dir: str = ""
    subjects_total: int = 0; subjects_succeeded: int = 0; subjects_failed: int = 0
    subjects_partial: int = 0  # subjects where SOME but not ALL metrics succeeded
    # Dataset selection transparency (AGENTS Scientific Computing Contract).
    # When files_discovered > files_selected, only a preview subset was processed.
    files_discovered: int = 0
    files_selected: int = 0
    dataset_complete: bool = True
    metric_plan_path: str = ""; stdout_log_path: str = ""; stderr_log_path: str = ""
    manifest_path: str = ""; provenance_path: str = ""; subject_status_path: str = ""
    # Per-metric status (ExecutionStatus values). A false ``computed`` flag with
    # a non-numeric status means only a sandbox was prepared, not a real map.
    alff_computed: bool = False
    alff_status: str = "metadata_only"
    falff_computed: bool = False
    reho_computed: bool = False
    reho_status: str = "metadata_only"

    # Validation level (separate from execution status per AGENTS contract).
    # Property of the algorithm implementation, not of this run's outcome.
    # The formal service always uses the CPU ReHo backend (golden-validated).
    reho_validation_status: str = "golden_validated"
    # Backend used for ReHo computation, e.g. "none", "cpu-numpy", "gpu-cupy".
    reho_backend: str = "none"
    # Aggregate TR source: "bids_json", "default", or "mixed".
    # "default" means sidecar(s) were missing and 2.0s fallback was used.
    tr_source: str = "default"
    warnings: list[str] = Field(default_factory=list); errors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


_ALFF_REHO_REQUIRED_FLAGS = ["MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
                              "MEDIMAGE_ALLOW_SANDBOXED_ALFF_REHO"]


def validate_alff_reho_env(env: dict[str, str]) -> tuple[bool, list[str]]:
    missing = sorted(f for f in _ALFF_REHO_REQUIRED_FLAGS if env.get(f) != "1")
    return len(missing) == 0, missing


def alff_reho_exec_safety_flags() -> dict[str, bool]:
    return {"sandbox_execution_only": True, "rawdata_not_modified": True,
            "previous_stage_outputs_not_modified": True, "no_fc_execution": True,
            "no_group_statistics": True, "no_full_preprocessing": True, "no_dpabi": True,
            "no_shell_execution": True, "python_only": True, "alff_reho_only": True,
            "research_use_only": True, "clinical_use_prohibited": True}
