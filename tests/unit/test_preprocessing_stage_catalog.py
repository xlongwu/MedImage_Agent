"""Tests for the unified preprocessing stage catalog."""
from __future__ import annotations

from src.backend.app.schemas.preprocessing_stage_catalog import (
    PREPROCESSING_STAGE_ORDER,
    PREPROCESSING_STAGE_STATUS_VALUES,
    build_legacy_dparsfa_stages,
    get_preprocessing_stage_spec,
    iter_preprocessing_stage_specs,
    normalize_stage_execution_status,
)


def test_stage_status_values_match_contract() -> None:
    assert PREPROCESSING_STAGE_STATUS_VALUES == (
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


def test_catalog_stage_ids_are_unique_and_ordered() -> None:
    stage_ids = [spec.stage_id for spec in iter_preprocessing_stage_specs()]
    assert len(stage_ids) == len(set(stage_ids))
    assert tuple(stage_ids) == PREPROCESSING_STAGE_ORDER
    assert stage_ids[0] == "input_validation"
    assert stage_ids[-1] == "group_summary"


def test_python_scientific_stages_are_not_matlab_only() -> None:
    for stage_id in (
        "nuisance_regression",
        "temporal_filtering",
        "alff_falff",
        "reho",
        "functional_connectivity",
    ):
        spec = get_preprocessing_stage_spec(stage_id)
        assert spec.default_backend == "python"
        assert "python" in spec.supported_backends
        assert not spec.requires_external_tool
        assert not spec.requires_approval
        assert spec.scientific_status == "computed"


def test_spatial_stages_default_to_native_with_explicit_spm_backend_available() -> None:
    for stage_id in (
        "slice_timing",
        "realignment",
        "t1_coregistration",
        "segmentation",
        "normalization",
        "spatial_smoothing",
    ):
        spec = get_preprocessing_stage_spec(stage_id)
        assert spec.default_backend == "native_python"
        assert "native_python" in spec.supported_backends
        assert "spm12" in spec.supported_backends
        assert not spec.requires_external_tool
        assert not spec.requires_approval
        assert spec.requires_env_flags == []
        assert spec.can_run_in_ci
        assert spec.initial_status in {"planned", "skipped"}
        assert "reference_pending" in spec.validation_status


def test_fc_catalog_distinguishes_real_fc_from_preview_risk() -> None:
    fc = get_preprocessing_stage_spec("functional_connectivity")
    assert fc.required_for_fc
    assert "atlas" in fc.input_artifact_types
    assert "fc_matrix" in fc.output_artifact_types
    assert "atlas_grounding_pending" in fc.validation_status
    assert fc.depends_on == ["temporal_filtering"]
    assert any("MNI atlas mode requires" in note for note in fc.prerequisite_notes)


def test_dparsfa_optional_stage_dependencies_are_explicit() -> None:
    coreg = get_preprocessing_stage_spec("t1_coregistration")
    segmentation = get_preprocessing_stage_spec("segmentation")
    normalization = get_preprocessing_stage_spec("normalization")
    smoothing = get_preprocessing_stage_spec("spatial_smoothing")
    nuisance = get_preprocessing_stage_spec("nuisance_regression")
    alff = get_preprocessing_stage_spec("alff_falff")
    reho = get_preprocessing_stage_spec("reho")

    assert coreg.depends_on == ["realignment"]
    assert segmentation.depends_on == ["t1_coregistration"]
    assert normalization.depends_on == ["segmentation"]
    assert smoothing.depends_on == ["normalization"]
    assert alff.depends_on == ["temporal_filtering"]
    assert reho.depends_on == ["temporal_filtering"]
    assert "segmentation_maps" not in nuisance.input_artifact_types
    assert "segmentation_maps" in nuisance.optional_input_artifact_types
    assert any("WM/CSF" in note for note in segmentation.prerequisite_notes)
    assert any("MNI-atlas" in note for note in normalization.prerequisite_notes)


def test_legacy_dparsfa_stage_export_is_derived_from_catalog() -> None:
    legacy = build_legacy_dparsfa_stages()
    assert [stage["stage_id"] for stage in legacy] == list(PREPROCESSING_STAGE_ORDER)
    nuisance = next(stage for stage in legacy if stage["stage_id"] == "nuisance_regression")
    assert nuisance["backend"] == "python"
    assert nuisance["requires_external_tool"] is False


def test_legacy_statuses_normalize_to_stage_contract() -> None:
    assert normalize_stage_execution_status("dry_run_ready") == "preview_only"
    assert normalize_stage_execution_status("disabled_external") == "blocked"
    assert normalize_stage_execution_status("planned_not_executed") == "planned"
    assert normalize_stage_execution_status("succeeded", metadata_only=True) == "metadata_only"
