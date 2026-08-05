from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.backend.app.safety.gpu_safety import (
    check_cuda_availability,
    validate_gpu_concurrency,
    validate_gpu_device,
    validate_gpu_memory_budget,
    validate_gpu_timeout,
)


def configure_cupy_cache_dir() -> Path:
    """Use a writable application cache without overriding an explicit choice.

    CuPy JIT compilation otherwise defaults to a user-profile directory.  The
    desktop sidecar can run under a restricted account, so cache placement must
    not make an apparently available GPU fail at its first numerical kernel.
    """
    configured = os.environ.get("CUPY_CACHE_DIR")
    target = Path(configured) if configured else Path(tempfile.gettempdir()) / "medimage-agent" / "cupy-cache"
    target.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CUPY_CACHE_DIR", str(target))
    return target


def is_scoped_derivative_path(path: str | Path, scope_dir: str | Path) -> bool:
    """Return true only for paths contained by the derivative scope."""

    try:
        resolved_path = Path(path).resolve()
        resolved_scope = Path(scope_dir).resolve()
        resolved_path.relative_to(resolved_scope)
    except ValueError:
        return False

    path_str = str(resolved_path).replace("\\", "/")
    scope_str = str(resolved_scope).replace("\\", "/")
    if ".." in path_str or ".." in scope_str:
        return False
    if any(seg in ("rawdata", "data") for seg in resolved_path.parts):
        return False
    return True


def apply_gpu_guard(
    result: dict[str, Any],
    *,
    device: str,
    functional_shape: Sequence[int] | None,
    dtype_bytes: int,
    batch_size: int,
    timeout_seconds: int,
    require_gpu: bool,
    torch_cuda_available: bool | None,
    device_count: int | None,
    active_jobs: int,
    max_concurrent_jobs: int,
    max_elements: int,
    max_bytes: int,
    max_timeout_seconds: int = 120,
) -> bool:
    """Apply the common pure-Python GPU scaffold guards to a result dict."""

    dev = validate_gpu_device(device)
    result["gpu_guard"] = dev.to_dict()
    if not dev.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in dev.errors)
        return False

    cuda = check_cuda_availability(
        torch_cuda_available=torch_cuda_available,
        device_count=device_count,
        require_gpu=require_gpu,
    )
    result["warnings"].extend(w.message for w in cuda.warnings)
    if not cuda.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in cuda.errors)
        return False

    if functional_shape:
        mem = validate_gpu_memory_budget(
            shape=functional_shape,
            dtype_bytes=dtype_bytes,
            batch_size=batch_size,
            max_elements=max_elements,
            max_bytes=max_bytes,
        )
        if not mem.ok:
            result["ok"] = False
            result["errors"].extend(e.message for e in mem.errors)
            return False
        result["estimated_bytes"] = mem.estimated_bytes

    tm = validate_gpu_timeout(timeout_seconds, max_timeout_seconds=max_timeout_seconds)
    if not tm.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in tm.errors)
        return False

    conc = validate_gpu_concurrency(active_jobs=active_jobs, max_concurrent_jobs=max_concurrent_jobs)
    if not conc.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in conc.errors)
        return False

    return True


def write_gpu_provenance(output_dir: str | Path, provenance: dict[str, Any]) -> Path:
    """Write scaffold provenance using the existing JSON formatting."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    provenance_path = output_path / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return provenance_path


def detect_gpu() -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        configure_cupy_cache_dir()
        import cupy as cp
    except ImportError as exc:
        return {
            "ok": True,
            "cupy_available": False,
            "gpu_available": False,
            "device_count": 0,
            "device_id": None,
            "device_name": None,
            "free_vram_bytes": None,
            "total_vram_bytes": None,
            "cuda_runtime_version": None,
            "driver_version": None,
            "gpu_utilization_percent": None,
            "capability_error_code": "CUPY_IMPORT_FAILED",
            "warnings": [f"CuPy import failed; GPU backend unavailable: {exc}"],
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
                "device_id": None,
                "device_name": None,
                "free_vram_bytes": None,
                "total_vram_bytes": None,
                "cuda_runtime_version": int(cp.cuda.runtime.runtimeGetVersion()),
                "driver_version": int(cp.cuda.runtime.driverGetVersion()),
                "gpu_utilization_percent": None,
                "capability_error_code": "GPU_UNAVAILABLE",
                "warnings": ["CuPy is installed but no CUDA device was detected."],
                "errors": [],
            }

        device = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(0)
        device_name = props.get("name", b"unknown")
        if isinstance(device_name, bytes):
            device_name = device_name.decode("utf-8", errors="replace")

        with device:
            free_bytes, total_bytes = cp.cuda.runtime.memGetInfo()
            # Exercise a JIT kernel, not merely device enumeration or cuBLAS,
            # so DLL/compiler/cache failures become a truthful unavailable
            # result before a reviewed run starts.
            _ = cp.sin(cp.asarray([1.0, 2.0, 3.0])).sum().item()

        return {
            "ok": True,
            "cupy_available": True,
            "gpu_available": True,
            "device_count": int(device_count),
            "device_id": "cuda:0",
            "device_name": str(device_name),
            "free_vram_bytes": int(free_bytes),
            "total_vram_bytes": int(total_bytes),
            "cuda_runtime_version": int(cp.cuda.runtime.runtimeGetVersion()),
            "driver_version": int(cp.cuda.runtime.driverGetVersion()),
            # CuPy does not provide a portable utilization API.  NVML remains
            # optional, so absence is explicit instead of guessed.
            "gpu_utilization_percent": None,
            "capability_error_code": None,
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        return {
            "ok": True,
            "cupy_available": True,
            "gpu_available": False,
            "device_count": 0,
            "device_id": None,
            "device_name": None,
            "free_vram_bytes": None,
            "total_vram_bytes": None,
            "cuda_runtime_version": None,
            "driver_version": None,
            "gpu_utilization_percent": None,
            "capability_error_code": "GPU_CAPABILITY_PROBE_FAILED",
            "warnings": [f"CuPy is installed but GPU check failed: {exc}"],
            "errors": [],
        }
