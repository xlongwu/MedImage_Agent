from __future__ import annotations

import sys

import numpy as np
import pytest


@pytest.fixture()
def small_4d_data():
    rng = np.random.default_rng(42)
    return rng.normal(0, 1, size=(8, 8, 6, 20)).astype("float32")


class TestRehoComputeNumPy:
    def test_numpy_shapes(self, small_4d_data):
        from src.backend.app.tools.reho_compute import compute_reho_numpy

        result = compute_reho_numpy(small_4d_data, neighborhood=27)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"
        reho = result["reho"]
        assert reho.shape == small_4d_data.shape[:3]
        assert reho.dtype == np.float32
        assert result["valid_voxel_count"] > 0

    def test_numpy_output_shape_valid(self):
        """Verify output shape matches input spatial dimensions."""
        from src.backend.app.tools.reho_compute import compute_reho_numpy

        nx, ny, nz, nt = 6, 6, 4, 10
        data = np.random.default_rng(77).normal(0, 1, size=(nx, ny, nz, nt)).astype("float32")
        result = compute_reho_numpy(data, neighborhood=27)
        assert result["ok"]
        reho = result["reho"]
        assert reho.shape == (nx, ny, nz)
        assert reho.dtype == np.float32
        assert result["valid_voxel_count"] > 0

    def test_numpy_neighborhood_sizes(self, small_4d_data):
        from src.backend.app.tools.reho_compute import compute_reho_numpy

        for nb in [7, 19, 27]:
            result = compute_reho_numpy(small_4d_data, neighborhood=nb)
            assert result["ok"]


class TestRehoComputeBackend:
    def test_backend_cpu_fallback(self, small_4d_data):
        from src.backend.app.tools.reho_compute import compute_reho_backend

        result = compute_reho_backend(small_4d_data, prefer_gpu=False)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"

    def test_backend_require_gpu_fails_without_cupy(self, small_4d_data, monkeypatch):
        from src.backend.app.tools.reho_compute import compute_reho_backend

        # Force cupy import to fail
        monkeypatch.setitem(sys.modules, "cupy", None)
        result = compute_reho_backend(small_4d_data, require_gpu=True)
        assert not result["ok"]
        assert result["backend"] == "none"
        assert "require_gpu=True" in result["errors"][0]
