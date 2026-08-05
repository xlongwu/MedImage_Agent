"""Unified preprocessing stage catalog.

This module is schema/data only. It centralizes preprocessing stage metadata so
plan previews, run status, reports, validation, and frontend contracts do not
drift into separate capability truths.
"""
from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, Field

PreprocessingStageExecutionStatus = Literal[
    "not_started",
    "planned",
    "review_required",
    "blocked",
    "running",
    "succeeded",
    "partial",
    "metadata_only",
    "failed",
    "skipped",
    "preview_only",
]

PreprocessingCapabilityStatus = Literal[
    "unavailable",
    "scaffolded",
    "metadata_only",
    "computed",
    "validated",
]


PREPROCESSING_STAGE_STATUS_VALUES: tuple[PreprocessingStageExecutionStatus, ...] = (
    "not_started",
    "planned",
    "review_required",
    "blocked",
    "running",
    "succeeded",
    "partial",
    "metadata_only",
    "failed",
    "skipped",
    "preview_only",
)

CAPABILITY_STATUS_VALUES: tuple[PreprocessingCapabilityStatus, ...] = (
    "unavailable",
    "scaffolded",
    "metadata_only",
    "computed",
    "validated",
)


SPM_STAGE_ENV_FLAGS = [
    "MEDIMAGE_MATLAB_ENABLED",
    "MEDIMAGE_SPM_SMOKE_ENABLED",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
    "MEDIMAGE_ALLOW_SANDBOXED_SPM_PREPROCESSING",
]
SPM_COREG_NORM_ENV_FLAGS = [*SPM_STAGE_ENV_FLAGS, "MEDIMAGE_ALLOW_SANDBOXED_SPM_COREG_NORM"]
SPM_SMOOTHING_ENV_FLAGS = [*SPM_STAGE_ENV_FLAGS, "MEDIMAGE_ALLOW_SANDBOXED_SPM_SMOOTHING"]

LEGACY_STAGE_ALIASES: dict[str, set[str]] = {
    "slice_timing": {"slice_timing", "slice_timing_realign", "slice-timing", "dry_run_manifest"},
    "realignment": {"realignment", "realign", "slice_timing_realign", "slice-timing-realign", "dry_run_manifest"},
    "t1_coregistration": {"t1_coregistration", "coregistration", "coreg_norm", "coreg-norm"},
    "segmentation": {"segmentation", "coreg_norm", "coreg-norm"},
    "normalization": {"normalization", "coreg_norm", "coreg-norm"},
    "spatial_smoothing": {"spatial_smoothing", "smoothing"},
    "alff_falff": {"alff_falff", "alff_reho", "alff-reho"},
    "reho": {"reho", "alff_reho", "alff-reho"},
    "temporal_filtering": {"temporal_filtering", "filtering"},
    "functional_connectivity": {"functional_connectivity", "fc"},
    "nuisance_regression": {"nuisance_regression", "nuisance"},
}

LEGACY_DRY_RUN_MANIFESTS: dict[str, set[str]] = {
    "slice_timing": {"dry_run_manifest.json"},
    "realignment": {"dry_run_manifest.json"},
    "t1_coregistration": {"coreg_norm_dry_run_manifest.json"},
    "segmentation": {"coreg_norm_dry_run_manifest.json"},
    "normalization": {"coreg_norm_dry_run_manifest.json"},
    "spatial_smoothing": {"smoothing_dry_run_manifest.json"},
    "nuisance_regression": {"nuisance_dry_run_manifest.json"},
    "temporal_filtering": {"filtering_dry_run_manifest.json"},
    "alff_falff": {"alff_reho_dry_run_manifest.json"},
    "reho": {"alff_reho_dry_run_manifest.json"},
    "functional_connectivity": {"fc_dry_run_manifest.json"},
}


class PreprocessingStageSpec(BaseModel):
    stage_id: str
    display_name: str
    category: str
    default_enabled: bool
    required_for_fc: bool
    optional: bool
    depends_on: list[str] = Field(default_factory=list)
    input_artifact_types: list[str] = Field(default_factory=list)
    optional_input_artifact_types: list[str] = Field(default_factory=list)
    output_artifact_types: list[str] = Field(default_factory=list)
    supported_backends: list[str] = Field(default_factory=list)
    default_backend: str
    requires_external_tool: bool
    requires_approval: bool
    requires_env_flags: list[str] = Field(default_factory=list)
    can_run_in_ci: bool
    scientific_status: PreprocessingCapabilityStatus
    validation_status: str
    subject_level: bool = True
    initial_status: PreprocessingStageExecutionStatus = "not_started"
    prerequisite_notes: list[str] = Field(default_factory=list)
    description: str = ""


