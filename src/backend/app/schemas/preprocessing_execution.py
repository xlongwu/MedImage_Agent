"""Preprocessing Execution Schema — Phase 4A.

Defines preprocessing stage types, input/output kinds, external tool kinds,
plan models, stage config models, execution models, and pure helper functions
for the DPARSFA-style rs-fMRI preprocessing pipeline.

Schema-only module.  No runtime executor is imported or modified.
No file I/O.  No external-tool execution is enabled.

Reference:
  docs/REAL_PREPROCESSING_EXECUTION_CONTRACT.md
  docs/PIPELINE_EXECUTOR_PRODUCTIZATION_CONTRACT.md
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════
# 1. Literal type aliases
# ═══════════════════════════════════════════════════════════════════════

PreprocessingStage = Literal[
    "dicom_to_nifti",
    "bids_organization",
    "remove_initial_volumes",
    "slice_timing",
    "realignment",
    "t1_coregistration",
    "t1_segmentation",
    "normalization",
    "nuisance_regression",
    "temporal_filtering",
    "spatial_smoothing",
    "alff_falff",
    "reho",
    "functional_connectivity",
    "subject_qc",
    "group_summary",
    "derivative_summary",
]

PreprocessingStageStatus = Literal[
    "pending",
    "skipped",
    "ready",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "unknown",
]

PreprocessingInputKind = Literal[
    "dicom_dir",
    "nifti_bold",
    "nifti_t1w",
    "nifti_tissue_map",
    "motion_params",
    "realigned_bold",
    "normalised_bold",
    "smoothed_bold",
    "alff_map",
    "falff_map",
    "reho_map",
    "fc_map",
    "sidecar_json",
    "pipeline_config",
    "dataset_index",
]

PreprocessingOutputKind = Literal[
    "nifti_bold",
    "nifti_t1w",
    "nifti_tissue_map_c1",
    "nifti_tissue_map_c2",
    "nifti_tissue_map_c3",
    "nifti_realigned",
    "nifti_mean",
    "nifti_coregistered",
    "nifti_normalised",
    "nifti_smoothed",
    "nifti_alff",
    "nifti_falff",
    "nifti_reho",
    "nifti_fc",
    "motion_params_txt",
    "qc_report_json",
    "qc_report_markdown",
    "group_summary_csv",
    "derivative_manifest_json",
    "sidecar_json",
    "stdout_log",
    "stderr_log",
    "provenance_json",
    "node_state_json",
    "output_manifest_json",
]

ExternalToolKind = Literal[
    "dcm2niix",
    "matlab",
    "spm12",
    "dpabi",
    "none",
]

# ═══════════════════════════════════════════════════════════════════════
# 2. Stage metadata maps
# ═══════════════════════════════════════════════════════════════════════

# Which stages require an external tool (dcm2niix, MATLAB, SPM, DPABI).
_EXTERNAL_TOOL_STAGES: frozenset[PreprocessingStage] = frozenset({
    "dicom_to_nifti",
    "slice_timing",
    "realignment",
    "t1_coregistration",
    "t1_segmentation",
    "normalization",
    "nuisance_regression",
    "temporal_filtering",
    "spatial_smoothing",
    "alff_falff",
    "reho",
    "functional_connectivity",
})

# Which stages are pure Python (no external tool).
_PYTHON_ONLY_STAGES: frozenset[PreprocessingStage] = frozenset({
    "bids_organization",
    "subject_qc",
    "group_summary",
    "derivative_summary",
})

# Which stages require explicit approval (all external-tool stages).
_APPROVAL_REQUIRED_STAGES: frozenset[PreprocessingStage] = _EXTERNAL_TOOL_STAGES

# Which stages are project-level (not subject-level).
_PROJECT_LEVEL_STAGES: frozenset[PreprocessingStage] = frozenset({
    "bids_organization",
    "group_summary",
    "derivative_summary",
})

# Which stages are subject-level.
_SUBJECT_LEVEL_STAGES: frozenset[PreprocessingStage] = frozenset({
    "dicom_to_nifti",
    "remove_initial_volumes",
    "slice_timing",
    "realignment",
    "t1_coregistration",
    "t1_segmentation",
    "normalization",
    "nuisance_regression",
    "temporal_filtering",
    "spatial_smoothing",
    "alff_falff",
    "reho",
    "functional_connectivity",
    "subject_qc",
})

# External tool kind per stage.
_STAGE_EXTERNAL_TOOL: dict[PreprocessingStage, ExternalToolKind] = {
    "dicom_to_nifti": "dcm2niix",
    "slice_timing": "spm12",
    "realignment": "spm12",
    "t1_coregistration": "spm12",
    "t1_segmentation": "spm12",
    "normalization": "spm12",
    "nuisance_regression": "dpabi",
    "temporal_filtering": "dpabi",
    "spatial_smoothing": "dpabi",
    "alff_falff": "dpabi",
    "reho": "dpabi",
    "functional_connectivity": "dpabi",
}

# The canonical DPARSFA-style stage order.
_DPARSFA_STAGE_ORDER: tuple[PreprocessingStage, ...] = (
    "dicom_to_nifti",
    "bids_organization",
    "remove_initial_volumes",
    "slice_timing",
    "realignment",
    "t1_segmentation",
    "t1_coregistration",
    "normalization",
    "nuisance_regression",
    "temporal_filtering",
    "spatial_smoothing",
    "alff_falff",
    "reho",
    "functional_connectivity",
    "subject_qc",
    "group_summary",
    "derivative_summary",
)

# Optional stages that can be excluded from a plan.
_OPTIONAL_STAGES: frozenset[PreprocessingStage] = frozenset({
    "alff_falff",
    "reho",
    "functional_connectivity",
})

# Maximum allowed PreprocessingStage values (for validation).
ALL_PREPROCESSING_STAGES: frozenset[PreprocessingStage] = frozenset(
    _DPARSFA_STAGE_ORDER
)

# ═══════════════════════════════════════════════════════════════════════
# 3. Pydantic models
# ═══════════════════════════════════════════════════════════════════════

class PreprocessingStageConfig(BaseModel):
    """Configuration for a single preprocessing stage."""

    stage: PreprocessingStage
    enabled: bool = True
    external_tool: ExternalToolKind = "none"
    requires_approval: bool = False
    params: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 3600
    stop_on_failure: bool = True
    overwrite_policy: str = "fail_if_exists"


class PreprocessingSubjectPlan(BaseModel):
    """Per-subject preprocessing execution plan."""

    subject_id: str
    stages: list[PreprocessingStageConfig] = Field(default_factory=list)
    input_dicom_dir: str | None = None
    output_root: str | None = None


class PreprocessingPlan(BaseModel):
    """Complete preprocessing pipeline plan for a project."""

    project_id: str
    pipeline_name: str = "dparsfa_style"
    subjects: list[PreprocessingSubjectPlan] = Field(default_factory=list)
    stages: list[PreprocessingStageConfig] = Field(default_factory=list)
    global_params: dict[str, Any] = Field(default_factory=dict)
    optional_stages_enabled: list[PreprocessingStage] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class PreprocessingExecutionRequest(BaseModel):
    """Request to execute a preprocessing pipeline."""

    project_id: str
    reviewed_plan_id: str
    plan: PreprocessingPlan | None = None
    dry_run: bool = True
    approved: bool = False
    approved_by: str | None = None
    env_flags: dict[str, str] = Field(default_factory=dict)
    subjects: list[str] = Field(default_factory=list)
    actor: str = "frontend-user"


class PreprocessingExecutionPreview(BaseModel):
    """Preview of what would happen during preprocessing execution."""

    project_id: str
    would_execute: bool
    dry_run: bool = True
    stage_count: int = 0
    subject_count: int = 0
    external_tool_stages: list[PreprocessingStage] = Field(default_factory=list)
    approval_required_stages: list[PreprocessingStage] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    estimated_duration_seconds: int | None = None
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class PreprocessingSafetyFlags(BaseModel):
    """Safety flags for preprocessing execution."""

    rawdata_read_only: bool = True
    no_external_tools_without_approval: bool = True
    no_rawdata_modification: bool = True
    dry_run_only: bool = True
    research_use_only: bool = True
    clinical_use_prohibited: bool = True
    conversion_disabled: bool = True
    spm_execution_disabled: bool = True
    dpabi_execution_disabled: bool = True
    matlab_execution_disabled: bool = True


# ═══════════════════════════════════════════════════════════════════════
# 4. Pure helper functions
# ═══════════════════════════════════════════════════════════════════════

def is_external_tool_stage(stage: PreprocessingStage) -> bool:
    """Return True if *stage* requires an external tool (dcm2niix/SPM/DPABI)."""
    return stage in _EXTERNAL_TOOL_STAGES


def is_python_only_stage(stage: PreprocessingStage) -> bool:
    """Return True if *stage* is pure Python (no external tool)."""
    return stage in _PYTHON_ONLY_STAGES


def requires_approval(stage: PreprocessingStage) -> bool:
    """Return True if *stage* requires explicit user approval before execution."""
    return stage in _APPROVAL_REQUIRED_STAGES


def requires_rawdata_readonly(stage: PreprocessingStage) -> bool:
    """Return True — all preprocessing stages must keep rawdata read-only.

    This always returns True because the rawdata read-only invariant is
    universal.  No stage, regardless of backend, may modify rawdata.
    """
    return True


def is_subject_level_stage(stage: PreprocessingStage) -> bool:
    """Return True if *stage* operates per-subject (not project-level)."""
    return stage in _SUBJECT_LEVEL_STAGES


def is_project_level_stage(stage: PreprocessingStage) -> bool:
    """Return True if *stage* operates at the project level."""
    return stage in _PROJECT_LEVEL_STAGES


def get_external_tool(stage: PreprocessingStage) -> ExternalToolKind:
    """Return the external tool kind for *stage*, or ``"none"``."""
    return _STAGE_EXTERNAL_TOOL.get(stage, "none")


def is_stage_optional(stage: PreprocessingStage) -> bool:
    """Return True if *stage* can be excluded from a preprocessing plan."""
    return stage in _OPTIONAL_STAGES


def get_canonical_stage_order() -> tuple[PreprocessingStage, ...]:
    """Return the canonical DPARSFA-style preprocessing stage order."""
    return _DPARSFA_STAGE_ORDER


def is_preprocessing_stage_order_valid(
    stages: list[PreprocessingStage],
) -> bool:
    """Return True if *stages* respects the canonical DPARSFA order.

    Stages may be a subset (some optional stages omitted), but their
    relative order must match the canonical sequence.  Unknown stage
    values cause the function to return False.
    """
    canonical = _DPARSFA_STAGE_ORDER
    # Build index lookup for canonical positions
    canonical_index: dict[PreprocessingStage, int] = {
        s: i for i, s in enumerate(canonical)
    }
    last_index = -1
    for stage in stages:
        idx = canonical_index.get(stage)
        if idx is None:
            return False  # Unknown stage
        if idx < last_index:
            return False  # Out of order
        last_index = idx
    return True


def build_default_dparsfa_style_plan(
    subjects: list[str],
    *,
    project_id: str = "",
    include_optional: bool = False,
    **options: Any,
) -> PreprocessingPlan:
    """Build a default DPARSFA-style preprocessing plan for *subjects*.

    All required stages are included.  Optional stages (ALFF/fALFF, ReHo,
    FC) are included only when ``include_optional=True`` or individually
    enabled via ``**options``.

    Pure function — no file I/O, no external tool checks, no path resolution.
    """
    stage_configs: list[PreprocessingStageConfig] = []
    for stage in _DPARSFA_STAGE_ORDER:
        if is_stage_optional(stage) and not include_optional:
            opt_key = f"include_{stage}"
            if not options.get(opt_key, False):
                continue

        stage_configs.append(
            PreprocessingStageConfig(
                stage=stage,
                enabled=True,
                external_tool=get_external_tool(stage),
                requires_approval=requires_approval(stage),
                params={},
            )
        )

    subject_plans: list[PreprocessingSubjectPlan] = [
        PreprocessingSubjectPlan(subject_id=sid, stages=stage_configs)
        for sid in subjects
    ]

    return PreprocessingPlan(
        project_id=project_id,
        pipeline_name="dparsfa_style",
        subjects=subject_plans,
        stages=stage_configs,
        optional_stages_enabled=[
            s for s in _OPTIONAL_STAGES if include_optional
        ],
        safety_flags=PreprocessingSafetyFlags().model_dump(),
    )


def validate_preprocessing_env_flags(
    env_flags: dict[str, str],
) -> tuple[bool, list[str]]:
    """Check whether required env flags are set for real preprocessing.

    Returns ``(all_set, missing_flags)``.  All four flags must be ``"1"``
    for real execution.  Pure function — no subprocess, no file I/O.
    """
    required = {
        "MEDIMAGE_MATLAB_ENABLED",
        "MEDIMAGE_SPM_SMOKE_ENABLED",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
    }
    missing = [f for f in sorted(required) if env_flags.get(f) != "1"]
    return len(missing) == 0, missing
