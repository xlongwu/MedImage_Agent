"""Tests for ReHo backend GPU/CPU selection and ties fallback logic.

These tests use monkeypatch to simulate GPU availability, ties detection,
and backend functions — no real CuPy installation is required.
"""
from __future__ import annotations
import numpy as np
import pytest


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
        __import__("sys").modules, "cupy", cupy_mod,
    )


# ── Mock GPU — unavailable ──

def _mock_cupy_unavailable(monkeypatch):
    """Restore normal import (CuPy not installed)."""
    import sys
    import builtins
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
    """Test that ties detection triggers CPU fallback correctly."""

    def test_falls_back_to_cpu_when_ties_detected_prefer_gpu(self, monkeypatch):
        """prefer_gpu=True + ties detected → CPU fallback (with allow_unvalidated_gpu)."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=True)
        _mock_cupy_available(monkeypatch)

        # Force ties detection to True
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute._detect_ties_gpu",
            lambda *a, **kw: True,
        )

        result = compute_reho_backend(
            data, neighborhood=7,
            prefer_gpu=True, require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"], f"Expected CPU to succeed: {result.get('errors')}"
        assert result["backend"] == "cpu-numpy", \
            f"Expected CPU fallback, got {result['backend']}"
        tie_warnings = [w for w in result.get("warnings", []) if "tied values" in w]
        assert len(tie_warnings) >= 1, "Expected ties warning in CPU result"

    def test_require_gpu_fails_when_ties_detected(self, monkeypatch):
        """require_gpu=True + ties detected → failure (no silent CPU fallback)."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=True)
        _mock_cupy_available(monkeypatch)

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute._detect_ties_gpu",
            lambda *a, **kw: True,
        )

        result = compute_reho_backend(
            data, neighborhood=7,
            prefer_gpu=True, require_gpu=True,
            allow_unvalidated_gpu=True,
        )
        assert not result["ok"], "Expected failure when require_gpu=True and ties detected"
        assert result["backend"] == "none"
        assert result["reho"] is None
        errors = result.get("errors", [])
        assert any("require_gpu=True" in e and "tied values" in e for e in errors), \
            f"Expected clear error message, got: {errors}"

    def test_require_gpu_fails_when_cupy_unavailable(self, monkeypatch):
        """require_gpu=True + CuPy not installed → failure."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_unavailable(monkeypatch)

        result = compute_reho_backend(
            data, neighborhood=7,
            require_gpu=True,
        )
        assert not result["ok"]
        assert result["backend"] == "none"
        errors = result.get("errors", [])
        assert any("CuPy is not available" in e for e in errors), \
            f"Expected CuPy unavailable error, got: {errors}"

    def test_uses_gpu_for_tie_free_data_with_opt_in(self, monkeypatch):
        """allow_unvalidated_gpu=True + no ties → GPU path used."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute._detect_ties_gpu",
            lambda *a, **kw: False,
        )

        # Mock GPU compute to return a success
        def mock_cupy(*a, **kw):
            return {
                "ok": True, "backend": "gpu-cupy",
                "reho": np.zeros(data.shape[:3], dtype=np.float32),
                "valid_voxel_count": 10, "skipped_voxel_count": 0,
                "warnings": [], "errors": [],
                "runtime_seconds": 0.01,
            }
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy",
            mock_cupy,
        )

        result = compute_reho_backend(
            data, neighborhood=7,
            prefer_gpu=True, require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"]
        assert result["backend"] == "gpu-cupy", \
            f"Expected GPU, got {result['backend']}"

    def test_cpu_only_without_allow_unvalidated(self, monkeypatch):
        """prefer_gpu=True + allow_unvalidated_gpu=False → CPU only (safety gate)."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        # Should never call GPU or ties detection
        gpu_called = [False]
        def mock_cupy(*a, **kw):
            gpu_called[0] = True
            return {"ok": True, "backend": "gpu-cupy"}
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy", mock_cupy,
        )

        ties_called = [False]
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute._detect_ties_gpu",
            lambda *a, **kw: ties_called.__setitem__(0, True) or False,
        )

        result = compute_reho_backend(
            data, neighborhood=7,
            prefer_gpu=True, require_gpu=False,
            allow_unvalidated_gpu=False,  # default
        )
        assert result["ok"]
        assert result["backend"] == "cpu-numpy", \
            f"Expected CPU when allow_unvalidated_gpu=False, got {result['backend']}"
        assert not gpu_called[0], "GPU should not be called without opt-in"
        assert not ties_called[0], "Ties detection should not be called without opt-in"
        safety_warnings = [w for w in result.get("warnings", [])
                          if "allow_unvalidated_gpu" in w]
        assert len(safety_warnings) >= 1, \
            "Expected safety-gate warning explaining allow_unvalidated_gpu"

    def test_allow_unvalidated_gpu_tie_free_uses_gpu(self, monkeypatch):
        """allow_unvalidated_gpu=True + ties free → GPU used."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute._detect_ties_gpu",
            lambda *a, **kw: False,
        )
        def mock_cupy(*a, **kw):
            return {
                "ok": True, "backend": "gpu-cupy",
                "reho": np.zeros(data.shape[:3], dtype=np.float32),
                "valid_voxel_count": 10, "skipped_voxel_count": 0,
                "warnings": [], "errors": [],
                "runtime_seconds": 0.01,
            }
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_cupy", mock_cupy,
        )

        result = compute_reho_backend(
            data, neighborhood=7,
            prefer_gpu=True, require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"]
        assert result["backend"] == "gpu-cupy"

    def test_ties_detection_error_conservative_fallback(self, monkeypatch):
        """Exception in ties detection → conservative: assume ties, fall back."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        _mock_cupy_available(monkeypatch)

        # Simulate detection crash
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute._detect_ties_gpu",
            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("detection crash")),
        )

        result = compute_reho_backend(
            data, neighborhood=7,
            prefer_gpu=True, require_gpu=False,
            allow_unvalidated_gpu=True,
        )
        assert result["ok"]
        assert result["backend"] == "cpu-numpy", \
            f"Expected conservative CPU fallback on detection error, got {result['backend']}"


class TestRehoBackendDirectCpu:
    """Test that prefer_gpu=False always uses CPU."""

    def test_prefer_gpu_false_uses_cpu(self):
        """prefer_gpu=False → CPU path directly."""
        from src.backend.app.tools.reho_compute import compute_reho_backend

        data = _make_data(ties=False)
        result = compute_reho_backend(
            data, neighborhood=7,
            prefer_gpu=False,
        )
        assert result["ok"]
        assert result["backend"] == "cpu-numpy"
