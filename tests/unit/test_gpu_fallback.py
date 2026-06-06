from __future__ import annotations

import sys

import numpy as np
import pytest


@pytest.fixture()
def small_4d():
    rng = np.random.default_rng(7)
    return rng.normal(0, 1, size=(6, 6, 4, 10)).astype("float32")


class TestReHoFallback:
    def test_prefer_gpu_falls_back_to_cpu(self, small_4d, monkeypatch):
        monkeypatch.setitem(sys.modules, "cupy", None)
        from src.backend.app.tools.reho_compute import compute_reho_backend

        result = compute_reho_backend(small_4d, prefer_gpu=True, require_gpu=False)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"

    def test_require_gpu_fails(self, small_4d, monkeypatch):
        monkeypatch.setitem(sys.modules, "cupy", None)
        from src.backend.app.tools.reho_compute import compute_reho_backend

        result = compute_reho_backend(small_4d, require_gpu=True)
        assert not result["ok"]
        assert "require_gpu=True" in result["errors"][0]


class TestNuisanceRegressionFallback:
    def test_prefer_gpu_falls_back_to_cpu(self, small_4d, monkeypatch):
        monkeypatch.setitem(sys.modules, "cupy", None)
        from src.backend.app.tools.nuisance_regression_compute import compute_nuisance_regression_backend

        X = np.column_stack([np.ones(10), np.arange(10)]).astype(np.float64)
        result = compute_nuisance_regression_backend(small_4d, X, prefer_gpu=True)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"


class TestTemporalFilteringFallback:
    def test_prefer_gpu_falls_back_to_cpu(self, small_4d, monkeypatch):
        monkeypatch.setitem(sys.modules, "cupy", None)
        from src.backend.app.tools.temporal_filtering_compute import compute_temporal_filter_backend

        result = compute_temporal_filter_backend(small_4d, tr=2.0, low_hz=0.01, high_hz=0.08, prefer_gpu=True)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"


class TestFCFallback:
    def test_prefer_gpu_falls_back_to_cpu(self, small_4d, monkeypatch):
        monkeypatch.setitem(sys.modules, "cupy", None)
        from src.backend.app.tools.functional_connectivity_compute import compute_fc_backend

        atlas = np.zeros(small_4d.shape[:3], dtype=np.int16)
        atlas[:3, :, :] = 1
        atlas[3:, :, :] = 2
        result = compute_fc_backend(small_4d, atlas, prefer_gpu=True)
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"


class TestGpuMemory:
    def test_estimate_memory(self):
        from src.backend.app.tools.gpu_memory import estimate_memory_requirement

        mb = estimate_memory_requirement((64, 64, 32, 150), "float32")
        assert mb > 0
        assert mb < 10000  # Should be reasonable

    def test_get_gpu_memory_info(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "cupy", None)
        monkeypatch.setitem(sys.modules, "torch", None)

        from src.backend.app.tools.gpu_memory import get_gpu_memory_info

        result = get_gpu_memory_info()
        assert result["ok"]
        assert "free_mb" in result
        assert "total_mb" in result
