from __future__ import annotations

import time
from typing import Any

import numpy as np


def _generate_atlas(shape: tuple[int, int, int], roi_count: int):
    nx, ny, nz = shape
    atlas = np.zeros(shape, dtype=np.int16)
    edges = np.linspace(0, nx, roi_count + 1).astype(int)
    defs = []
    for idx in range(roi_count):
        s, e = int(edges[idx]), int(edges[idx + 1])
        if e <= s:
            continue
        atlas[s:e, :, :] = idx + 1
        defs.append({"label": idx + 1, "name": f"ROI_{idx+1}", "strategy": "synthetic_x_chunk", "x_start": s, "x_end": e})
    return atlas, defs


def _fisher_z(corr: np.ndarray) -> np.ndarray:
    c = np.clip(corr, -0.999999, 0.999999)
    z = np.arctanh(c)
    np.fill_diagonal(z, 0.0)
    return z


def compute_fc_numpy(
    data_4d: np.ndarray,
    atlas_3d: np.ndarray,
    generate_seed_map: bool = False,
) -> dict[str, Any]:
    """ROI-based functional connectivity on CPU via NumPy."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "cpu-numpy", "correlation_matrix": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    nx, ny, nz, nt = data_4d.shape
    if list(atlas_3d.shape[:3]) != [nx, ny, nz]:
        return {"ok": False, "backend": "cpu-numpy", "correlation_matrix": None,
                "warnings": [], "errors": ["Atlas shape mismatch."],
                "runtime_seconds": 0.0}

    labels = sorted(int(x) for x in np.unique(atlas_3d) if int(x) > 0)
    if not labels:
        return {"ok": False, "backend": "cpu-numpy", "correlation_matrix": None,
                "warnings": [], "errors": ["No valid ROI labels in atlas."],
                "runtime_seconds": 0.0}

    try:
        # Extract ROI time-series (mean across voxels per ROI)
        flat = data_4d.reshape((-1, nt)).astype(np.float64)
        rts = []
        for label in labels:
            mask = (atlas_3d.ravel() == label)
            if not np.any(mask):
                rts.append(np.zeros(nt, dtype=np.float64))
                warnings.append(f"ROI {label} is empty.")
                continue
            ts = np.mean(flat[mask, :], axis=0)
            rts.append(np.where(np.isfinite(ts), ts, 0.0))
        rta = np.vstack(rts) if rts else np.zeros((0, nt))

        # Correlation matrix via z-score + matmul
        zt = rta - rta.mean(axis=1, keepdims=True)
        stds = np.std(rta, axis=1)
        denom = stds[:, None] * stds[None, :] * (nt - 1)
        corr = (zt @ zt.T) / denom
        np.fill_diagonal(corr, 1.0)
        corr = np.where(np.isfinite(corr), corr, 0.0)

        fz = _fisher_z(corr)

        # Seed-to-voxel map
        seed_map = None
        seed_z_map = None
        if generate_seed_map and len(labels) > 0:
            seed_ts = rta[0]
            ss = float(np.std(seed_ts))
            if ss > 0:
                sc = seed_ts - np.mean(seed_ts)
                z_data = flat - flat.mean(axis=1, keepdims=True)
                sv = np.std(flat, axis=1)
                denom_seed = (nt - 1) * ss * sv
                seed_corr = np.where(denom_seed > 0, (z_data @ sc) / denom_seed, 0.0)
                seed_corr = np.where(np.isfinite(seed_corr), seed_corr, 0.0)
                seed_map = seed_corr.reshape((nx, ny, nz)).astype("float32")
                seed_z_map = np.arctanh(np.clip(seed_map, -0.999999, 0.999999)).astype("float32")
    except Exception as exc:
        return {"ok": False, "backend": "cpu-numpy", "correlation_matrix": None,
                "warnings": warnings, "errors": [str(exc)],
                "runtime_seconds": time.perf_counter() - t_start}

    duration = time.perf_counter() - t_start
    return {
        "ok": True, "backend": "cpu-numpy",
        "correlation_matrix": corr, "fisher_z_matrix": fz,
        "seed_correlation_map": seed_map, "seed_fisher_z_map": seed_z_map,
        "roi_count": len(labels), "timepoints": nt,
        "warnings": warnings, "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def compute_fc_cupy(
    data_4d: np.ndarray,
    atlas_3d: np.ndarray,
    generate_seed_map: bool = False,
) -> dict[str, Any]:
    """ROI-based functional connectivity on GPU via CuPy."""
    import cupy as cp

    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "gpu-cupy", "correlation_matrix": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    nx, ny, nz, nt = data_4d.shape
    if list(atlas_3d.shape[:3]) != [nx, ny, nz]:
        return {"ok": False, "backend": "gpu-cupy", "correlation_matrix": None,
                "warnings": [], "errors": ["Atlas shape mismatch."],
                "runtime_seconds": 0.0}

    labels = sorted(int(x) for x in np.unique(atlas_3d) if int(x) > 0)
    if not labels:
        return {"ok": False, "backend": "gpu-cupy", "correlation_matrix": None,
                "warnings": [], "errors": ["No valid ROI labels in atlas."],
                "runtime_seconds": 0.0}

    try:
        data_gpu = cp.asarray(data_4d.reshape((-1, nt)), dtype=cp.float64)
        atlas_gpu = cp.asarray(atlas_3d.ravel(), dtype=cp.int16)
    except Exception as exc:
        return {"ok": False, "backend": "gpu-cupy", "correlation_matrix": None,
                "warnings": warnings, "errors": [f"GPU transfer failed: {exc}"],
                "runtime_seconds": time.perf_counter() - t_start}

    try:
        rts = []
        for label in labels:
            mask = (atlas_gpu == label)
            count = cp.count_nonzero(mask)
            if count == 0:
                rts.append(cp.zeros(nt, dtype=cp.float64))
                warnings.append(f"ROI {label} is empty.")
                continue
            ts = cp.mean(data_gpu[mask, :], axis=0)
            rts.append(cp.where(cp.isfinite(ts), ts, 0.0))
        rta = cp.vstack(rts) if rts else cp.zeros((0, nt), dtype=cp.float64)

        # Correlation via z-score matmul
        zt = rta - cp.mean(rta, axis=1, keepdims=True)
        stds = cp.std(rta, axis=1)
        denom = cp.outer(stds, stds) * (nt - 1)
        corr_gpu = (zt @ zt.T) / denom
        cp.fill_diagonal(corr_gpu, 1.0)
        corr_gpu = cp.where(cp.isfinite(corr_gpu), corr_gpu, 0.0)

        fz_gpu = cp.arctanh(cp.clip(corr_gpu, -0.999999, 0.999999))
        cp.fill_diagonal(fz_gpu, 0.0)

        # Seed-to-voxel map
        seed_map = None
        seed_z_map = None
        if generate_seed_map and len(labels) > 0:
            seed_gpu = rta[0]
            ss = float(cp.std(seed_gpu))
            if ss > 0:
                sc = seed_gpu - cp.mean(seed_gpu)
                z_data = data_gpu - cp.mean(data_gpu, axis=1, keepdims=True)
                sv = cp.std(data_gpu, axis=1)
                denom_seed = (nt - 1) * ss * sv
                seed_corr_gpu = cp.where(denom_seed > 0, (z_data @ sc) / denom_seed, 0.0)
                seed_corr_gpu = cp.where(cp.isfinite(seed_corr_gpu), seed_corr_gpu, 0.0)
                seed_map = cp.asnumpy(seed_corr_gpu.reshape((nx, ny, nz)).astype(cp.float32))
                seed_z_map = np.arctanh(np.clip(seed_map, -0.999999, 0.999999)).astype("float32")

        cp.cuda.Stream.null.synchronize()
        corr = cp.asnumpy(corr_gpu)
        fz = cp.asnumpy(fz_gpu)
    except Exception as exc:
        return {"ok": False, "backend": "gpu-cupy", "correlation_matrix": None,
                "warnings": warnings, "errors": [f"GPU computation failed: {exc}"],
                "runtime_seconds": time.perf_counter() - t_start}

    duration = time.perf_counter() - t_start
    return {
        "ok": True, "backend": "gpu-cupy",
        "correlation_matrix": corr, "fisher_z_matrix": fz,
        "seed_correlation_map": seed_map, "seed_fisher_z_map": seed_z_map,
        "roi_count": len(labels), "timepoints": nt,
        "warnings": warnings, "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def compute_fc_backend(
    data_4d: np.ndarray,
    atlas_3d: np.ndarray,
    generate_seed_map: bool = False,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
) -> dict[str, Any]:
    """FC computation with automatic GPU/CPU backend selection."""
    gpu_available = False
    if prefer_gpu or require_gpu:
        try:
            import cupy as cp  # noqa: F401
            gpu_available = True
        except ImportError:
            pass

    if require_gpu and not gpu_available:
        return {
            "ok": False, "backend": "none", "correlation_matrix": None,
            "fisher_z_matrix": None, "warnings": [],
            "errors": ["require_gpu=True but CuPy is not available."],
            "runtime_seconds": 0.0,
        }

    if gpu_available:
        result = compute_fc_cupy(data_4d, atlas_3d, generate_seed_map)
        if result["ok"]:
            return result
        if require_gpu:
            return result

    return compute_fc_numpy(data_4d, atlas_3d, generate_seed_map)
