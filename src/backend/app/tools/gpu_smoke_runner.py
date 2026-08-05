"""Synthetic GPU smoke runner (M8-GPU-T006b).

Pure Python — no torch import, no CUDA, no GPU allocation.
Uses gpu_safety.py guards for device, memory, timeout, concurrency validation.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from src.backend.app.safety.gpu_safety import (
    validate_gpu_concurrency,
    validate_gpu_runtime_request,
)


def run_gpu_synthetic_smoke(
    *,
    device: str = "auto",
    shape: Sequence[int] = (64, 64),
    dtype_bytes: int = 4,
    batch_size: int = 1,
    timeout_seconds: int = 10,
    require_gpu: bool = False,
    torch_cuda_available: bool | None = None,
    device_count: int | None = None,
    active_jobs: int = 0,
    max_concurrent_jobs: int = 1,
    reports_dir: str | Path | None = None,
    work_dir: str | Path | None = None,
    run_id: str | None = None,
    approved: bool = True,
) -> dict:

    result: dict = {
        "ok": True,
        "node_id": "gpu_synthetic_smoke",
        "backend": "gpu",
        "synthetic_only": True,
        "device": device,
        "shape": list(shape),
        "estimated_bytes": 0,
        "timeout_seconds": timeout_seconds,
        "cuda_called": False,
        "gpu_called": False,
        "tensor_allocated": False,
        "runs_training": False,
        "runs_model_inference": False,
        "writes_rawdata": False,
        "writes_derivatives": False,
        "errors": [],
        "warnings": [],
    }

    if not approved:
        result["ok"] = False
        result["errors"].append("GPU synthetic smoke requires approved=true.")
        return result

    # ── Concurrency guard ──
    conc = validate_gpu_concurrency(active_jobs=active_jobs, max_concurrent_jobs=max_concurrent_jobs)
    if not conc.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in conc.errors)
        result["gpu_guard"] = conc.to_dict()
        result["stage"] = "concurrency_preflight"
        return result

    # ── Unified GPU runtime guard ──
    guard = validate_gpu_runtime_request(
        device=device,
        shape=shape,
        dtype_bytes=dtype_bytes,
        batch_size=batch_size,
        timeout_seconds=timeout_seconds,
        require_gpu=require_gpu,
        torch_cuda_available=torch_cuda_available,
        device_count=device_count,
    )
    result["gpu_guard"] = guard.to_dict()
    result["estimated_bytes"] = guard.estimated_bytes or 0

    if not guard.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in guard.errors)
        result["stage"] = "gpu_guard_preflight"
        return result

    result["warnings"].extend(w.message for w in guard.warnings)

    # ── Output scope ──
    if reports_dir:
        reports = Path(reports_dir)
        rstr = str(reports.resolve()).replace("\\", "/")
        if ".." in rstr:
            result["ok"] = False
            result["errors"].append("Path traversal rejected for reports_dir.")
            return result
        out_path = reports / "gpu" / "smoke" / (run_id or "latest") / "gpu_synthetic_smoke_result.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["report_json"] = str(out_path)

    return result
