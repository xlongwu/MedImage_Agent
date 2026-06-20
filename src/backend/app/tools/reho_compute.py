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


def _rank_along_time_numpy(vals: np.ndarray) -> np.ndarray:
    """Rank timepoints within each voxel's time-series.

    ``vals`` has shape (T, K): T timepoints, K neighborhood voxels.
    Each column k is one voxel's time-series of length T. We rank the T
    timepoints *within* each column (voxel), so each voxel acts as a
    "judge" ranking the T "objects" (timepoints) by signal intensity.

    Ties are assigned average ranks. Returns an array of shape (T, K).
    """
    T, K = vals.shape
    ranks = np.zeros_like(vals, dtype=np.float64)
    for k in range(K):
        col = vals[:, k]
        order = np.argsort(col, kind="mergesort")
        sv = col[order]
        rr = np.empty(T, dtype=np.float64)
        s = 0
        while s < T:
            e = s + 1
            while e < T and sv[e] == sv[s]:
                e += 1
            rr[order[s:e]] = (s + 1 + e) / 2.0  # average rank
            s = e
        ranks[:, k] = rr
    return ranks


def _tie_correction_numpy(vals: np.ndarray) -> float:
    """Compute Kendall's W tie correction term summed across all judges.

    For each column (voxel/judge), sum(t_i^3 - t_i) where t_i is the size
    of each tied group. Returns the total across all K judges.
    """
    T, K = vals.shape
    total = 0.0
    for k in range(K):
        col = vals[:, k]
        sv = np.sort(col)
        s = 0
        while s < T:
            e = s + 1
            while e < T and sv[e] == sv[s]:
                e += 1
            t_i = e - s
            if t_i > 1:
                total += t_i ** 3 - t_i
            s = e
    return total


def _kcc_numpy(tbv: np.ndarray) -> float:
    """Kendall's coefficient of concordance (W) for ReHo.

    ``tbv`` has shape (T, K): T timepoints (objects), K neighborhood voxels
    (judges). Each voxel judges the T timepoints by ranking its own
    time-series. Perfect agreement (all voxels rank timepoints identically)
    yields W = 1.

    Formula (with ties correction):

        W = 12 * S / (K^2 * (T^3 - T) - K * T_corr)

    where:
        S   = sum over timepoints of (rank_sum - mean_rank_sum)^2
        K   = number of judges (neighborhood voxels)
        T   = number of objects (timepoints)
        T_corr = sum across all judges of sum(t_i^3 - t_i)
    """
    T, K = tbv.shape
    if T < 2 or K < 2:
        return 0.0
    r = _rank_along_time_numpy(tbv)          # (T, K): rank of each timepoint per voxel
    rs = np.sum(r, axis=1)                     # (T,): rank-sum per timepoint across K judges
    rm = np.mean(rs)                            # mean rank-sum
    num = 12.0 * np.sum((rs - rm) ** 2)
    tie_corr = _tie_correction_numpy(tbv)
    den = K ** 2 * (T ** 3 - T) - K * tie_corr
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

        # Compute ranks per timepoint within each voxel (vectorized).
        # neighbor_data: (nv, K, T) — for each voxel, K neighbors each with T timepoints.
        # Each of the K voxels is a "judge" that ranks its T timepoints.
        # So we rank along axis=2 (the T axis) — rank timepoints within each voxel.
        # Double argsort gives ranks (1-based after +1.0).
        order = cp.argsort(cp.argsort(neighbor_data, axis=2), axis=2).astype(cp.float64) + 1.0  # (nv, K, T)

        # Sum ranks across K judges (axis=1) for each timepoint → rank_sum per timepoint.
        rs = cp.sum(order, axis=1)  # (nv, T)
        rm = cp.mean(rs, axis=1, keepdims=True)  # (nv, 1)
        num = 12.0 * cp.sum((rs - rm) ** 2, axis=1)  # (nv,)

        # Denominator: K^2 * (T^3 - T). Ties correction omitted for GPU speed;
        # CPU path handles ties exactly. For typical MRI data ties are rare.
        den = float(K ** 2) * (nt ** 3 - nt)  # scalar

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


