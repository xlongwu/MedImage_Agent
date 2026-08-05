from __future__ import annotations

import time
from typing import Any

import numpy as np

from src.backend.app.tools.gpu_utils import configure_cupy_cache_dir


def compute_temporal_filter_numpy(
    data_4d: np.ndarray,
    tr: float,
    low_hz: float,
    high_hz: float,
) -> dict[str, Any]:
    """Band-pass filter on CPU via NumPy FFT/IFFT."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "cpu-numpy", "filtered_4d": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    _, _, _, n_time = data_4d.shape
    if n_time < 4:
        return {"ok": False, "backend": "cpu-numpy", "filtered_4d": None,
                "warnings": [], "errors": ["Need >= 4 timepoints."],
                "runtime_seconds": 0.0}

    try:
        freqs = np.fft.rfftfreq(n_time, d=tr)
        spectrum = np.fft.rfft(data_4d, axis=3)
        mask = (freqs >= low_hz) & (freqs <= high_hz)
        spectrum[..., ~mask] = 0.0
        filtered = np.fft.irfft(spectrum, n=n_time, axis=3).astype("float32")

        input_std = float(np.std(data_4d))
        filtered_std = float(np.std(filtered))
        finite_fraction = float(np.count_nonzero(np.isfinite(filtered)) / filtered.size) if filtered.size else 0.0
        retained_bins = int(np.count_nonzero(mask))
    except Exception as exc:
        return {"ok": False, "backend": "cpu-numpy", "filtered_4d": None,
                "warnings": warnings, "errors": [str(exc)],
                "runtime_seconds": time.perf_counter() - t_start}

    duration = time.perf_counter() - t_start

    return {
        "ok": True,
        "backend": "cpu-numpy",
        "filtered_4d": filtered,
        "retained_frequency_bin_count": retained_bins,
        "low_hz": low_hz,
        "high_hz": high_hz,
        "tr": tr,
        "input_std": round(input_std, 6),
        "filtered_std": round(filtered_std, 6),
        "finite_fraction": round(finite_fraction, 6),
        "warnings": warnings,
        "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def compute_temporal_filter_cupy(
    data_4d: np.ndarray,
    tr: float,
    low_hz: float,
    high_hz: float,
) -> dict[str, Any]:
    """Band-pass filter on GPU via CuPy cuFFT."""
    configure_cupy_cache_dir()
    import cupy as cp

    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    if data_4d.ndim != 4:
        return {"ok": False, "backend": "gpu-cupy", "filtered_4d": None,
                "warnings": [], "errors": ["Data must be 4D."],
                "runtime_seconds": 0.0}

    _, _, _, n_time = data_4d.shape
    if n_time < 4:
        return {"ok": False, "backend": "gpu-cupy", "filtered_4d": None,
                "warnings": [], "errors": ["Need >= 4 timepoints."],
                "runtime_seconds": 0.0}

    try:
        data_gpu = cp.asarray(data_4d, dtype=cp.float32)
        freqs = cp.fft.rfftfreq(n_time, d=tr)
        mask = cp.asarray((freqs >= low_hz) & (freqs <= high_hz))
        spectrum = cp.fft.rfft(data_gpu, axis=3)
        spectrum[..., ~mask] = 0.0
        filtered_gpu = cp.fft.irfft(spectrum, n=n_time, axis=3)
        cp.cuda.Stream.null.synchronize()
        filtered = cp.asnumpy(filtered_gpu).astype("float32")

        input_std = float(np.std(data_4d))
        filtered_std = float(np.std(filtered))
        finite_fraction = float(np.count_nonzero(np.isfinite(filtered)) / filtered.size) if filtered.size else 0.0
        retained_bins = int(cp.count_nonzero(mask).item())
    except Exception as exc:
        return {"ok": False, "backend": "gpu-cupy", "filtered_4d": None,
                "warnings": warnings, "errors": [f"GPU computation failed: {exc}"],
                "runtime_seconds": time.perf_counter() - t_start}

    duration = time.perf_counter() - t_start

    return {
        "ok": True,
        "backend": "gpu-cupy",
        "filtered_4d": filtered,
        "retained_frequency_bin_count": retained_bins,
        "low_hz": low_hz,
        "high_hz": high_hz,
        "tr": tr,
        "input_std": round(input_std, 6),
        "filtered_std": round(filtered_std, 6),
        "finite_fraction": round(finite_fraction, 6),
        "warnings": warnings,
        "errors": errors,
        "runtime_seconds": round(duration, 3),
    }


def compute_temporal_filter_backend(
    data_4d: np.ndarray,
    tr: float,
    low_hz: float,
    high_hz: float,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
) -> dict[str, Any]:
    """Band-pass filtering with automatic GPU/CPU backend selection."""
    gpu_available = False
    if prefer_gpu or require_gpu:
        try:
            import cupy as cp  # noqa: F401
            gpu_available = True
        except ImportError:
            pass

    if require_gpu and not gpu_available:
        return {
            "ok": False, "backend": "none", "filtered_4d": None,
            "retained_frequency_bin_count": 0,
            "warnings": [],
            "errors": ["require_gpu=True but CuPy is not available."],
            "runtime_seconds": 0.0,
        }

    if gpu_available:
        result = compute_temporal_filter_cupy(data_4d, tr, low_hz, high_hz)
        if result["ok"]:
            return result
        if require_gpu:
            return result

    return compute_temporal_filter_numpy(data_4d, tr, low_hz, high_hz)
