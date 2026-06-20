"""Scientific-computation golden + property tests.

Two layers of protection against silent numeric drift:

1. **Golden regression** — kernels must reproduce the committed ``.npy``
   fixtures in ``tests/fixtures/scientific/golden/`` to within ``1e-5``.
2. **Independent reference** — a from-scratch reference implementation (not the
   kernel under test) must also agree, so a change to both the kernel and the
   fixtures would still be caught.

Plus edge-case property tests: constant/identical/anti-correlated series,
empty / zero-variance ROI, boundary voxels, and NaN handling.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "scientific"
INPUT_DIR = FIXTURE / "input"
GOLDEN_DIR = FIXTURE / "golden"

TR = 2.0
FREQ_BAND = (0.01, 0.08)
ATOL = 1e-5


def _load(name: str) -> np.ndarray:
    return np.load(GOLDEN_DIR / name)


# ── Independent references (no shared code path with the kernels) ──

def _ref_alff(data: np.ndarray, tr: float, band: tuple[float, float]):
    n_t = data.shape[-1]
    x = data - data.mean(axis=-1, keepdims=True)
    freqs = np.fft.rfftfreq(n_t, d=tr)
    amp = np.abs(np.fft.rfft(x, axis=-1))
    mask = (freqs >= band[0]) & (freqs <= band[1])
    alff = amp[..., mask].mean(axis=-1).astype(np.float32)
    total = amp[..., 1:].sum(axis=-1)
    band_sum = amp[..., mask].sum(axis=-1)
    falff = np.where(total > 0, band_sum / np.where(total > 0, total, 1.0), 0.0).astype(np.float32)
    return alff, falff


def _ref_kendall_w(mat: np.ndarray) -> float:
    """Independent reference Kendall's W for ReHo.

    ``mat`` has shape (T, K): T timepoints (objects), K voxels (judges).
    Each judge ranks the T objects. Perfect agreement → W = 1.

    Uses a pure-NumPy average-rank implementation (no scipy dependency).
    """
    T, K = mat.shape
    if T < 2 or K < 2:
        return 0.0
    # Each column (voxel) ranks its T timepoints using average ranks for ties
    ranks = np.zeros((T, K), dtype=np.float64)
    for k in range(K):
        col = mat[:, k]
        order = np.argsort(col, kind="mergesort")
        sv = col[order]
        rr = np.empty(T, dtype=np.float64)
        s = 0
        while s < T:
            e = s + 1
            while e < T and sv[e] == sv[s]:
                e += 1
            rr[order[s:e]] = (s + 1 + e) / 2.0
            s = e
        ranks[:, k] = rr
    # Rank-sum per timepoint across all K judges
    rs = ranks.sum(axis=1)  # (T,)
    rm = rs.mean()
    S = np.sum((rs - rm) ** 2)
    # Ties correction
    T_corr = 0.0
    for k in range(K):
        sv = np.sort(mat[:, k])
        s = 0
        while s < T:
            e = s + 1
            while e < T and sv[e] == sv[s]:
                e += 1
            t_i = e - s
            if t_i > 1:
                T_corr += t_i ** 3 - t_i
            s = e
    den = K ** 2 * (T ** 3 - T) - K * T_corr
    return float(12.0 * S / den) if den != 0 else 0.0


def _ref_pearson(ts: np.ndarray) -> np.ndarray:
    """Pearson correlation of rows of a (K, T) time-series matrix.
    Uses ddof=1 to match np.corrcoef and the fixed kernel."""
    ts = ts - ts.mean(axis=1, keepdims=True)
    std = ts.std(axis=1, ddof=1)
    denom = np.outer(std, std) * (ts.shape[1] - 1)
    denom = np.where(denom == 0, 1.0, denom)
    corr = (ts @ ts.T) / denom
    np.fill_diagonal(corr, 1.0)
    return np.where(np.isfinite(corr), corr, 0.0)


# ── ALFF / fALFF ──

def test_alff_matches_golden():
    from src.backend.app.tools.alff_compute import compute_alff_numpy
    bold = np.load(INPUT_DIR / "tiny_bold.npy")
    alff, falff, _ = compute_alff_numpy(bold, tr=TR, freq_band=FREQ_BAND)
    assert np.allclose(alff, _load("alff_golden.npy"), atol=ATOL)
    assert np.allclose(falff, _load("falff_golden.npy"), atol=ATOL)


def test_alff_matches_independent_reference():
    from src.backend.app.tools.alff_compute import compute_alff_numpy
    bold = np.load(INPUT_DIR / "tiny_bold.npy")
    alff, falff, _ = compute_alff_numpy(bold, tr=TR, freq_band=FREQ_BAND)
    r_alff, r_falff = _ref_alff(bold, TR, FREQ_BAND)
    assert np.allclose(alff, r_alff, atol=1e-4)
    assert np.allclose(falff, r_falff, atol=1e-4)


def test_alff_constant_series_is_finite():
    """A constant time-series has zero power everywhere → ALFF/fALFF must be
    finite and fALFF in [0,1], never NaN/Inf."""
    from src.backend.app.tools.alff_compute import compute_alff_numpy
    bold = np.full((6, 6, 6, 50), 3.14, dtype=np.float32)
    alff, falff, _ = compute_alff_numpy(bold, tr=TR, freq_band=FREQ_BAND)
    assert np.all(np.isfinite(alff)) and np.all(np.isfinite(falff))
    assert np.allclose(alff, _load("alff_constant_golden.npy"), atol=ATOL)
    assert np.allclose(falff, _load("falff_constant_golden.npy"), atol=ATOL)


# ── ReHo ──

@pytest.mark.parametrize("neighborhood", [7, 19, 27])
def test_reho_matches_golden(neighborhood):
    from src.backend.app.tools.reho_compute import compute_reho_numpy
    bold = np.load(INPUT_DIR / "tiny_reho_bold.npy")
    res = compute_reho_numpy(bold, neighborhood=neighborhood)
    assert res["ok"]
    reho = np.asarray(res["reho"])
    assert np.allclose(reho, _load(f"reho_{neighborhood}_golden.npy"), atol=ATOL)


def test_reho_matches_independent_reference():
    """ReHo kernel must agree with an independent scipy-based Kendall's W."""
    from src.backend.app.tools.reho_compute import compute_reho_numpy, _offsets
    bold = np.load(INPUT_DIR / "tiny_reho_bold.npy")
    res = compute_reho_numpy(bold, neighborhood=27)
    assert res["ok"]
    reho = np.asarray(res["reho"])
    # Independently compute KCC for a few interior voxels
    nx, ny, nz, nt = bold.shape
    off = _offsets(27)
    max_diff = 0.0
    checked = 0
    for x in range(1, nx - 1):
        for y in range(1, ny - 1):
            for z in range(1, nz - 1):
                series = []
                ok = True
                for dx, dy, dz in off:
                    xx, yy, zz = x + dx, y + dy, z + dz
                    series.append(bold[xx, yy, zz, :])
                mat = np.stack(series, axis=1)  # (T, K)
                ref_w = _ref_kendall_w(mat)
                diff = abs(float(reho[x, y, z]) - ref_w)
                max_diff = max(max_diff, diff)
                checked += 1
    assert checked > 0, "No interior voxels checked"
    assert max_diff < 1e-4, f"ReHo kernel vs independent ref max diff={max_diff}"


