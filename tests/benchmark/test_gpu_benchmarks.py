from __future__ import annotations

import time

import numpy as np
import pytest


@pytest.mark.slow
@pytest.mark.gpu
class TestGPUBenchmarks:
    """Benchmark CPU vs GPU performance. Requires CUDA GPU.
    Run with: pytest tests/benchmark/ -k gpu -v
    """

    def test_benchmark_reho(self):
        """Time CPU vs GPU for ReHo with increasing data sizes."""
        pytest.importorskip("cupy")
        from src.backend.app.tools.reho_compute import compute_reho_numpy, compute_reho_cupy

        rng = np.random.default_rng(1)
        for size in [(16, 16, 12, 50), (32, 32, 16, 100)]:
            data = rng.normal(0, 1, size=size).astype("float32")

            t0 = time.perf_counter()
            cpu_r = compute_reho_numpy(data, neighborhood=27)
            cpu_t = time.perf_counter() - t0
            assert cpu_r["ok"]

            t0 = time.perf_counter()
            gpu_r = compute_reho_cupy(data, neighborhood=27)
            gpu_t = time.perf_counter() - t0

            if gpu_r["ok"]:
                speedup = cpu_t / max(gpu_t, 0.001)
                print(f"  ReHo {size}: CPU={cpu_r['runtime_seconds']}s, GPU={gpu_r['runtime_seconds']}s, speedup={speedup:.1f}x")
                assert speedup > 2.0, f"GPU speedup {speedup:.1f}x below 2x minimum"

    def test_benchmark_nuisance_regression(self):
        """Time CPU vs GPU for nuisance regression."""
        pytest.importorskip("cupy")
        from src.backend.app.tools.nuisance_regression_compute import (
            compute_nuisance_regression_numpy,
            compute_nuisance_regression_cupy,
        )

        rng = np.random.default_rng(2)
        size = (32, 32, 16, 150)
        data = rng.normal(0, 1, size=size).astype("float32")
        X = np.column_stack([
            rng.normal(0, 0.1, size=150),
            rng.normal(0, 0.1, size=150),
            np.ones(150),
            np.arange(150) / 150.0,
        ]).astype(np.float64)

        cpu_r = compute_nuisance_regression_numpy(data, X)
        assert cpu_r["ok"]
        gpu_r = compute_nuisance_regression_cupy(data, X)

        if gpu_r["ok"]:
            speedup = cpu_r["runtime_seconds"] / max(gpu_r["runtime_seconds"], 0.001)
            print(f"  NuisanceReg: CPU={cpu_r['runtime_seconds']}s, GPU={gpu_r['runtime_seconds']}s, speedup={speedup:.1f}x")
            assert speedup > 2.0

    def test_benchmark_temporal_filtering(self):
        """Time CPU vs GPU for temporal filtering."""
        pytest.importorskip("cupy")
        from src.backend.app.tools.temporal_filtering_compute import (
            compute_temporal_filter_numpy,
            compute_temporal_filter_cupy,
        )

        rng = np.random.default_rng(3)
        size = (32, 32, 16, 200)
        data = rng.normal(0, 1, size=size).astype("float32")

        cpu_r = compute_temporal_filter_numpy(data, tr=2.0, low_hz=0.01, high_hz=0.08)
        assert cpu_r["ok"]
        gpu_r = compute_temporal_filter_cupy(data, tr=2.0, low_hz=0.01, high_hz=0.08)

        if gpu_r["ok"]:
            speedup = cpu_r["runtime_seconds"] / max(gpu_r["runtime_seconds"], 0.001)
            print(f"  TemporalFilter: CPU={cpu_r['runtime_seconds']}s, GPU={gpu_r['runtime_seconds']}s, speedup={speedup:.1f}x")
            assert speedup > 2.0

    def test_benchmark_functional_connectivity(self):
        """Time CPU vs GPU for functional connectivity."""
        pytest.importorskip("cupy")
        from src.backend.app.tools.functional_connectivity_compute import (
            compute_fc_numpy,
            compute_fc_cupy,
            _generate_atlas,
        )

        rng = np.random.default_rng(4)
        size = (32, 32, 16, 150)
        data = rng.normal(0, 1, size=size).astype("float32")
        atlas, _ = _generate_atlas(size[:3], 8)

        cpu_r = compute_fc_numpy(data, atlas, generate_seed_map=True)
        assert cpu_r["ok"]
        gpu_r = compute_fc_cupy(data, atlas, generate_seed_map=True)

        if gpu_r["ok"]:
            speedup = cpu_r["runtime_seconds"] / max(gpu_r["runtime_seconds"], 0.001)
            print(f"  FC: CPU={cpu_r['runtime_seconds']}s, GPU={gpu_r['runtime_seconds']}s, speedup={speedup:.1f}x")
            assert speedup > 2.0
