from __future__ import annotations

import sys

import numpy as np
import pytest

from src.backend.app.tools.functional_connectivity_compute import _generate_atlas


@pytest.fixture()
def small_fc_data():
    rng = np.random.default_rng(99)
    nx, ny, nz, nt = 6, 6, 4, 20
    # Create data with distinct ROI signals
    data = np.zeros((nx, ny, nz, nt), dtype="float32")
    # ROI 1: first x-half, strong signal
    data[:3, :, :, :] = rng.normal(5, 1, size=(3, ny, nz, nt)).astype("float32")
    # ROI 2: second x-half, different signal
    data[3:, :, :, :] = rng.normal(-2, 0.5, size=(3, ny, nz, nt)).astype("float32")
    atlas, defs = _generate_atlas((nx, ny, nz), 2)
    return data, atlas, defs


class TestFCComputeNumPy:
    def test_numpy_shapes(self, small_fc_data):
        from src.backend.app.tools.functional_connectivity_compute import compute_fc_numpy

        data, atlas, _ = small_fc_data
        result = compute_fc_numpy(data, atlas, generate_seed_map=True)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"
        corr = result["correlation_matrix"]
        assert corr.shape == (2, 2)
        assert np.abs(np.diag(corr) - 1.0).max() < 1e-5

    def test_seed_map_shape(self, small_fc_data):
        from src.backend.app.tools.functional_connectivity_compute import compute_fc_numpy

        data, atlas, _ = small_fc_data
        result = compute_fc_numpy(data, atlas, generate_seed_map=True)
        assert result["ok"]
        assert result["seed_correlation_map"] is not None
        assert result["seed_correlation_map"].shape == data.shape[:3]


class TestFCBackend:
    def test_backend_cpu_fallback(self, small_fc_data):
        from src.backend.app.tools.functional_connectivity_compute import compute_fc_backend

        data, atlas, _ = small_fc_data
        result = compute_fc_backend(data, atlas, prefer_gpu=False)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"

    def test_backend_require_gpu_fails(self, small_fc_data, monkeypatch):
        from src.backend.app.tools.functional_connectivity_compute import compute_fc_backend

        data, atlas, _ = small_fc_data
        monkeypatch.setitem(sys.modules, "cupy", None)
        result = compute_fc_backend(data, atlas, require_gpu=True)
        assert not result["ok"]