PREPROCESSING_STAGE_CATALOG: tuple[PreprocessingStageSpec, ...] = (
    PreprocessingStageSpec(
        stage_id="input_validation",
        display_name="Input Validation",
        category="input",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        input_artifact_types=["converted_bold", "converted_t1w", "sidecar_json"],
        output_artifact_types=["input_inventory", "qc_json"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="metadata_only",
        validation_status="metadata_contract_tested",
        initial_status="not_started",
        description="Discover registered BIDS/NIfTI inputs and subject/session coverage.",
    ),
    PreprocessingStageSpec(
        stage_id="dummy_scan_removal",
        display_name="Dummy Scan Removal",
        category="temporal_preprocessing",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        input_artifact_types=["converted_bold"],
        output_artifact_types=["dummy_removed_bold"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="scaffolded",
        validation_status="planned_not_computed",
        initial_status="planned",
        description="Planned stage; no image-transform output is produced by Python preflight.",
    ),
    PreprocessingStageSpec(
        stage_id="slice_timing",
        display_name="Slice Timing Correction",
        category="temporal_preprocessing",
        default_enabled=False,
        required_for_fc=False,
        optional=True,
        input_artifact_types=["dummy_removed_bold", "converted_bold", "sidecar_json"],
        output_artifact_types=["slice_timing_corrected_bold", "stage_manifest"],
        supported_backends=["native_python", "spm12"],
        default_backend="native_python",
        requires_external_tool=False,
        requires_approval=False,
        requires_env_flags=[],
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="native_synthetic_tested_reference_pending",
        initial_status="skipped",
        description="Native Python slice-timing stage; external SPM remains available only by explicit gated backend selection.",
    ),
    PreprocessingStageSpec(
        stage_id="realignment",
        display_name="Realignment",
        category="motion",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        input_artifact_types=["slice_timing_corrected_bold", "dummy_removed_bold", "converted_bold"],
        output_artifact_types=["realigned_bold", "mean_bold", "motion_parameters", "qc_json"],
        supported_backends=["native_python", "spm12"],
        default_backend="native_python",
        requires_external_tool=False,
        requires_approval=False,
        requires_env_flags=[],
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="native_simplified_reference_pending",
        initial_status="planned",
        description="Native Python translation-only realignment is the default; external SPM realignment remains explicit and approval-gated.",
    ),
    PreprocessingStageSpec(
        stage_id="t1_coregistration",
        display_name="T1 Coregistration",
        category="spatial_preprocessing",
        default_enabled=False,
        required_for_fc=False,
        optional=True,
        depends_on=["realignment"],
        input_artifact_types=["mean_bold", "converted_t1w"],
        output_artifact_types=["coregistered_t1w", "stage_manifest", "qc_json"],
        supported_backends=["native_python", "spm12"],
        default_backend="native_python",
        requires_external_tool=False,
        requires_approval=False,
        requires_env_flags=[],
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="native_simplified_reference_pending",
        initial_status="skipped",
        prerequisite_notes=["Requires a mean functional reference and a T1w anatomical input."],
        description="Optional native Python coregistration; not required for native-space FC. External SPM is explicit and gated.",
    ),
    PreprocessingStageSpec(
        stage_id="segmentation",
        display_name="T1 Segmentation",
        category="spatial_preprocessing",
        default_enabled=False,
        required_for_fc=False,
        optional=True,
        depends_on=["t1_coregistration"],
        input_artifact_types=["converted_t1w", "coregistered_t1w"],
        output_artifact_types=["segmentation_maps", "stage_manifest", "qc_json"],
        supported_backends=["native_python", "spm12"],
        default_backend="native_python",
        requires_external_tool=False,
        requires_approval=False,
        requires_env_flags=[],
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="native_simplified_reference_pending",
        initial_status="skipped",
        prerequisite_notes=[
            "Required before enabling WM/CSF nuisance regressors.",
            "Required before SPM normalization deformation-based workflows.",
        ],
        description="Optional native Python intensity-kmeans segmentation; SPM unified segmentation remains explicit and gated.",
    ),
    PreprocessingStageSpec(
        stage_id="normalization",
        display_name="Normalization to MNI",
        category="spatial_preprocessing",
        default_enabled=False,
        required_for_fc=False,
        optional=True,
        depends_on=["segmentation"],
        input_artifact_types=["realigned_bold", "segmentation_maps"],
        output_artifact_types=["normalized_bold", "stage_manifest", "qc_json"],
        supported_backends=["native_python", "spm12"],
        default_backend="native_python",
        requires_external_tool=False,
        requires_approval=False,
        requires_env_flags=[],
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="native_affine_only_reference_pending",
        initial_status="skipped",
        prerequisite_notes=["Required before MNI-atlas functional connectivity workflows."],
        description="Optional native Python affine normalization; nonlinear SPM normalization remains explicit and gated.",
    ),
    PreprocessingStageSpec(
        stage_id="spatial_smoothing",
        display_name="Spatial Smoothing",
        category="spatial_preprocessing",
        default_enabled=False,
        required_for_fc=False,
        optional=True,
        depends_on=["normalization"],
        input_artifact_types=["normalized_bold"],
        optional_input_artifact_types=["realigned_bold"],
        output_artifact_types=["smoothed_bold", "stage_manifest", "qc_json"],
        supported_backends=["native_python", "spm12"],
        default_backend="native_python",
        requires_external_tool=False,
        requires_approval=False,
        requires_env_flags=[],
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="native_synthetic_tested_reference_pending",
        initial_status="skipped",
        prerequisite_notes=[
            "Optional for Minimal FC; FC input must be selected by configuration.",
            "ReHo is usually computed before smoothing unless configuration states otherwise.",
        ],
        description="Optional native Python smoothing; external SPM smoothing remains explicit and gated.",
    ),
    PreprocessingStageSpec(
        stage_id="nuisance_regression",
        display_name="Nuisance Regression",
        category="denoising",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        depends_on=["realignment"],
        input_artifact_types=["realigned_bold", "motion_parameters"],
        optional_input_artifact_types=["segmentation_maps"],
        output_artifact_types=["confounds_tsv", "denoised_bold", "stage_manifest", "qc_json"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="sandbox_and_unit_tested",
        initial_status="planned",
        prerequisite_notes=["WM/CSF regressors require a completed segmentation stage."],
        description="Python runner/kernel exists; missing prerequisites must block execution.",
    ),
    PreprocessingStageSpec(
        stage_id="temporal_filtering",
        display_name="Temporal Filtering",
        category="denoising",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        depends_on=["nuisance_regression"],
        input_artifact_types=["denoised_bold", "sidecar_json"],
        output_artifact_types=["filtered_bold", "stage_manifest", "qc_json"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="sandbox_and_unit_tested",
        initial_status="planned",
        description="Python filtering is available; TR must be explicit or derived from metadata.",
    ),
    PreprocessingStageSpec(
        stage_id="alff_falff",
        display_name="ALFF / fALFF",
        category="derived_metric",
        default_enabled=False,
        required_for_fc=False,
        optional=True,
        depends_on=["temporal_filtering"],
        input_artifact_types=["filtered_bold"],
        output_artifact_types=["alff_map", "falff_map", "stage_manifest", "qc_json"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="sandbox_and_unit_tested",
        initial_status="skipped",
        prerequisite_notes=["ALFF/fALFF requires a real TR source or explicit fallback TR."],
        description="Python metric runner exists; this remains optional for Minimal FC.",
    ),
    PreprocessingStageSpec(
        stage_id="reho",
        display_name="ReHo",
        category="derived_metric",
        default_enabled=False,
        required_for_fc=False,
        optional=True,
        depends_on=["temporal_filtering"],
        input_artifact_types=["filtered_bold"],
        output_artifact_types=["reho_map", "stage_manifest", "qc_json"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="sandbox_and_unit_tested",
        initial_status="skipped",
        prerequisite_notes=["Compute ReHo before smoothing unless the selected profile explicitly differs."],
        description="Python metric runner exists; this remains optional for Minimal FC.",
    ),
    PreprocessingStageSpec(
        stage_id="functional_connectivity",
        display_name="Functional Connectivity",
        category="connectivity",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        depends_on=["temporal_filtering"],
        input_artifact_types=["filtered_bold", "atlas"],
        output_artifact_types=["atlas", "roi_labels", "roi_timeseries", "fc_matrix", "fisher_z_matrix", "stage_manifest", "qc_json"],
        supported_backends=["python", "gpu"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="computed",
        validation_status="sandbox_and_unit_tested_atlas_grounding_pending",
        initial_status="planned",
        prerequisite_notes=[
            "Native or matched atlas mode does not require normalization.",
            "MNI atlas mode requires successful normalization first.",
        ],
        description="Python/GPU FC exists; synthetic atlas output must remain preview_only.",
    ),
    PreprocessingStageSpec(
        stage_id="subject_qc",
        display_name="Subject QC",
        category="qc",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        input_artifact_types=["input_inventory", "motion_parameters", "fc_matrix"],
        output_artifact_types=["qc_json", "stage_manifest"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="metadata_only",
        validation_status="metadata_contract_tested",
        initial_status="not_started",
        description="Metadata/QC summary stage; does not imply numerical preprocessing success.",
    ),
    PreprocessingStageSpec(
        stage_id="group_summary",
        display_name="Group Summary",
        category="reporting",
        default_enabled=True,
        required_for_fc=True,
        optional=False,
        input_artifact_types=["qc_json", "fc_matrix"],
        output_artifact_types=["pipeline_report"],
        supported_backends=["python"],
        default_backend="python",
        requires_external_tool=False,
        requires_approval=False,
        can_run_in_ci=True,
        scientific_status="metadata_only",
        validation_status="metadata_contract_tested",
        initial_status="not_started",
        description="Project-level summary/reporting stage.",
        subject_level=False,
    ),
)

PREPROCESSING_STAGE_ORDER: tuple[str, ...] = tuple(
    spec.stage_id for spec in PREPROCESSING_STAGE_CATALOG
)
_CATALOG_BY_ID = {spec.stage_id: spec for spec in PREPROCESSING_STAGE_CATALOG}


def iter_preprocessing_stage_specs() -> tuple[PreprocessingStageSpec, ...]:
    return PREPROCESSING_STAGE_CATALOG


def get_preprocessing_stage_spec(stage_id: str) -> PreprocessingStageSpec:
    try:
        return _CATALOG_BY_ID[stage_id]
    except KeyError as exc:
        raise KeyError(f"Unknown preprocessing stage: {stage_id}") from exc


def build_legacy_dparsfa_stages() -> list[dict[str, object]]:
    return [
        {
            "stage_id": spec.stage_id,
            "name": spec.display_name,
            "backend": spec.default_backend,
            "requires_external_tool": spec.requires_external_tool,
            "optional": spec.optional,
            "description": spec.description,
        }
        for spec in PREPROCESSING_STAGE_CATALOG
    ]


def stage_aliases(stage_id: str) -> set[str]:
    return {stage_id, stage_id.replace("_", "-"), *LEGACY_STAGE_ALIASES.get(stage_id, set())}


def stage_dry_run_manifest_names(stage_id: str) -> set[str]:
    return LEGACY_DRY_RUN_MANIFESTS.get(stage_id, {f"{stage_id}_dry_run_manifest.json"})


def contains_stage_marker(text: str, stage_id: str) -> bool:
    lowered = text.lower()
    return any(alias in lowered for alias in stage_aliases(stage_id))


def initial_stage_execution_status(
    spec: PreprocessingStageSpec,
) -> PreprocessingStageExecutionStatus:
    if spec.requires_external_tool:
        return "blocked"
    if not spec.default_enabled:
        return "skipped"
    return spec.initial_status


def normalize_stage_execution_status(
    status: str,
    *,
    metadata_only: bool = False,
    preview_only: bool = False,
) -> PreprocessingStageExecutionStatus:
    if metadata_only:
        return "metadata_only"
    if preview_only:
        return "preview_only"
    legacy_map = {
        "dry_run_preview": "preview_only",
        "dry_run_ready": "preview_only",
        "disabled_external": "blocked",
        "planned_not_executed": "planned",
        "warning": "partial",
        "registered_from_dry_run": "preview_only",
        "registered": "succeeded",
        "numerically_computed": "succeeded",
    }
    normalized = legacy_map.get(status, status)
    if normalized in PREPROCESSING_STAGE_STATUS_VALUES:
        return cast(PreprocessingStageExecutionStatus, normalized)
    return "not_started"


__all__ = [
    "CAPABILITY_STATUS_VALUES",
    "LEGACY_DRY_RUN_MANIFESTS",
    "LEGACY_STAGE_ALIASES",
    "PREPROCESSING_STAGE_CATALOG",
    "PREPROCESSING_STAGE_ORDER",
    "PREPROCESSING_STAGE_STATUS_VALUES",
    "PreprocessingCapabilityStatus",
    "PreprocessingStageExecutionStatus",
    "PreprocessingStageSpec",
    "build_legacy_dparsfa_stages",
    "contains_stage_marker",
    "get_preprocessing_stage_spec",
    "initial_stage_execution_status",
    "iter_preprocessing_stage_specs",
    "normalize_stage_execution_status",
    "stage_aliases",
    "stage_dry_run_manifest_names",
]
