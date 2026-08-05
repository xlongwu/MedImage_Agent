from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.stages.slice_timing import (  # noqa: E402
    run_slice_timing_correction,  # noqa: E402
)


def _save_nifti(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4)), str(path))
    return path


def _sidecar_for(path: Path) -> Path:
    return path.with_name(path.name[:-7] + ".json")


def test_slice_timing_corrects_shifted_sine_wave_and_preserves_shape(tmp_path: Path) -> None:
    tr = 2.0
    timepoints = 60
    sample_times = np.arange(timepoints, dtype=np.float32) * tr
    freq_hz = 0.04
    data = np.zeros((1, 1, 2, timepoints), dtype=np.float32)
    data[0, 0, 0, :] = np.sin(2.0 * np.pi * freq_hz * (sample_times + 0.0))
    data[0, 0, 1, :] = np.sin(2.0 * np.pi * freq_hz * (sample_times + 1.0))
    bold = _save_nifti(tmp_path / "sub-01_task-rest_bold.nii.gz", data)
    _sidecar_for(bold).write_text(
        json.dumps({"RepetitionTime": tr, "SliceTiming": [0.0, 1.0]}),
        encoding="utf-8",
    )

    result = run_slice_timing_correction(bold, tmp_path / "native", reference_time=0.0)

    assert result.status == "succeeded"
    out = np.asanyarray(nib.load(result.output_artifacts[0].path).dataobj)
    assert out.shape == data.shape
    original_error = np.mean(np.abs(data[0, 0, 1, 5:-5] - data[0, 0, 0, 5:-5]))
    corrected_error = np.mean(np.abs(out[0, 0, 1, 5:-5] - out[0, 0, 0, 5:-5]))
    assert corrected_error < original_error * 0.35
    assert result.qc.metrics["tr"] == tr
    assert result.output_artifacts[0].metadata["reference_time"] == 0.0


def test_slice_timing_blocks_when_sidecar_metadata_is_missing(tmp_path: Path) -> None:
    bold = _save_nifti(
        tmp_path / "sub-01_task-rest_bold.nii.gz", np.zeros((2, 2, 2, 4), dtype=np.float32)
    )

    result = run_slice_timing_correction(bold, tmp_path / "native")

    assert result.status == "blocked"
    assert result.output_artifacts == []
    assert any("sidecar" in error.lower() for error in result.errors)
    assert (tmp_path / "native" / "qc" / "slice_timing_qc.json").exists()