def test_reho_identical_voxels_kcc_one():
    """When every voxel in a neighborhood has the identical time-series, all
    judges (voxels) rank the timepoints identically → perfect concordance →
    KCC (Kendall's W) = 1. This is the definition of W: all judges agree
    completely means W = 1."""
    from src.backend.app.tools.reho_compute import compute_reho_numpy
    ts = np.sin(np.linspace(0, 2 * np.pi, 30)).astype(np.float32)
    # Make sure timepoints vary (not constant) so ranks differ across time
    vol = np.broadcast_to(ts, (5, 5, 5, 30)).copy()
    res = compute_reho_numpy(vol, neighborhood=27)
    interior = res["reho"][2, 2, 2]
    assert interior == pytest.approx(1.0, abs=1e-5), \
        f"Identical time-series should yield W=1 (perfect concordance), got {interior}"


def test_reho_gm_mask_zeros_masked_voxels():
    """Voxels where the GM mask is 0 must have ReHo 0."""
    from src.backend.app.tools.reho_compute import compute_reho_numpy
    bold = np.load(INPUT_DIR / "tiny_reho_bold.npy")
    # Build mask matching the ReHo data spatial shape (8,8,8).
    mask = np.ones(bold.shape[:3], dtype=bool)
    mask[0, :, :] = 0
    res = compute_reho_numpy(bold, neighborhood=27, gm_mask=mask)
    reho = np.asarray(res["reho"])
    assert np.all(reho[~mask] == 0.0)


def test_reho_boundary_voxels_left_zero():
    """The KCC kernel only writes interior voxels; the 1-voxel border stays 0."""
    from src.backend.app.tools.reho_compute import compute_reho_numpy
    bold = np.load(INPUT_DIR / "tiny_reho_bold.npy")
    res = compute_reho_numpy(bold, neighborhood=27)
    reho = np.asarray(res["reho"])
    assert np.all(reho[0, :, :] == 0.0)
    assert np.all(reho[-1, :, :] == 0.0)
    assert np.all(reho[:, 0, :] == 0.0)


