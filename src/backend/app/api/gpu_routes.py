"""GPU route handlers."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.backend.app.api.execution_contract import reject_execution_contract
from src.backend.app.api.models import GpuBenchmarkRequest
from src.backend.app.tools.gpu_utils import detect_gpu

router = APIRouter()


@router.get("/api/gpu/detect")
def api_gpu_detect() -> dict[str, Any]:
    return detect_gpu()

@router.post("/api/gpu/benchmark")
def api_gpu_benchmark(payload: GpuBenchmarkRequest) -> dict[str, Any]:
    reject_execution_contract("gpu.benchmark")

@router.get("/api/gpu/capability")
async def gpu_capability():
    """Detect GPU capability (CuPy, PyTorch CUDA, device info)."""
    from src.backend.app.tools.gpu_capability import detect_gpu_capability

    return detect_gpu_capability()

@router.post("/api/gpu/synthetic-benchmark")
async def gpu_synthetic_benchmark(request: dict[str, Any]):
    """Run CPU vs GPU benchmark for ALFF computation."""
    reject_execution_contract("gpu.synthetic_benchmark")
