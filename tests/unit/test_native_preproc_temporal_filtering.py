from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.stages.temporal_filtering import (  # noqa: E402
    run_temporal_filtering,  # noqa: E402
)


def _save_bold(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4)), str(path))
    return path


def _fft_amplitude(series: np.ndarray, tr: float, target_hz: float) -> float:
    freqs = np.fft.rfftfreq(series.shape[0], d=tr)
    spectrum = np.abs(np.fft.rfft(series))
    idx = int(np.argmin(np.abs(freqs - target_hz)))
    return float(spectrum[idx])


def test_temporal_filtering_bandpass_removes_out_of_band_component(tmp_path: Path) -> None:
    tr = 1.0
    timepoints = 128
    times = np.arange(timepoints, dtype=np.float32) * tr
    low = np.sin(2.0 * np.pi * 0.03 * times)
    high = 0.8 * np.sin(2.0 * np.pi * 0.20 * times)
    data = (low + high).reshape((1, 1, 1, timepoints)).astype(np.float32)
    bold = _save_bold(tmp_path / "sub-01_desc-detrended_bold.nii.gz", data)

    result = run_temporal_filtering(
        bold,
        tmp_path / "native",
        tr=tr,
        filter_type="bandpass",
        low_hz=0.01,
        high_hz=0.08,
        method="fft",
    )

    assert result.status == "succeeded"
    out = np.asanyarray(nib.load(result.output_artifacts[0].path).dataobj)
    before_high = _fft_amplitude(data[0, 0, 0, :], tr, 0.20)
    after_high = _fft_amplitude(out[0, 0, 0, :], tr, 0.20)
    before_low = _fft_amplitude(data[0, 0, 0, :], tr, 0.03)
    after_low = _fft_amplitude(out[0, 0, 0, :], tr, 0.03)
    assert after_high < before_high * 0.05
    assert after_low > before_low * 0.8
    assert result.qc.metrics["filter"]["retained_frequency_bin_count"] > 0
    assert result.output_artifacts[0].artifact_type == "filtered_bold"


def test_temporal_filtering_no_filter_preserves_data(tmp_path: Path) -> None:
    data = np.random.default_rng(0).normal(size=(2, 2, 2, 8)).astype(np.float32)
    bold = _save_bold(tmp_path / "sub-01_bold.nii.gz", data)

    result = run_temporal_filtering(bold, tmp_path / "native", tr=2.0, filter_type="no-filter")

    assert result.status == "succeeded"
    out = np.asanyarray(nib.load(result.output_artifacts[0].path).dataobj)
    assert np.allclose(out, data)
    assert result.parameters["filter_type"] == "no-filter"


def test_temporal_filtering_blocks_band_above_nyquist(tmp_path: Path) -> None:
    bold = _save_bold(tmp_path / "sub-01_bold.nii.gz", np.zeros((2, 2, 2, 8), dtype=np.float32))

    result = run_temporal_filtering(bold, tmp_path / "native", tr=1.0, low_hz=0.01, high_hz=0.6)

    assert result.status == "blocked"
    assert "Nyquist" in result.errors[0]
