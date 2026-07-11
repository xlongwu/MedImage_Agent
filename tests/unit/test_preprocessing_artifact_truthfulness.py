from __future__ import annotations

from pathlib import Path

from src.backend.app.services.preprocessing_orchestrator import _artifact_type_for_output


def test_fc_atlas_nifti_outputs_are_registered_as_atlas():
    assert _artifact_type_for_output(
        "functional_connectivity",
        Path("aal_atlas_sha256-abcdef123456.nii"),
    ) == "atlas"
    assert _artifact_type_for_output(
        "functional_connectivity",
        Path("synthetic_roi_atlas.nii"),
    ) == "atlas"


def test_fc_seed_maps_are_not_registered_as_atlas():
    assert _artifact_type_for_output(
        "functional_connectivity",
        Path("seed_correlation_map.nii"),
    ) != "atlas"