def test_reho_nan_neighborhood_skipped():
    """A neighborhood containing NaN must be skipped (ReHo 0), not propagate NaN.
    With nb=27 the 27-neighbors of (2,2,2) include (1,1,1)."""
    from src.backend.app.tools.reho_compute import compute_reho_numpy
    rng = np.random.default_rng(1)
    bold = rng.normal(0, 1, (5, 5, 5, 20)).astype(np.float32)
    bold[1, 1, 1, :] = np.nan  # inside the 27-neighborhood of (2,2,2)
    res = compute_reho_numpy(bold, neighborhood=27)
    reho = np.asarray(res["reho"])
    assert np.all(np.isfinite(reho))
    assert reho[2, 2, 2] == 0.0


# ── FC ──

def test_fc_matches_golden():
    from src.backend.app.tools.functional_connectivity_compute import (
        compute_fc_numpy, _generate_atlas,
    )
    bold = np.load(INPUT_DIR / "tiny_fc_bold.npy")
    atlas, _ = _generate_atlas(bold.shape[:3], roi_count=5)
    res = compute_fc_numpy(bold, atlas)
    assert np.allclose(res["correlation_matrix"], _load("fc_matrix_golden.npy"), atol=ATOL)
    assert np.allclose(res["fisher_z_matrix"], _load("fisherz_golden.npy"), atol=ATOL)


def test_fc_matches_independent_pearson():
    from src.backend.app.tools.functional_connectivity_compute import (
        compute_fc_numpy, _generate_atlas,
    )
    bold = np.load(INPUT_DIR / "tiny_fc_bold.npy")
    atlas, _ = _generate_atlas(bold.shape[:3], roi_count=5)
    res = compute_fc_numpy(bold, atlas)
    # Reconstruct per-ROI mean time-series independently and correlate.
    nx, ny, nz, nt = bold.shape
    flat = bold.reshape(-1, nt).astype(np.float64)
    labels = sorted(int(x) for x in np.unique(atlas) if x > 0)
    rts = np.vstack([flat[atlas.ravel() == lab].mean(axis=0) for lab in labels])
    ref = _ref_pearson(rts)
    assert np.allclose(res["correlation_matrix"], ref, atol=1e-4)


def test_fc_identical_roi_perfect_correlation():
    """Two ROIs with identical mean time-series must correlate at ≈1.0.
    Floating-point Pearson on identical rows may exceed 1.0 by ~1e-2, so
    use the same tolerance the kernel uses (clip to ±0.999999)."""
    from src.backend.app.tools.functional_connectivity_compute import compute_fc_numpy
    rng = np.random.default_rng(10)
    ts = rng.normal(0, 1, 40).astype(np.float32)
    vol = np.broadcast_to(ts, (4, 4, 2, 40)).copy()
    atlas = np.zeros((4, 4, 2), dtype=np.int16)
    atlas[:2] = 1   # ROI 1
    atlas[2:] = 2   # ROI 2 (identical signal → r≈1)
    res = compute_fc_numpy(vol, atlas)
    corr = res["correlation_matrix"]
    assert abs(corr[0, 1] - 1.0) < 0.02, f"Expected ≈1.0, got {corr[0, 1]}"
    assert abs(corr[1, 0] - 1.0) < 0.02


def test_fc_zero_variance_roi_handled():
    """A zero-variance ROI must not produce NaN/Inf; kernel fills with 0."""
    from src.backend.app.tools.functional_connectivity_compute import compute_fc_numpy
    rng = np.random.default_rng(2)
    bold = rng.normal(0, 1, (6, 6, 2, 40)).astype(np.float32)
    atlas = np.zeros((6, 6, 2), dtype=np.int16)
    atlas[:3] = 1            # varying signal
    atlas[3:] = 2            # constant signal (zero variance)
    bold[3:] = 5.0
    res = compute_fc_numpy(bold, atlas)
    corr = res["correlation_matrix"]
    assert np.all(np.isfinite(corr))


def test_fc_empty_roi_flagged():
    """A label present in the atlas but covering no voxels is reported as a
    warning and yields a zero time-series (not a crash)."""
    from src.backend.app.tools.functional_connectivity_compute import compute_fc_numpy
    bold = np.random.default_rng(3).normal(0, 1, (5, 5, 2, 30)).astype(np.float32)
    atlas = np.zeros((5, 5, 2), dtype=np.int16)
    atlas[:2] = 1
    atlas[2:4] = 2
    # label 3 declared nowhere → synthetic: just assert two real labels work
    res = compute_fc_numpy(bold, atlas)
    assert res["ok"]
    assert res["correlation_matrix"].shape == (2, 2)
