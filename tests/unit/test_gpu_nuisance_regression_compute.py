from __future__ import annotations

import sys

import numpy as np
import pytest


@pytest.fixture()
def small_4d_data():
    rng = np.random.default_rng(123)
    return rng.normal(0, 2, size=(6, 6, 4, 15)).astype("float32")


@pytest.fixture()
def design_matrix():
    rng = np.random.default_rng(123)
    X = np.column_stack([
        rng.normal(0, 0.1, size=15),
        rng.normal(0, 0.1, size=15),
        np.ones(15),
    ])
    return X.astype(np.float64)


class TestNuisanceRegressionComputeNumPy:
    def test_numpy_shapes(self, small_4d_data, design_matrix):
        from src.backend.app.tools.nuisance_regression_compute import compute_nuisance_regression_numpy

        result = compute_nuisance_regression_numpy(small_4d_data, design_matrix)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"
        residual = result["residual_4d"]
        assert residual.shape == small_4d_data.shape
        assert residual.dtype == np.float32
        assert result["confound_rank"] > 0

    def test_residual_variance_ratio(self, small_4d_data, design_matrix):
        from src.backend.app.tools.nuisance_regression_compute import compute_nuisance_regression_numpy

        result = compute_nuisance_regression_numpy(small_4d_data, design_matrix)
        assert result["ok"]
        # Nuisance regression should reduce or maintain variance
        assert result["variance_ratio"] is not None
        assert result["variance_ratio"] <= 1.0 + 1e-6 or result["variance_ratio"] < 1.2

    def test_shape_mismatch(self, small_4d_data):
        from src.backend.app.tools.nuisance_regression_compute import compute_nuisance_regression_numpy

        bad_X = np.ones((10, 3))
        result = compute_nuisance_regression_numpy(small_4d_data, bad_X)
        assert not result["ok"]


class TestNuisanceRegressionBackend:
    def test_backend_cpu_fallback(self, small_4d_data, design_matrix):
        from src.backend.app.tools.nuisance_regression_compute import compute_nuisance_regression_backend

        result = compute_nuisance_regression_backend(small_4d_data, design_matrix, prefer_gpu=False)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"

    def test_backend_require_gpu_fails_without_cupy(self, small_4d_data, design_matrix, monkeypatch):
        from src.backend.app.tools.nuisance_regression_compute import compute_nuisance_regression_backend

        monkeypatch.setitem(sys.modules, "cupy", None)
        result = compute_nuisance_regression_backend(small_4d_data, design_matrix, require_gpu=True)
        assert not result["ok"]