def _detect_ties_gpu(data_4d: np.ndarray, sample_voxels: int = 1000) -> bool:
    """Quick heuristic: check if the data likely contains tied values.

    Ties break the GPU double-argsort ranking (which does not apply average
    ranks or ties correction). We sample a small subset of voxels and check
    for duplicate values within their time-series. This is a fast heuristic,
    not an exhaustive check.

    Returns True if ties are detected, meaning CPU fallback is needed.
    """
    if data_4d.ndim != 4:
        return False
    nx, ny, nz, nt = data_4d.shape
    rng = np.random.default_rng(0)
    # Sample interior voxels
    xs = rng.integers(1, max(2, nx - 1), size=min(sample_voxels, (nx - 2) * (ny - 2) * (nz - 2)))
    ys = rng.integers(1, max(2, ny - 1), size=len(xs))
    zs = rng.integers(1, max(2, nz - 1), size=len(xs))
    for i in range(len(xs)):
        ts = data_4d[xs[i], ys[i], zs[i], :]
        if ts.size > 1 and np.unique(ts).size < ts.size:
            return True
    return False


def compute_reho_backend(
    data_4d: np.ndarray,
    neighborhood: int = 27,
    gm_mask: np.ndarray | None = None,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    z_chunk_size: int = 8,
    allow_unvalidated_gpu: bool = False,
) -> dict[str, Any]:
    """Compute ReHo with automatic GPU/CPU backend selection.

    GPU path does NOT implement ties correction (average ranks + tie factor).
    Ties detection is a probabilistic heuristic (random sampling of voxels)
    and cannot guarantee safety.

    By default, the GPU path is **disabled** even when ``prefer_gpu=True``
    because the GPU backend lacks ties correction.  Callers that want to use
    the GPU despite this must set ``allow_unvalidated_gpu=True`` and accept
    the risk.

    When ``require_gpu=True`` and ties are detected, this function returns
    failure immediately — it never silently falls back to CPU in that case.
    """
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

    # Safety gate: GPU ties correction is unimplemented and ties detection is
    # probabilistic.  Unless the caller explicitly opts in, route to CPU.
    if prefer_gpu and not require_gpu and not allow_unvalidated_gpu:
        cpu_result = compute_reho_numpy(data_4d, neighborhood, gm_mask)
        cpu_result.setdefault("warnings", []).append(
            "ReHo GPU path disabled: GPU backend lacks ties correction and "
            "ties detection is probabilistic (random voxel sampling). Using "
            "CPU path. Set allow_unvalidated_gpu=True to opt into GPU at "
            "your own risk."
        )
        return cpu_result

    # Auto-fallback: GPU path does not handle ties. Detect and fall back.
    use_gpu = gpu_available
    ties_warning = ""
    if use_gpu:
        try:
            has_ties = _detect_ties_gpu(data_4d)
        except Exception:
            has_ties = True  # conservative: fall back on detection error
        if has_ties:
            if require_gpu:
                return {
                    "ok": False, "backend": "none",
                    "reho": None,
                    "valid_voxel_count": 0, "skipped_voxel_count": 0,
                    "warnings": [],
                    "errors": [
                        "require_gpu=True but GPU ReHo cannot proceed: "
                        "tied values were detected and the GPU backend does "
                        "not implement ties correction. Use "
                        "require_gpu=False to allow CPU fallback."
                    ],
                    "runtime_seconds": 0.0,
                }
            use_gpu = False
            ties_warning = (
                "ReHo GPU path skipped: tied values detected in data. "
                "GPU does not implement ties correction; using CPU path."
            )

    if use_gpu:
        result = compute_reho_cupy(data_4d, neighborhood, gm_mask, z_chunk_size)
        if result["ok"]:
            return result
        if require_gpu:
            if ties_warning:
                result["warnings"].append(ties_warning)
            return result
        # Fall through to CPU on GPU failure when prefer_gpu

    cpu_result = compute_reho_numpy(data_4d, neighborhood, gm_mask)
    if ties_warning:
        cpu_result.setdefault("warnings", []).append(ties_warning)
    return cpu_result
