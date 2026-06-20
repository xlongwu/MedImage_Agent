from __future__ import annotations

import time
from typing import Any

import numpy as np


def _safe_falff(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    out = np.zeros_like(numerator, dtype="float32")
    mask = denominator > 0
    out[mask] = numerator[mask] / denominator[mask]
    return out.astype("float32")


def compute_alff_numpy(
    data: np.ndarray,
    tr: float,
    freq_band: tuple[float, float],
    *,
    standardize: bool = False,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Compute ALFF/fALFF with optional z-standardization.

    Args:
        data: 4D BOLD (x, y, z, t)
        tr: Repetition time in seconds
        freq_band: (low, high) Hz for target band
        standardize: If True, apply z-score normalization to ALFF/fALFF maps
    """
    warnings: list[str] = []

    if data.ndim != 4:
        raise ValueError(f"Expected 4D BOLD data, got shape={data.shape}")

    n_timepoints = data.shape[-1]
    if n_timepoints < 8:
        warnings.append(f"Very few timepoints for ALFF: {n_timepoints}")

    data = data.astype("float32")
    data = data - np.mean(data, axis=-1, keepdims=True)

    freqs = np.fft.rfftfreq(n_timepoints, d=tr)
    spectrum = np.fft.rfft(data, axis=-1)
    amplitude = np.abs(spectrum).astype("float32")

    low, high = freq_band
    band_mask = (freqs >= low) & (freqs <= high)

    if not np.any(band_mask):
        warnings.append(
            f"No FFT bins found in frequency band {freq_band}; ALFF will be zeros."
        )
        alff = np.zeros(data.shape[:3], dtype="float32")
        falff = np.zeros(data.shape[:3], dtype="float32")
        return alff, falff, warnings

    band_amp = amplitude[..., band_mask]
    alff = np.mean(band_amp, axis=-1).astype("float32")

    total_amp = np.sum(amplitude[..., 1:], axis=-1).astype("float32")
    band_sum = np.sum(band_amp, axis=-1).astype("float32")
    falff = _safe_falff(band_sum, total_amp)

    if standardize:
        alff_mean = alff.mean(); alff_std = alff.std() + 1e-10
        alff = (alff - alff_mean) / alff_std
        falff_mean = falff.mean(); falff_std = falff.std() + 1e-10
        falff = (falff - falff_mean) / falff_std

    return alff, falff, warnings


def compute_alff_cupy(
    data: np.ndarray,
    tr: float,
    freq_band: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    warnings: list[str] = []

    try:
        import cupy as cp
    except ImportError as exc:
        raise RuntimeError("CuPy is not installed.") from exc

    if data.ndim != 4:
        raise ValueError(f"Expected 4D BOLD data, got shape={data.shape}")

    n_timepoints = data.shape[-1]
    if n_timepoints < 8:
        warnings.append(f"Very few timepoints for ALFF: {n_timepoints}")

    x = cp.asarray(data.astype("float32"))
    x = x - cp.mean(x, axis=-1, keepdims=True)

    freqs = cp.asarray(np.fft.rfftfreq(n_timepoints, d=tr))
    spectrum = cp.fft.rfft(x, axis=-1)
    amplitude = cp.abs(spectrum).astype(cp.float32)

    low, high = freq_band
    band_mask = (freqs >= low) & (freqs <= high)

    if not bool(cp.any(band_mask).get()):
        warnings.append(
            f"No FFT bins found in frequency band {freq_band}; ALFF will be zeros."
        )
        alff = cp.zeros(x.shape[:3], dtype=cp.float32)
        falff = cp.zeros(x.shape[:3], dtype=cp.float32)
        return cp.asnumpy(alff), cp.asnumpy(falff), warnings

    band_amp = amplitude[..., band_mask]
    alff = cp.mean(band_amp, axis=-1).astype(cp.float32)

    total_amp = cp.sum(amplitude[..., 1:], axis=-1).astype(cp.float32)
    band_sum = cp.sum(band_amp, axis=-1).astype(cp.float32)

    falff = cp.zeros_like(band_sum, dtype=cp.float32)
    mask = total_amp > 0
    falff[mask] = band_sum[mask] / total_amp[mask]

    cp.cuda.Stream.null.synchronize()

    return cp.asnumpy(alff), cp.asnumpy(falff), warnings


def compute_alff_torch(
    data: np.ndarray,
    tr: float,
    freq_band: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """GPU-accelerated ALFF/fALFF using PyTorch CUDA."""
    warnings: list[str] = []

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is not installed.") from exc

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available for PyTorch.")

    if data.ndim != 4:
        raise ValueError(f"Expected 4D BOLD data, got shape={data.shape}")

    n_timepoints = data.shape[-1]
    if n_timepoints < 8:
        warnings.append(f"Very few timepoints for ALFF: {n_timepoints}")

    device = torch.device("cuda")
    x = torch.from_numpy(data.astype("float32")).to(device)
    x = x - torch.mean(x, dim=-1, keepdim=True)

    freqs = np.fft.rfftfreq(n_timepoints, d=tr)
    spectrum = torch.fft.rfft(x, dim=-1)
    amplitude = torch.abs(spectrum)

    low, high = freq_band
    band_mask_np = (freqs >= low) & (freqs <= high)
    band_mask = torch.from_numpy(band_mask_np).to(device)

    if not torch.any(band_mask).item():
        warnings.append(f"No FFT bins found in frequency band {freq_band}; ALFF will be zeros.")
        alff = torch.zeros(x.shape[:3], dtype=torch.float32, device=device)
        falff = torch.zeros(x.shape[:3], dtype=torch.float32, device=device)
        return alff.cpu().numpy(), falff.cpu().numpy(), warnings

    band_amp = amplitude[..., band_mask]
    alff = torch.mean(band_amp, dim=-1)

    total_amp = torch.sum(amplitude[..., 1:], dim=-1)
    band_sum = torch.sum(band_amp, dim=-1)
    falff = torch.zeros_like(band_sum)
    mask = total_amp > 0
    falff[mask] = band_sum[mask] / total_amp[mask]

    torch.cuda.synchronize()
    return alff.cpu().numpy(), falff.cpu().numpy(), warnings


def compute_alff_backend(
    data: np.ndarray,
    tr: float,
    freq_band: tuple[float, float],
    prefer_gpu: bool = True,
    require_gpu: bool = False,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if prefer_gpu:
        # Try CuPy first, then PyTorch
        for gpu_backend in [("gpu-cupy", compute_alff_cupy), ("gpu-torch", compute_alff_torch)]:
            try:
                start = time.perf_counter()
                alff, falff, backend_warnings = gpu_backend[1](data, tr, freq_band)
                runtime_seconds = time.perf_counter() - start
                warnings.extend(backend_warnings)
                return {
                    "ok": True,
                    "backend": gpu_backend[0],
                    "alff": alff.astype("float32"),
                    "falff": falff.astype("float32"),
                    "runtime_seconds": runtime_seconds,
                    "warnings": warnings,
                    "errors": errors,
                }
            except Exception as exc:
                continue

        if require_gpu:
            return {
                "ok": False,
                "backend": "gpu",
                "alff": None,
                "falff": None,
                "runtime_seconds": None,
                "warnings": warnings,
                "errors": [f"GPU ALFF failed and require_gpu=true: no GPU backend available"],
            }
        warnings.append("GPU backend unavailable, falling back to CPU.")

    start = time.perf_counter()
    alff, falff, backend_warnings = compute_alff_numpy(data, tr, freq_band)
    runtime_seconds = time.perf_counter() - start
    warnings.extend(backend_warnings)

    return {
        "ok": True,
        "backend": "cpu-numpy",
        "alff": alff.astype("float32"),
        "falff": falff.astype("float32"),
        "runtime_seconds": runtime_seconds,
        "warnings": warnings,
        "errors": errors,
    }
