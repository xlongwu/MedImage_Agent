from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.orchestrator.validation import validate_stage_result_artifacts
from src.backend.app.native_preproc.stages.alff_falff import run_alff, run_falff


def _save(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), np.eye(4)), str(path))
    return path


def test_alff_and_falff_detect_known_band_limited_signal(tmp_path: Path) -> None:
    tr = 1.0
    timepoints = 128
    times = np.arange(timepoints, dtype=np.float32) * tr
    in_band = np.sin(2.0 * np.pi * (4.0 / timepoints) * times)
    out_of_band = 0.25 * np.sin(2.0 * np.pi * (26.0 / timepoints) * times)
    data = np.zeros((2, 2, 2, timepoints), dtype=np.float32)
    data[0, 0, 0, :] = in_band + out_of_band
    data[1, 1, 1, :] = out_of_band
    bold = _save(tmp_path / "sub-01_desc-filtered_bold.nii.gz", data)
    mask = _save(tmp_path / "mask.nii.gz", np.ones((2, 2, 2), dtype=np.float32))

    alff_result = run_alff(bold, tmp_path / "native", tr=tr, freq_band=(0.01, 0.08), mask=mask)
    falff_result = run_falff(bold, tmp_path / "native", tr=tr, freq_band=(0.01, 0.08), mask=mask)

    assert alff_result.status == "warning"
    assert falff_result.status == "warning"
    assert validate_stage_result_artifacts(alff_result) == []
    assert validate_stage_result_artifacts(falff_result) == []
    alff = np.asanyarray(nib.load(alff_result.output_artifacts[0].path).dataobj)
    falff = np.asanyarray(nib.load(falff_result.output_artifacts[0].path).dataobj)
    assert alff.shape == data.shape[:3]
    assert falff.shape == data.shape[:3]
    assert alff[0, 0, 0] > alff[1, 1, 1]
    assert falff[0, 0, 0] > 0.7
    assert alff_result.output_artifacts[0].artifact_type == "alff_map"
    assert falff_result.output_artifacts[0].artifact_type == "falff_map"


def test_alff_blocks_mask_shape_mismatch(tmp_path: Path) -> None:
    bold = _save(tmp_path / "bold.nii.gz", np.zeros((2, 2, 2, 8), dtype=np.float32))
    bad_mask = _save(tmp_path / "bad_mask.nii.gz", np.ones((3, 2, 2), dtype=np.float32))

    result = run_alff(bold, tmp_path / "native", tr=1.0, mask=bad_mask)

    assert result.status == "blocked"
    assert "mask shape" in result.errors[0]


def test_falff_blocks_band_above_nyquist(tmp_path: Path) -> None:
    bold = _save(tmp_path / "bold.nii.gz", np.zeros((2, 2, 2, 16), dtype=np.float32))

    result = run_falff(bold, tmp_path / "native", tr=2.0, freq_band=(0.01, 0.4))

    assert result.status == "blocked"
    assert "Nyquist" in result.errors[0]
