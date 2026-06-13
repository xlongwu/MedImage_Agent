"""GPU route handlers."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.backend.app.api.models import GpuBenchmarkRequest
from src.backend.app.tools.gpu_alff_runner import run_alff_subject
from src.backend.app.tools.gpu_utils import detect_gpu

router = APIRouter()


@router.get("/api/gpu/detect")
def api_gpu_detect() -> dict[str, Any]:
    return detect_gpu()

@router.post("/api/gpu/benchmark")
def api_gpu_benchmark(payload: GpuBenchmarkRequest) -> dict[str, Any]:
    result = run_alff_subject(
        subject_id=payload.subject_id,
        input_nii=payload.input_nii,
        derivatives_dir=payload.derivatives_dir,
        tr=payload.tr,
        freq_band=payload.freq_band,
        prefer_gpu=payload.prefer_gpu,
        require_gpu=payload.require_gpu,
        benchmark_compare_cpu_gpu=payload.benchmark_compare_cpu_gpu,
    )
    return result

@router.get("/api/gpu/capability")
async def gpu_capability():
    """Detect GPU capability (CuPy, PyTorch CUDA, device info)."""
    from src.backend.app.tools.gpu_capability import detect_gpu_capability

    return detect_gpu_capability()

@router.post("/api/gpu/synthetic-benchmark")
async def gpu_synthetic_benchmark(request: dict[str, Any]):
    """Run CPU vs GPU benchmark for ALFF computation."""
    from src.backend.app.tools.alff_compute import compute_alff_backend, compute_alff_numpy
    import numpy as np
    import time

    shape = tuple(request.get("shape", [32, 32, 32, 128]))
    filter_type = request.get("filter_type", "bandpass")
    low_hz = float(request.get("low_hz", 0.01))
    high_hz = float(request.get("high_hz", 0.08))
    tr = float(request.get("tr", 2.0))

    data = np.random.default_rng(42).normal(size=shape).astype(np.float32)

    t0 = time.time()
    _cpu = compute_alff_numpy(data, low_hz=low_hz, high_hz=high_hz, tr=tr)
    cpu_time = round(time.time() - t0, 3)

    gpu_time = None
    gpu_error = None
    try:
        t0 = time.time()
        _gpu = compute_alff_backend(data, low_hz=low_hz, high_hz=high_hz, tr=tr, prefer_gpu=True)
        gpu_time = round(time.time() - t0, 3)
    except Exception as exc:
        gpu_error = str(exc)

    return {
        "ok": True,
        "shape": list(shape),
        "cpu_time_s": cpu_time,
        "gpu_time_s": gpu_time,
        "gpu_error": gpu_error,
        "speedup": round(cpu_time / gpu_time, 2) if gpu_time else None,
    }
