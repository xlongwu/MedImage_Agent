from __future__ import annotations

from typing import Any


def detect_gpu() -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        import cupy as cp
    except ImportError:
        return {
            "ok": True,
            "cupy_available": False,
            "gpu_available": False,
            "device_count": 0,
            "device_name": None,
            "warnings": ["CuPy is not installed. GPU backend unavailable."],
            "errors": [],
        }

    try:
        device_count = cp.cuda.runtime.getDeviceCount()
        if device_count <= 0:
            return {
                "ok": True,
                "cupy_available": True,
                "gpu_available": False,
                "device_count": 0,
                "device_name": None,
                "warnings": ["CuPy is installed but no CUDA device was detected."],
                "errors": [],
            }

        device = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(0)
        device_name = props.get("name", b"unknown")
        if isinstance(device_name, bytes):
            device_name = device_name.decode("utf-8", errors="replace")

        with device:
            _ = cp.asarray([1.0, 2.0, 3.0]).sum().item()

        return {
            "ok": True,
            "cupy_available": True,
            "gpu_available": True,
            "device_count": int(device_count),
            "device_name": str(device_name),
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        return {
            "ok": True,
            "cupy_available": True,
            "gpu_available": False,
            "device_count": 0,
            "device_name": None,
            "warnings": [f"CuPy is installed but GPU check failed: {exc}"],
            "errors": [],
        }
