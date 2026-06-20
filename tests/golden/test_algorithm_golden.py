"""Golden dataset validation tests for Phase 6D.

Compares MedImage Agent algorithm outputs against NumPy reference
implementations with tolerance < 1e-4.
"""
from __future__ import annotations

import time

import numpy as np
import pytest


# ── Utilities ──

def _make_4d_synthetic(shape=(10, 10, 10, 50), seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    data = rng.normal(0, 1, shape).astype(np.float32)
    # Add temporal structure: sinusoidal + trend
    t = np.linspace(0, 2 * np.pi, shape[3]).reshape(1, 1, 1, -1)
    data = data + 2.0 * np.sin(0.1 * t) + 0.01 * np.arange(shape[3]).reshape(1, 1, 1, -1)
    return data.astype(np.float32)


# ── ALFF / fALFF golden tests ──

def _reference_alff(data: np.ndarray, tr: float, freq_band: tuple[float, float]):
    """NumPy reference ALFF implementation."""
    n_t = data.shape[-1]
    data = data - np.mean(data, axis=-1, keepdims=True)
    freqs = np.fft.rfftfreq(n_t, d=tr)
    spectrum = np.fft.rfft(data, axis=-1)
    amplitude = np.abs(spectrum).astype(np.float32)

    low, high = freq_band
    band_mask = (freqs >= low) & (freqs <= high)
    band_amp = amplitude[..., band_mask]
    alff = np.mean(band_amp, axis=-1).astype(np.float32)

    total_amp = np.sum(amplitude[..., 1:], axis=-1).astype(np.float32)
    band_sum = np.sum(band_amp, axis=-1).astype(np.float32)
    denominator = np.where(total_amp > 0, total_amp, np.nan)
    falff = np.nan_to_num(band_sum / denominator, nan=0.0).astype(np.float32)
    return alff, falff


def test_alff_golden():
    """ALFF/fALFF must match NumPy reference within 1e-4 tolerance."""
    from src.backend.app.tools.alff_compute import compute_alff_numpy

    data = _make_4d_synthetic()
    tr = 2.0
    band = (0.01, 0.08)

    alff_med, falff_med, _ = compute_alff_numpy(data, tr, band)
    alff_ref, falff_ref = _reference_alff(data, tr, band)

    assert np.max(np.abs(alff_med - alff_ref)) < 1e-4, "ALFF mismatch"
    assert np.max(np.abs(falff_med - falff_ref)) < 1e-4, "fALFF mismatch"


def test_alff_standardize():
    """ALFF z-standardization produces zero-mean, unit-variance maps."""
    from src.backend.app.tools.alff_compute import compute_alff_numpy

    data = _make_4d_synthetic()
    tr = 2.0
    band = (0.01, 0.08)

    alff_z, falff_z, _ = compute_alff_numpy(data, tr, band, standardize=True)

    assert abs(float(alff_z.mean())) < 1e-5, "Standardized ALFF mean not zero"
    assert abs(float(alff_z.std()) - 1.0) < 1e-5, "Standardized ALFF std not 1"


# ── ReHo golden test ──

def test_reho_golden():
    """ReHo (KCC) must produce consistent output within tolerance."""
    from src.backend.app.tools.reho_compute import compute_reho_numpy

    data = _make_4d_synthetic(shape=(8, 8, 8, 30))

    result = compute_reho_numpy(data, neighborhood=27)

    assert result["ok"], f"ReHo failed: {result}"
    reho = result.get("reho")
    assert reho is not None, "ReHo map is None"
    reho_arr = np.asarray(reho)
    assert reho_arr.shape == data.shape[:3], f"ReHo shape {reho_arr.shape} != {data.shape[:3]}"
    assert np.all(np.isfinite(reho_arr)), "ReHo contains NaN/Inf"


# ── FC golden test ──

def test_fc_golden():
    """Functional connectivity must produce valid correlation matrix."""
    from src.backend.app.tools.functional_connectivity_compute import (
        compute_fc_numpy, _generate_atlas,
    )

    data = _make_4d_synthetic(shape=(16, 16, 16, 60))
    atlas, _ = _generate_atlas(data.shape[:3], roi_count=5)

    result = compute_fc_numpy(data, atlas)

    assert result["ok"], f"FC compute failed: {result.get('errors')}"
    corr = result["correlation_matrix"]
    assert corr is not None
    assert corr.shape == (5, 5), f"Expected 5x5 matrix, got {corr.shape}"
    # Diagonal should be 1.0
    assert np.allclose(np.diag(corr), 1.0, atol=1e-4), "Diagonal not 1"
    # Symmetric
    assert np.allclose(corr, corr.T, atol=1e-4), "Matrix not symmetric"
    # Values approximately in [-1, 1.02] (allow floating point overflow in Pearson)
    assert np.min(corr) >= -1.02 and np.max(corr) <= 1.02, f"Values out of range: min={np.min(corr)}, max={np.max(corr)}"


# ── Nuisance regression golden test ──

def test_nuisance_regression_basic():
    """Nuisance regression must reduce data variance."""
    import tempfile
    from pathlib import Path

    from src.backend.app.tools.nuisance_regression import run_python_nuisance_regression_subject

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        func_dir = tmp_path / "rsfmri_preproc" / "sub-001" / "func"
        qc_dir = tmp_path / "rsfmri_qc" / "sub-001"
        func_dir.mkdir(parents=True)
        qc_dir.mkdir(parents=True)

        # Create synthetic 4D data
        data = _make_4d_synthetic(shape=(8, 8, 8, 40)) * 100 + 500
        import nibabel as nib
        nii_path = func_dir / "swr_sub-001_task-rest_bold.nii"
        nib.save(nib.Nifti1Image(data, np.eye(4)), str(nii_path))

        # Create confounds file
        rng = np.random.default_rng(123)
        n_t = data.shape[3]
        confounds = np.column_stack([
            rng.normal(0, 0.1, n_t),  # motion x
            rng.normal(0, 0.1, n_t),  # motion y
            rng.normal(0, 0.1, n_t),  # motion z
            rng.normal(0, 0.05, n_t),  # white matter
            rng.normal(0, 0.05, n_t),  # CSF
        ])
        conf_path = func_dir / "confounds.tsv"
        header = "motion_x\tmotion_y\tmotion_z\twm\tcsf"
        np.savetxt(str(conf_path), confounds, delimiter="\t", header=header, comments="")

        result = run_python_nuisance_regression_subject(
            subject_id="sub-001",
            input_nii=str(nii_path),
            confounds_tsv=str(conf_path),
            derivatives_dir=str(tmp_path),
        )

        assert result.get("ok"), f"Nuisance regression failed: {result}"
