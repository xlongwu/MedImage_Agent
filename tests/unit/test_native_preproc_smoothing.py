from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")
pytest.importorskip("scipy")

from src.backend.app.native_preproc.stages.smoothing import run_smoothing


def _save_bold(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4)), str(path))
    return path


def test_smoothing_is_spatial_only_and_preserves_timepoints(tmp_path: Path) -> None:
    data = np.zeros((7, 7, 7, 3), dtype=np.float32)
    data[3, 3, 3, 1] = 1.0
    bold = _save_bold(tmp_path / "sub-01_task-rest_bold.nii.gz", data)

    result = run_smoothing(bold, tmp_path / "native", fwhm_mm=2.0)

    assert result.status == "succeeded"
    out = np.asanyarray(nib.load(result.output_artifacts[0].path).dataobj)
    assert out.shape == data.shape
    assert result.qc.metrics["timepoints_preserved"] is True
    assert float(out[3, 3, 3, 1]) < 1.0
    assert float(out[3, 3, 4, 1]) > 0.0
    assert np.allclose(out[..., 0], 0.0)
    assert np.allclose(out[..., 2], 0.0)
    assert result.output_artifacts[0].metadata["spatial_only"] is True


def test_smoothing_blocks_invalid_fwhm(tmp_path: Path) -> None:
    bold = _save_bold(tmp_path / "sub-01_task-rest_bold.nii.gz", np.zeros((4, 4, 4, 2), dtype=np.float32))

    result = run_smoothing(bold, tmp_path / "native", fwhm_mm=-1.0)

    assert result.status == "blocked"
    assert result.output_artifacts == []
    assert "FWHM values must be non-negative" in result.errors[0]
