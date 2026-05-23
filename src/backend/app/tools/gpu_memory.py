from __future__ import annotations

from typing import Any


def get_gpu_memory_info() -> dict[str, Any]:
    """Return free and total GPU memory in MB. Returns zeros if GPU unavailable."""
    result: dict[str, Any] = {
        "ok": True,
        "free_mb": 0,
        "total_mb": 0,
        "device_name": None,
        "warnings": [],
        "errors": [],
    }

    try:
        import cupy as cp
    except ImportError:
        result["warnings"].append("CuPy not installed; GPU memory info unavailable.")
        _try_torch_memory_info(result)
        return result

    try:
        dev = cp.cuda.Device(0)
        free_bytes, total_bytes = dev.mem_info
        result["free_mb"] = round(free_bytes / (1024 * 1024), 1)
        result["total_mb"] = round(total_bytes / (1024 * 1024), 1)
        props = cp.cuda.runtime.getDeviceProperties(0)
        result["device_name"] = props.get("name", "unknown").decode() if isinstance(props.get("name"), bytes) else str(props.get("name", "unknown"))
    except Exception as exc:
        result["errors"].append(f"CuPy GPU memory query failed: {exc}")
        _try_torch_memory_info(result)

    return result


def _try_torch_memory_info(result: dict[str, Any]) -> None:
    try:
        import torch
    except ImportError:
        return
    try:
        if torch.cuda.is_available():
            free_bytes = torch.cuda.mem_get_info()[0] if hasattr(torch.cuda, "mem_get_info") else 0
            total_bytes = torch.cuda.mem_get_info()[1] if hasattr(torch.cuda, "mem_get_info") else torch.cuda.get_device_properties(0).total_memory
            result["free_mb"] = round(free_bytes / (1024 * 1024), 1)
            result["total_mb"] = round(total_bytes / (1024 * 1024), 1)
            result["device_name"] = torch.cuda.get_device_name(0)
    except Exception:
        pass


def estimate_memory_requirement(shape: tuple[int, ...], dtype: str = "float32") -> float:
    """Estimate GPU memory needed for a 4D array including intermediate buffers.

    Uses shape_bytes * 5 to account for: input, output, FFT workspace,
    temporary arrays, and library overhead.
    """
    import numpy as np

    dtype_obj = np.dtype(dtype)
    element_bytes = dtype_obj.itemsize
    total_elements = 1
    for dim in shape:
        total_elements *= dim
    raw_bytes = total_elements * element_bytes
    return raw_bytes * 5 / (1024 * 1024)  # MB


def can_fit_in_gpu(shape: tuple[int, ...], dtype: str = "float32", safety_margin_mb: float = 512) -> dict[str, Any]:
    """Check if a data array can fit in available GPU memory."""
    estimated_mb = estimate_memory_requirement(shape, dtype)
    mem_info = get_gpu_memory_info()

    free_mb = mem_info.get("free_mb", 0)
    available = free_mb > (estimated_mb + safety_margin_mb)

    return {
        "ok": True,
        "estimated_mb": round(estimated_mb, 1),
        "free_mb": free_mb,
        "total_mb": mem_info.get("total_mb", 0),
        "device_name": mem_info.get("device_name"),
        "can_fit": available,
        "safety_margin_mb": safety_margin_mb,
        "recommendation": (
            "Sufficient GPU memory available."
            if available
            else f"Insufficient GPU memory: need ~{round(estimated_mb)}MB, have {free_mb}MB free."
        ),
    }
