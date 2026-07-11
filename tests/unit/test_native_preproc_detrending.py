from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.stages.detrending import run_detrending


def _save_bold(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4)), str(path))
    return path


def test_detrending_removes_linear_trend_and_preserves_shape(tmp_path: Path) -> None:
    timepoints = 32
    t = np.linspace(-1.0, 1.0, timepoints, dtype=np.float32)
    data = np.zeros((2, 2, 2, timepoints), dtype=np.float32)
    data[:] = 2.0 + 5.0 * t
    bold = _save_bold(tmp_path / "sub-01_desc-residual_bold.nii.gz", data)

    result = run_detrending(bold, tmp_path / "native", polynomial_order=1)

    assert result.status == "succeeded"
    out = np.asanyarray(nib.load(result.output_artifacts[0].path).dataobj)
    assert out.shape == data.shape
    slope = np.polyfit(t, out[0, 0, 0, :], deg=1)[0]
    assert abs(float(slope)) < 1e-5
    assert result.output_artifacts[0].artifact_type == "detrended_bold"
    assert result.qc.metrics["timepoints_preserved"] is True


def test_detrending_blocks_insufficient_timepoints(tmp_path: Path) -> None:
    bold = _save_bold(tmp_path / "sub-01_bold.nii.gz", np.zeros((2, 2, 2, 2), dtype=np.float32))

    result = run_detrending(bold, tmp_path / "native", polynomial_order=2)

    assert result.status == "blocked"
    assert "insufficient timepoints" in result.errors[0]
