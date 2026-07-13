from __future__ import annotations

import asyncio

import numpy as np

from src.backend.app.api.gpu_routes import gpu_synthetic_benchmark
from src.backend.app.tools import alff_compute


def test_synthetic_benchmark_uses_current_alff_backend_contract(monkeypatch):
    def cpu(data, tr, freq_band):
        assert data.shape == (2, 2, 2, 8)
        assert tr == 2.0
        assert freq_band == (0.01, 0.08)
        return np.zeros((2, 2, 2), dtype=np.float32), np.zeros((2, 2, 2), dtype=np.float32), []

    def gpu(data, tr, freq_band, prefer_gpu, require_gpu):
        assert prefer_gpu is True
        assert require_gpu is True
        return {"ok": True, "backend": "gpu-cupy", "errors": []}

    monkeypatch.setattr(alff_compute, "compute_alff_numpy", cpu)
    monkeypatch.setattr(alff_compute, "compute_alff_backend", gpu)

    result = asyncio.run(gpu_synthetic_benchmark({"shape": [2, 2, 2, 8]}))

    assert result["gpu_time_s"] is not None
    assert result["gpu_error"] is None
