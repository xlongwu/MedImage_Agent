from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")
pytest.importorskip("scipy")

from src.backend.app.native_preproc.orchestrator.validation import (  # noqa: E402
    validate_stage_result_artifacts,  # noqa: E402
)
from src.backend.app.native_preproc.stages.atlas_resampling import (  # noqa: E402
    run_atlas_resampling,  # noqa: E402
)


def _save(path: Path, data: np.ndarray, affine: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data, affine), str(path))
    return path


def test_atlas_resampling_uses_nearest_neighbor_and_preserves_labels(tmp_path: Path) -> None:
    atlas = np.zeros((4, 4, 4), dtype=np.int16)
    atlas[:2, :, :] = 1
    atlas[2:, :, :] = 2
    atlas_affine = np.diag([2.0, 2.0, 2.0, 1.0])
    reference = np.zeros((8, 8, 8, 2), dtype=np.float32)
    reference_affine = np.eye(4)
    atlas_path = _save(tmp_path / "synthetic_atlas.nii.gz", atlas, atlas_affine)
    reference_path = _save(
        tmp_path / "sub-01_space-template_bold.nii.gz", reference, reference_affine
    )

    result = run_atlas_resampling(atlas_path, reference_path, tmp_path / "native")

    assert result.status == "succeeded"
    assert result.capability_level == "numerically_implemented"
    assert validate_stage_result_artifacts(result) == []
    output = np.asanyarray(nib.load(result.output_artifacts[0].path).dataobj)
    assert output.shape == reference.shape[:3]
    assert set(np.unique(output)).issubset({0.0, 1.0, 2.0})
    assert result.qc.metrics["fractional_label_voxels"] == 0
    assert result.output_artifacts[0].metadata["interpolation"] == "nearest_neighbor"


def test_atlas_resampling_blocks_4d_atlas(tmp_path: Path) -> None:
    atlas_path = _save(
        tmp_path / "bad_atlas.nii.gz", np.zeros((2, 2, 2, 2), dtype=np.int16), np.eye(4)
    )
    reference_path = _save(
        tmp_path / "sub-01_space-template_bold.nii.gz",
        np.zeros((2, 2, 2), dtype=np.float32),
        np.eye(4),
    )

    result = run_atlas_resampling(atlas_path, reference_path, tmp_path / "native")

    assert result.status == "blocked"
    assert result.output_artifacts == []
    assert "3D atlas input" in result.errors[0]
