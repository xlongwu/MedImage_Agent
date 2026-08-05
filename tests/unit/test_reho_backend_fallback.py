"""Tests for ReHo backend GPU/CPU selection and experimental gating."""

from __future__ import annotations

import numpy as np

# ── Helper: create synthetic 4D data ──


def _make_data(shape=(8, 8, 8, 20), ties=False):
    """Create synthetic 4D BOLD data, optionally with tied values."""
    rng = np.random.default_rng(42)
    data = rng.random(shape, dtype=np.float32)
    if ties:
        # Introduce ties in a few interior voxels
        for x in range(2, 6):
            for y in range(2, 6):
                data[x, y, 2, 5] = data[x, y, 2, 0]  # duplicate timepoint
    return data


# ── Mock GPU — available ──


def _mock_cupy_available(monkeypatch):
    """Monkeypatch so that `import cupy` succeeds."""
    import types

    cupy_mod = types.ModuleType("cupy")
    monkeypatch.setitem(
        __import__("sys").modules,
        "cupy",
        cupy_mod,
    )


# ── Mock GPU — unavailable ──


def _mock_cupy_unavailable(monkeypatch):
    """Restore normal import (CuPy not installed)."""
    import builtins
    import sys

    # Remove cupy from sys.modules if it was added
    sys.modules.pop("cupy", None)
    original_import = builtins.__import__

    def _block_cupy(name, *args, **kwargs):
        if name == "cupy":
            raise ImportError("No module named cupy")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_cupy)


# ── Tests ──


class TestRehoBackendTiesFallback:
    """Test experimental ReHo GPU selection without probabilistic tie gates."""

    def test_ties_use_exact_gpu_kernel_when_explicitly_opted_in(self, monkeypatch):
        """Tied values do not force fallback because the kernel corrects ties."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=True)
        _mock_cupy_available(monkeypatch)

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy",
            lambda *a, **kw: {
                "ok": True,
                "backend": "gpu-cupy",
                "reho": np.zeros(data.shape[:3], dtype=np.float32),
                "valid_voxel_count": 1,
                "skipped_voxel_count": 0,
                "warnings": [],
                "errors": [],
                "runtime_seconds": 0.01,
            },
        )

        result = compute_reho_backend(
            data,
            neighborhood=7,
            prefer_gpu=True,
            require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"], result.get("errors")
        assert result["backend"] == "gpu-cupy"

    def test_require_gpu_uses_exact_kernel_for_ties(self, monkeypatch):
        """require_gpu=True does not reject tied data after tie correction."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=True)
        _mock_cupy_available(monkeypatch)

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy",
            lambda *a, **kw: {
                "ok": True,
                "backend": "gpu-cupy",
                "reho": np.zeros(data.shape[:3], dtype=np.float32),
                "valid_voxel_count": 1,
                "skipped_voxel_count": 0,
                "warnings": [],
                "errors": [],
                "runtime_seconds": 0.01,
            },
        )

        result = compute_reho_backend(
            data,
            neighborhood=7,
            prefer_gpu=True,
            require_gpu=True,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"]
        assert result["backend"] == "gpu-cupy"

    def test_require_gpu_fails_when_cupy_unavailable(self, monkeypatch):
        """require_gpu=True + CuPy not installed → failure."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_unavailable(monkeypatch)

        result = compute_reho_backend(
            data,
            neighborhood=7,
            require_gpu=True,
        )
        assert not result["ok"]
        assert result["backend"] == "none"
        errors = result.get("errors", [])
        assert any("CuPy is not available" in e for e in errors), (
            f"Expected CuPy unavailable error, got: {errors}"
        )

    def test_uses_gpu_for_tie_free_data_with_opt_in(self, monkeypatch):
        """allow_unvalidated_gpu=True + no ties → GPU path used."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        # Mock GPU compute to return a success
        def mock_cupy(*a, **kw):
            return {
                "ok": True,
                "backend": "gpu-cupy",
                "reho": np.zeros(data.shape[:3], dtype=np.float32),
                "valid_voxel_count": 10,
                "skipped_voxel_count": 0,
                "warnings": [],
                "errors": [],
                "runtime_seconds": 0.01,
            }

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy",
            mock_cupy,
        )

        result = compute_reho_backend(
            data,
            neighborhood=7,
            prefer_gpu=True,
            require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"]
        assert result["backend"] == "gpu-cupy", f"Expected GPU, got {result['backend']}"

    def test_cpu_only_without_allow_unvalidated(self, monkeypatch):
        """prefer_gpu=True + allow_unvalidated_gpu=False → CPU only (safety gate)."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        # Should never call GPU in default experimental-off mode.
        gpu_called = [False]

        def mock_cupy(*a, **kw):
            gpu_called[0] = True
            return {"ok": True, "backend": "gpu-cupy"}

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy",
            mock_cupy,
        )

        result = compute_reho_backend(
            data,
            neighborhood=7,
            prefer_gpu=True,
            require_gpu=False,
            allow_unvalidated_gpu=False,  # default
        )
        assert result["ok"]
        assert result["backend"] == "cpu-numpy", (
            f"Expected CPU when allow_unvalidated_gpu=False, got {result['backend']}"
        )
        assert not gpu_called[0], "GPU should not be called without opt-in"
        safety_warnings = [w for w in result.get("warnings", []) if "experimental" in w]
        assert len(safety_warnings) >= 1, (
            "Expected safety-gate warning explaining allow_unvalidated_gpu"
        )

    def test_allow_unvalidated_gpu_tie_free_uses_gpu(self, monkeypatch):
        """allow_unvalidated_gpu=True + ties free → GPU used."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        def mock_cupy(*a, **kw):
            return {
                "ok": True,
                "backend": "gpu-cupy",
                "reho": np.zeros(data.shape[:3], dtype=np.float32),
                "valid_voxel_count": 10,
                "skipped_voxel_count": 0,
                "warnings": [],
                "errors": [],
                "runtime_seconds": 0.01,
            }

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy",
            mock_cupy,
        )

        result = compute_reho_backend(
            data,
            neighborhood=7,
            prefer_gpu=True,
            require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"]
        assert result["backend"] == "gpu-cupy"

    def test_gpu_compute_failure_falls_back_when_not_required(self, monkeypatch):
        """A real GPU compute failure falls back only for non-require mode."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy",
            lambda *a, **kw: {
                "ok": False,
                "backend": "gpu-cupy",
                "reho": None,
                "valid_voxel_count": 0,
                "skipped_voxel_count": 0,
                "warnings": [],
                "errors": ["forced failure"],
                "runtime_seconds": 0.01,
            },
        )

        result = compute_reho_backend(
            data,
            neighborhood=7,
            prefer_gpu=True,
            require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"


class TestRehoBackendDirectCpu:
    """Test that prefer_gpu=False always uses CPU."""

    def test_prefer_gpu_false_uses_cpu(self):
        """prefer_gpu=False → CPU path directly."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        result = compute_reho_backend(
            data,
            neighborhood=7,
            prefer_gpu=False,
        )
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"
