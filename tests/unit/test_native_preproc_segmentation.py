from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.orchestrator.validation import validate_stage_result_artifacts
from src.backend.app.native_preproc.stages.segmentation import run_segmentation


def _save(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4)), str(path))
    return path


def _tissue_phantom() -> np.ndarray:
    data = np.zeros((9, 9, 9), dtype=np.float32)
    coords = np.indices(data.shape, dtype=np.float32)
    center = np.asarray([4.0, 4.0, 4.0], dtype=np.float32).reshape((3, 1, 1, 1))
    radius = np.sqrt(np.sum((coords - center) ** 2, axis=0))
    data[(radius > 3.0) & (radius <= 4.0)] = 0.25
    data[(radius > 1.8) & (radius <= 3.0)] = 0.55
    data[radius <= 1.8] = 0.85
    return data


def _artifact_path(result, artifact_type: str) -> Path:
    return Path(next(artifact.path for artifact in result.output_artifacts if artifact.artifact_type == artifact_type))


def test_segmentation_writes_simplified_tissue_maps_with_valid_ranges(tmp_path: Path) -> None:
    t1 = _save(tmp_path / "sub-01_T1w.nii.gz", _tissue_phantom())

    result = run_segmentation(t1, tmp_path / "native")

    assert result.status == "simplified"
    assert result.capability_level == "simplified"
    assert "simplified_intensity_kmeans_not_spm_unified_segmentation" in result.warnings
    assert validate_stage_result_artifacts(result) == []
    brain_mask = np.asanyarray(nib.load(_artifact_path(result, "brain_mask")).dataobj)
    assert int(np.count_nonzero(brain_mask)) > 0
    for artifact_type in ("csf_map", "gm_map", "wm_map"):
        data = np.asanyarray(nib.load(_artifact_path(result, artifact_type)).dataobj)
        assert data.shape == brain_mask.shape
        assert float(np.min(data)) >= 0.0
        assert float(np.max(data)) <= 1.0
        assert float(np.sum(data)) > 0.0
    assert result.qc.metrics["wm_volume_voxels"] > 0.0
    assert result.qc.metrics["csf_volume_voxels"] > 0.0


def test_segmentation_blocks_empty_t1(tmp_path: Path) -> None:
    t1 = _save(tmp_path / "sub-01_T1w.nii.gz", np.zeros((4, 4, 4), dtype=np.float32))

    result = run_segmentation(t1, tmp_path / "native")

    assert result.status == "blocked"
    assert result.output_artifacts == []
    assert "brain mask is empty" in result.errors[0]
