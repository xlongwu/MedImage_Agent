from __future__ import annotations

import sys

import numpy as np
import pytest


@pytest.fixture()
def sine_wave_data():
    """Create 4D data with known frequency content for filtering tests."""
    nx, ny, nz, nt = 6, 6, 4, 100
    tr = 2.0
    t = np.arange(nt) * tr
    # Low-frequency sine (0.02 Hz)
    signal = np.sin(2 * np.pi * 0.02 * t).astype("float32")
    data = np.zeros((nx, ny, nz, nt), dtype="float32")
    data[:, :, :, :] = signal[np.newaxis, np.newaxis, np.newaxis, :]
    return data, tr


class TestTemporalFilteringComputeNumPy:
    def test_numpy_shapes(self, sine_wave_data):
        from src.backend.app.tools.temporal_filtering_compute import compute_temporal_filter_numpy

        data, tr = sine_wave_data
        result = compute_temporal_filter_numpy(data, tr=tr, low_hz=0.01, high_hz=0.08)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"
        filtered = result["filtered_4d"]
        assert filtered.shape == data.shape
        assert filtered.dtype == np.float32
        assert result["retained_frequency_bin_count"] > 0

    def test_numpy_preserves_low_freq(self, sine_wave_data):
        """Low-frequency signal should pass through band-pass."""
        from src.backend.app.tools.temporal_filtering_compute import compute_temporal_filter_numpy

        data, tr = sine_wave_data
        result = compute_temporal_filter_numpy(data, tr=tr, low_hz=0.01, high_hz=0.08)
        assert result["ok"]
        # The signal should still be present (std > 0)
        assert result["filtered_std"] > 0

    def test_numpy_full_band_preserves(self, sine_wave_data):
        """Full band filter should preserve the input."""
        from src.backend.app.tools.temporal_filtering_compute import compute_temporal_filter_numpy

        data, tr = sine_wave_data
        result = compute_temporal_filter_numpy(data, tr=tr, low_hz=0, high_hz=0.25)
        assert result["ok"]
        max_diff = float(np.max(np.abs(data - result["filtered_4d"])))
        assert max_diff < 0.1  # Should be close to original


class TestTemporalFilteringBackend:
    def test_backend_cpu_fallback(self, sine_wave_data):
        from src.backend.app.tools.temporal_filtering_compute import compute_temporal_filter_backend

        data, tr = sine_wave_data
        result = compute_temporal_filter_backend(data, tr=tr, low_hz=0.01, high_hz=0.08, prefer_gpu=False)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"

    def test_backend_require_gpu_fails(self, sine_wave_data, monkeypatch):
        from src.backend.app.tools.temporal_filtering_compute import compute_temporal_filter_backend

        data, tr = sine_wave_data
        monkeypatch.setitem(sys.modules, "cupy", None)
        result = compute_temporal_filter_backend(data, tr=tr, low_hz=0.01, high_hz=0.08, require_gpu=True)
        assert not result["ok"]
