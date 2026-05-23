from __future__ import annotations

import time
from typing import Any

import numpy as np


def compute_nuisance_regression_numpy(
    data_4d: np.ndarray,
    X: np.ndarray,
) -> dict[str, Any]:
    """OLS nuisance regression on CPU via NumPy pseudoinverse + matmul."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "cpu-numpy", "residual_4d": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    x, y, z, t = data_4d.shape
    if X.shape[0] != t:
        return {"ok": False, "backend": "cpu-numpy", "residual_4d": None,
                "warnings": [], "errors": [f"X rows mismatch: {X.shape[0]} vs T={t}."],
                "runtime_seconds": 0.0}

    try:
        Y = data_4d.reshape((-1, t)).T.astype(np.float64)
        beta = np.linalg.pinv(X) @ Y
        fitted = X @ beta
        residual = Y - fitted
        residual_4d = residual.T.reshape((x, y, z, t)).astype("float32")

        finite_mask = np.isfinite(residual_4d)
        finite_fraction = float(np.count_nonzero(finite_mask) / residual_4d.size) if residual_4d.size else 0.0
        input_std = float(np.std(data_4d))
        residual_std_val = float(np.std(residual_4d))
        variance_ratio = float(residual_std_val / input_std) if input_std > 0 else None
        rank = int(np.linalg.matrix_rank(X))
    except Exception as exc:
        return {"ok": False, "backend": "cpu-numpy", "residual_4d": None,
                "warnings": warnings, "errors": [str(exc)],
                "runtime_seconds": time.perf_counter() - t_start}

    duration = time.perf_counter() - t_start

    if finite_fraction < 0.95:
        warnings.append(f"Residual finite fraction {finite_fraction:.4f} below 0.95.")
    if variance_ratio is not None and variance_ratio > 1.2:
        warnings.append(f"Residual std larger than input std. Ratio={variance_ratio:.4f}.")

    return {
        "ok": True,
        "backend": "cpu-numpy",
        "residual_4d": residual_4d,
        "confound_rank": rank,
        "finite_fraction": round(finite_fraction, 6),
        "input_std": round(input_std, 6),
        "residual_std": round(residual_std_val, 6),
        "variance_ratio": round(variance_ratio, 6) if variance_ratio is not None else None,
        "warnings": warnings,
        "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def compute_nuisance_regression_cupy(
    data_4d: np.ndarray,
    X: np.ndarray,
) -> dict[str, Any]:
    """OLS nuisance regression on GPU via CuPy pseudoinverse + cuBLAS matmul."""
    import cupy as cp

    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "gpu-cupy", "residual_4d": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    x, y, z, t = data_4d.shape
    if X.shape[0] != t:
        return {"ok": False, "backend": "gpu-cupy", "residual_4d": None,
                "warnings": [], "errors": [f"X rows mismatch: {X.shape[0]} vs T={t}."],
                "runtime_seconds": 0.0}

    try:
        X_gpu = cp.asarray(X, dtype=cp.float64)
        Y_flat = data_4d.reshape((-1, t)).T.astype(np.float64)
        Y_gpu = cp.asarray(Y_flat)
    except Exception as exc:
        return {"ok": False, "backend": "gpu-cupy", "residual_4d": None,
                "warnings": warnings, "errors": [f"GPU transfer failed: {exc}"],
                "runtime_seconds": time.perf_counter() - t_start}

    try:
        X_pinv = cp.linalg.pinv(X_gpu)
        beta = X_pinv @ Y_gpu
        fitted = X_gpu @ beta
        residual_gpu = Y_gpu - fitted
        cp.cuda.Stream.null.synchronize()

        residual_2d = cp.asnumpy(residual_gpu)
        residual_4d = residual_2d.T.reshape((x, y, z, t)).astype("float32")

        finite_mask = np.isfinite(residual_4d)
        finite_fraction = float(np.count_nonzero(finite_mask) / residual_4d.size) if residual_4d.size else 0.0
        input_std = float(np.std(data_4d))
        residual_std_val = float(np.std(residual_4d))
        variance_ratio = float(residual_std_val / input_std) if input_std > 0 else None
        rank = int(np.linalg.matrix_rank(X))
    except Exception as exc:
        return {"ok": False, "backend": "gpu-cupy", "residual_4d": None,
                "warnings": warnings, "errors": [f"GPU computation failed: {exc}"],
                "runtime_seconds": time.perf_counter() - t_start}

    duration = time.perf_counter() - t_start

    if finite_fraction < 0.95:
        warnings.append(f"Residual finite fraction {finite_fraction:.4f} below 0.95.")
    if variance_ratio is not None and variance_ratio > 1.2:
        warnings.append(f"Residual std larger than input std. Ratio={variance_ratio:.4f}.")

    return {
        "ok": True,
        "backend": "gpu-cupy",
        "residual_4d": residual_4d,
        "confound_rank": rank,
        "finite_fraction": round(finite_fraction, 6),
        "input_std": round(input_std, 6),
        "residual_std": round(residual_std_val, 6),
        "variance_ratio": round(variance_ratio, 6) if variance_ratio is not None else None,
        "warnings": warnings,
        "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def compute_nuisance_regression_backend(
    data_4d: np.ndarray,
    X: np.ndarray,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
) -> dict[str, Any]:
    """OLS nuisance regression with automatic GPU/CPU backend selection."""
    gpu_available = False
    if prefer_gpu or require_gpu:
        try:
            import cupy as cp  # noqa: F401
            gpu_available = True
        except ImportError:
            pass

    if require_gpu and not gpu_available:
        return {
            "ok": False, "backend": "none", "residual_4d": None,
            "confound_rank": None, "finite_fraction": 0.0,
            "warnings": [],
            "errors": ["require_gpu=True but CuPy is not available."],
            "runtime_seconds": 0.0,
        }

    if gpu_available:
        result = compute_nuisance_regression_cupy(data_4d, X)
        if result["ok"]:
            return result
        if require_gpu:
            return result

    return compute_nuisance_regression_numpy(data_4d, X)
