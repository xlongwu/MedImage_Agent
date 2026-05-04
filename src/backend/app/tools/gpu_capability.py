"""GPU capability detection — check CUDA, CuPy, PyTorch availability."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def detect_gpu_capability(report_dir: str = "./work/gpu") -> dict[str, Any]:
    """Comprehensive GPU capability check. Always succeeds (GPU is optional)."""
    report_out = Path(report_dir)
    report_out.mkdir(parents=True, exist_ok=True)

    cupy_available = False
    cupy_version = None
    torch_available = False
    torch_version = None
    torch_cuda = False
    gpu_name = None
    gpu_memory_mb = None
    cuda_version = None
    errors: list[str] = []

    # CuPy
    try:
        import cupy as cp
        cupy_version = cp.__version__
        if cp.cuda.is_available():
            cupy_available = True
            gpu_name = cp.cuda.Device().name
            mem = cp.cuda.Device().mem_info
            gpu_memory_mb = mem[0] // (1024 * 1024)
    except ImportError:
        errors.append("CuPy not installed. pip install cupy-cuda12x")
    except Exception as e:
        errors.append(f"CuPy error: {e}")

    # PyTorch
    try:
        import torch
        torch_version = torch.__version__
        torch_available = True
        if torch.cuda.is_available():
            torch_cuda = True
            if not gpu_name:
                gpu_name = torch.cuda.get_device_name(0)
            if not gpu_memory_mb:
                gpu_memory_mb = torch.cuda.get_device_properties(0).total_mem // (1024 * 1024)
            cuda_version = torch.version.cuda
    except ImportError:
        errors.append("PyTorch not installed")
    except Exception as e:
        errors.append(f"PyTorch error: {e}")

    gpu_available = cupy_available or torch_cuda

    capability = {
        "ok": True,
        "gpu_available": gpu_available,
        "cupy": {
            "available": cupy_available,
            "version": cupy_version,
        },
        "torch": {
            "available": torch_available,
            "version": torch_version,
            "cuda_available": torch_cuda,
        },
        "device": {
            "name": gpu_name,
            "memory_mb": gpu_memory_mb,
            "cuda_version": cuda_version,
        } if gpu_available else None,
        "message": "GPU available for acceleration" if gpu_available else "GPU not available. CPU backend will be used.",
        "errors": errors,
    }

    (report_out / "gpu_capability.json").write_text(
        json.dumps(capability, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return capability
