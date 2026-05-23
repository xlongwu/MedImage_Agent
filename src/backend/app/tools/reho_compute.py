from __future__ import annotations

import time
from typing import Any

import numpy as np


def _offsets(nb: int) -> list[tuple[int, int, int]]:
    off = []
    rng = [-1, 0, 1]
    for dx in rng:
        for dy in rng:
            for dz in rng:
                m = abs(dx) + abs(dy) + abs(dz)
                if nb == 7 and m <= 1:
                    off.append((dx, dy, dz))
                elif nb == 19 and m <= 2:
                    off.append((dx, dy, dz))
                elif nb == 27:
                    off.append((dx, dy, dz))
    return off


def compute_reho_numpy(
    data_4d: np.ndarray,
    neighborhood: int = 27,
    gm_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compute ReHo using NumPy (CPU). Extracted from reho.py core logic."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "cpu-numpy", "reho": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    nx, ny, nz, nt = data_4d.shape
    if nt < 2:
        return {"ok": False, "backend": "cpu-numpy", "reho": None,
                "warnings": [], "errors": ["Need >= 2 timepoints."],
                "runtime_seconds": 0.0}

    off = _offsets(neighborhood)
    reho_map = np.zeros((nx, ny, nz), dtype=np.float32)
    vc = 0
    sc = 0

    for x in range(1, nx - 1):
        for y in range(1, ny - 1):
            for z in range(1, nz - 1):
                if gm_mask is not None and not bool(gm_mask[x, y, z]):
                    sc += 1
                    continue
                series = []
                ok = True
                for dx, dy, dz in off:
                    xx, yy, zz = x + dx, y + dy, z + dz
                    if xx < 0 or yy < 0 or zz < 0 or xx >= nx or yy >= ny or zz >= nz:
                        ok = False
                        break
                    series.append(data_4d[xx, yy, zz, :])
                if not ok:
                    sc += 1
                    continue
                mat = np.stack(series, axis=1)
                if not np.isfinite(mat).all():
                    sc += 1
                    continue
                reho_map[x, y, z] = _kcc_numpy(mat)
                vc += 1

    duration = time.perf_counter() - t_start
    return {
        "ok": vc > 0,
        "backend": "cpu-numpy",
        "reho": reho_map,
        "valid_voxel_count": vc,
        "skipped_voxel_count": sc,
        "warnings": warnings,
        "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def _rank_cols_numpy(vals: np.ndarray) -> np.ndarray:
    T, K = vals.shape
    ranks = np.zeros_like(vals, dtype=np.float64)
    for t in range(T):
        row = vals[t, :]
        order = np.argsort(row, kind="mergesort")
        sv = row[order]
        rr = np.empty_like(row, dtype=np.float64)
        s = 0
        while s < len(sv):
            e = s + 1
            while e < len(sv) and sv[e] == sv[s]:
                e += 1
            rr[order[s:e]] = (s + 1 + e) / 2.0
            s = e
        ranks[t, :] = rr
    return ranks


def _kcc_numpy(tbv: np.ndarray) -> float:
    T, K = tbv.shape
    if T < 2 or K < 2:
        return 0.0
    r = _rank_cols_numpy(tbv)
    rs = np.sum(r, axis=0)
    rm = np.mean(rs)
    num = 12.0 * np.sum((rs - rm) ** 2)
    den = T**2 * (K**3 - K)
    return float(num / den) if den != 0 else 0.0


def compute_reho_cupy(
    data_4d: np.ndarray,
    neighborhood: int = 27,
    gm_mask: np.ndarray | None = None,
    z_chunk_size: int = 8,
) -> dict[str, Any]:
    """Compute ReHo using CuPy (GPU) with z-slice chunking."""
    import cupy as cp

    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "gpu-cupy", "reho": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    nx, ny, nz, nt = data_4d.shape
    if nt < 2:
        return {"ok": False, "backend": "gpu-cupy", "reho": None,
                "warnings": [], "errors": ["Need >= 2 timepoints."],
                "runtime_seconds": 0.0}

    off = _offsets(neighborhood)
    K = len(off)

    try:
        data_gpu = cp.asarray(data_4d, dtype=cp.float32)
    except Exception as exc:
        errors.append(f"Failed to transfer data to GPU: {exc}")
        return {"ok": False, "backend": "gpu-cupy", "reho": None,
                "warnings": warnings, "errors": errors,
                "runtime_seconds": time.perf_counter() - t_start}

    reho_gpu = cp.zeros((nx, ny, nz), dtype=cp.float32)
    vc_total = 0
    sc_total = 0

    # Build offset index arrays (shared across all chunks)
    dy_off = cp.array([o[1] for o in off], dtype=cp.int32)
    dz_off = cp.array([o[2] for o in off], dtype=cp.int32)

    for z_start in range(1, nz - 1, z_chunk_size):
        z_end = min(z_start + z_chunk_size, nz - 1)
        nz_chunk = z_end - z_start

        if nz_chunk <= 0:
            continue

        # Interior voxels in this chunk: x in [1,nx-1), y in [1,ny-1), z in [z_start,z_end)
        nv = (nx - 2) * (ny - 2) * nz_chunk

        # Build flat index maps
        x_idx = cp.arange(1, nx - 1, dtype=cp.int32)
        y_idx = cp.arange(1, ny - 1, dtype=cp.int32)
        z_idx = cp.arange(z_start, z_end, dtype=cp.int32)

        # Create grids: shape (nv,)
        xg, yg, zg = cp.meshgrid(x_idx, y_idx, z_idx, indexing="ij")
        x_flat = xg.ravel()
        y_flat = yg.ravel()
        z_flat = zg.ravel()

        # Extract neighborhood: for each interior voxel, gather K neighbors
        # neighbor_data shape: (nv, K, nt)
        neighbor_data = cp.zeros((nv, K, nt), dtype=cp.float32)

        for ki in range(K):
            nx_idx = x_flat + off[ki][0]
            ny_idx = y_flat + off[ki][1]
            nz_idx = z_flat + off[ki][2]
            # Clamp to valid range (should always be valid for interior voxels with 27-neighborhood)
            nx_idx = cp.clip(nx_idx, 0, nx - 1)
            ny_idx = cp.clip(ny_idx, 0, ny - 1)
            nz_idx = cp.clip(nz_idx, 0, nz - 1)
            neighbor_data[:, ki, :] = data_gpu[nx_idx, ny_idx, nz_idx, :]

        # Compute ranks per timepoint (vectorized)
        # neighbor_data: (nv, K, T) -> we need ranks along K axis for each T
        # Transpose to (nv, T, K) for easier processing
        nd_t = neighbor_data.transpose(0, 2, 1)  # (nv, T, K)

        # Double argsort for rank approximation (ties not handled, acceptable for MRI data)
        order = cp.argsort(cp.argsort(nd_t, axis=2), axis=2).astype(cp.float64) + 1.0  # (nv, T, K)

        # Sum ranks across time: R_s = sum_t rank(t, s)
        rs = cp.sum(order, axis=1)  # (nv, K)
        rm = cp.mean(rs, axis=1, keepdims=True)  # (nv, 1)
        num = 12.0 * cp.sum((rs - rm) ** 2, axis=1)  # (nv,)
        den = float(nt**2) * (K**3 - K)  # scalar

        # KCC values
        kcc = cp.where(den != 0, num / den, 0.0).astype(cp.float32)

        # Check for non-finite neighbor data
        finite_mask = cp.all(cp.isfinite(neighbor_data.reshape(nv, -1)), axis=1)
        kcc = cp.where(finite_mask, kcc, 0.0)

        # Apply GM mask if provided
        if gm_mask is not None:
            gm_gpu = cp.asarray(gm_mask, dtype=cp.bool_)
            gm_flat = gm_gpu[x_flat, y_flat, z_flat]
            kcc = cp.where(gm_flat, kcc, 0.0)
            sc_total += int(cp.count_nonzero(~gm_flat))
        else:
            sc_total += int(cp.count_nonzero(~cp.isfinite(neighbor_data.reshape(nv, -1)).all(axis=1)))

        vc_total += int(cp.count_nonzero(kcc != 0))

        # Write back to reho map
        reho_gpu[x_flat, y_flat, z_flat] = kcc

    cp.cuda.Stream.null.synchronize()
    reho_map = cp.asnumpy(reho_gpu)
    duration = time.perf_counter() - t_start

    return {
        "ok": bool(vc_total > 0),
        "backend": "gpu-cupy",
        "reho": reho_map,
        "valid_voxel_count": vc_total,
        "skipped_voxel_count": sc_total,
        "warnings": warnings,
        "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def compute_reho_backend(
    data_4d: np.ndarray,
    neighborhood: int = 27,
    gm_mask: np.ndarray | None = None,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    z_chunk_size: int = 8,
) -> dict[str, Any]:
    """Compute ReHo with automatic GPU/CPU backend selection."""
    gpu_available = False
    if prefer_gpu or require_gpu:
        try:
            import cupy as cp  # noqa: F401
            gpu_available = True
        except ImportError:
            pass

    if require_gpu and not gpu_available:
        return {
            "ok": False, "backend": "none",
            "reho": None, "valid_voxel_count": 0, "skipped_voxel_count": 0,
            "warnings": [],
            "errors": ["require_gpu=True but CuPy is not available."],
            "runtime_seconds": 0.0,
        }

    if gpu_available:
        result = compute_reho_cupy(data_4d, neighborhood, gm_mask, z_chunk_size)
        if result["ok"]:
            return result
        if require_gpu:
            return result
        # Fall through to CPU on GPU failure when prefer_gpu

    return compute_reho_numpy(data_4d, neighborhood, gm_mask)
