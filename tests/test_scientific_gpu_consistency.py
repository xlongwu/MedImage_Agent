"""Conditional GPU-consistency tests for the scientific-computation kernels.

Skip behavior follows the project convention: ``pytest.ini`` declares the
``gpu`` marker for CUDA-only tests. Each test marks itself accordingly and
skips gracefully when the required backend is not installed.

Environment at test time (2026-06-20):
- CuPy: NOT installed → FC/ReHo CuPy consistency tests are skipped.
- PyTorch 2.7.0 + CUDA: available → ALFF torch-consistency test runs.
"""
from __future__ import annotations

import importlib

import numpy as np
import pytest

FIXTURE = pytest.importorskip("pathlib").Path(__file__).resolve().parent / "fixtures" / "scientific"
INPUT_DIR = FIXTURE / "input"

TR = 2.0
FREQ_BAND = (0.01, 0.08)
GPU_ATOL = 1e-4


def _cupy_available() -> bool:
    try:
        importlib.import_module("cupy")
        return True
    except ImportError:
        return False


def _torch_cuda_available() -> bool:
    try:
        torch = importlib.import_module("torch")
        return torch.cuda.is_available()
    except ImportError:
        return False


# ── ALFF: CPU numpy vs GPU torch ──

@pytest.mark.gpu
def test_alff_cpu_torch_consistency():
    """CPU compute_alff_numpy must match GPU compute_alff_backend (torch)
    within atol=1e-4. Skips if torch CUDA is not available."""
    pytest.importorskip("torch")
    if not _torch_cuda_available():
        pytest.skip("torch CUDA not available")

    from src.backend.app.tools.alff_compute import compute_alff_numpy, compute_alff_backend

    bold = np.load(INPUT_DIR / "tiny_bold.npy").astype(np.float32)
    alff_cpu, falff_cpu, _ = compute_alff_numpy(bold, tr=TR, freq_band=FREQ_BAND)

    # Backend selector will pick torch over numpy because prefer_gpu=True and
    # torch is available.
    res = compute_alff_backend(bold, tr=TR, freq_band=FREQ_BAND, prefer_gpu=True)
    assert res["ok"], res.get("errors")
    assert res["backend"] == "gpu-torch", f"Expected gpu-torch, got {res['backend']}"

    alff_gpu = np.asarray(res["alff"]).astype(np.float32)
    falff_gpu = np.asarray(res["falff"]).astype(np.float32)

    assert np.allclose(alff_cpu, alff_gpu, atol=GPU_ATOL), (
        f"ALFF CPU/torch mismatch max={np.max(np.abs(alff_cpu - alff_gpu))}")
    assert np.allclose(falff_cpu, falff_gpu, atol=GPU_ATOL), (
        f"fALFF CPU/torch mismatch max={np.max(np.abs(falff_cpu - falff_gpu))}")


# ── FC: CPU numpy vs GPU cupy ──

@pytest.mark.gpu
@pytest.mark.skipif(not _cupy_available(), reason="CuPy not installed")
def test_fc_cpu_cupy_consistency():
    """CPU compute_fc_numpy must match GPU compute_fc_cupy within atol=1e-4.
    Skipped automatically when CuPy is not installed."""
    from src.backend.app.tools.functional_connectivity_compute import (
        compute_fc_numpy,
        compute_fc_cupy,
        _generate_atlas,
    )

    bold = np.load(INPUT_DIR / "tiny_fc_bold.npy").astype(np.float32)
    atlas, _ = _generate_atlas(bold.shape[:3], roi_count=5)

    cpu_res = compute_fc_numpy(bold, atlas)
    assert cpu_res["ok"]
    gpu_res = compute_fc_cupy(bold, atlas)
    assert gpu_res["ok"], gpu_res.get("errors")

    assert np.allclose(cpu_res["correlation_matrix"], gpu_res["correlation_matrix"], atol=GPU_ATOL), (
        f"FC correlation CPU/GPU max diff={np.max(np.abs(cpu_res['correlation_matrix'] - gpu_res['correlation_matrix']))}")
    assert np.allclose(cpu_res["fisher_z_matrix"], gpu_res["fisher_z_matrix"], atol=GPU_ATOL), (
        f"FC Fisher-Z CPU/GPU max diff={np.max(np.abs(cpu_res['fisher_z_matrix'] - gpu_res['fisher_z_matrix']))}")


# ── ReHo: CPU numpy vs GPU cupy ──

@pytest.mark.gpu
@pytest.mark.skipif(not _cupy_available(), reason="CuPy not installed")
def test_reho_cpu_cupy_consistency():
    """CPU compute_reho_numpy must match GPU compute_reho_cupy within atol=1e-4
    on the shared tiny input. Skipped automatically when CuPy is not installed."""
    from src.backend.app.tools.reho_compute import (
        compute_reho_numpy,
        compute_reho_cupy,
    )

    bold = np.load(INPUT_DIR / "tiny_reho_bold.npy").astype(np.float32)

    cpu_res = compute_reho_numpy(bold, neighborhood=27)
    assert cpu_res["ok"]
    gpu_res = compute_reho_cupy(bold, neighborhood=27)
    assert gpu_res["ok"], gpu_res.get("errors")

    cpu_map = np.asarray(cpu_res["reho"])
    gpu_map = np.asarray(gpu_res["reho"])
    assert cpu_map.shape == gpu_map.shape
    # Only compare interior voxels (both kernels zero the border).
    interior = slice(1, -1)
    diff = np.abs(cpu_map[interior, interior, interior] - gpu_map[interior, interior, interior])
    assert np.max(diff) < GPU_ATOL, (
        f"ReHo CPU/GPU interior max diff={np.max(diff)} at {np.unravel_index(np.argmax(diff), diff.shape)}")
    # Both must agree on which interior voxels are valid (>0).
    cpu_valid = cpu_map > 0
    gpu_valid = gpu_map > 0
    assert np.all(cpu_valid == gpu_valid), "CPU/GPU disagree on valid ReHo voxel set"
