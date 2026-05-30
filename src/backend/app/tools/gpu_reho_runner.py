"""GPU ReHo subject runner scaffold (M8-GPU-T008b).

Pure Python preflight — no torch import, no CUDA, no GPU allocation.
Uses gpu_safety.py guards for device, memory, timeout, concurrency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from src.backend.app.safety.gpu_safety import (
    validate_gpu_device,
    check_cuda_availability,
    validate_gpu_memory_budget,
    validate_gpu_timeout,
    validate_gpu_concurrency,
)


def _is_scoped_path(path: Path, scope_dir: Path) -> bool:
    try:
        rp = path.resolve()
        rs = scope_dir.resolve()
        rp.relative_to(rs)
    except ValueError:
        return False
    ps = str(rp).replace("\\", "/")
    if ".." in ps:
        return False
    if any(seg in ("rawdata", "data") for seg in rp.parts):
        return False
    return True


_ALLOWED_NEIGHBORHOODS = frozenset({7, 19, 27})


def run_gpu_reho_subject(
    *,
    subject_id: str,
    input_functional: str | Path,
    derivatives_dir: str | Path,
    run_id: str,
    neighborhood: int = 27,
    mask_path: str | Path | None = None,
    device: str = "auto",
    functional_shape: Sequence[int] | None = None,
    dtype_bytes: int = 4,
    batch_size: int = 1,
    timeout_seconds: int = 60,
    require_gpu: bool = False,
    torch_cuda_available: bool | None = None,
    device_count: int | None = None,
    active_jobs: int = 0,
    max_concurrent_jobs: int = 1,
    approved: bool = True,
    dry_run: bool = False,
) -> dict:

    result: dict = {
        "ok": True, "node_id": "gpu_reho_subject", "backend": "gpu",
        "subject_id": subject_id, "run_id": run_id,
        "cuda_called": False, "gpu_called": False, "tensor_allocated": False,
        "runs_training": False, "runs_model_inference": False,
        "writes_rawdata": False, "errors": [], "warnings": [],
    }

    if not approved:
        result["ok"] = False
        result["errors"].append("GPU ReHo subject requires approved=true.")
        return result
    if not subject_id or not isinstance(subject_id, str):
        result["ok"] = False
        result["errors"].append(f"Invalid subject_id: {subject_id!r}.")
        return result

    # ── Input ──
    derivatives = Path(derivatives_dir)
    input_path = Path(input_functional)
    if not _is_scoped_path(input_path, derivatives):
        result["ok"] = False
        result["errors"].append(f"Input functional not under derivatives_dir: {input_functional}")
        return result

    # ── Mask ──
    if mask_path:
        mp = Path(mask_path)
        if not _is_scoped_path(mp, derivatives):
            result["ok"] = False
            result["errors"].append(f"Mask not under derivatives_dir: {mask_path}")
            return result

    # ── Neighborhood ──
    if neighborhood not in _ALLOWED_NEIGHBORHOODS:
        result["ok"] = False
        result["errors"].append(
            f"Invalid neighborhood: {neighborhood}. Allowed: {sorted(_ALLOWED_NEIGHBORHOODS)}."
        )
        return result

    # ── GPU guard ──
    dev = validate_gpu_device(device)
    result["gpu_guard"] = dev.to_dict()
    if not dev.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in dev.errors)
        return result

    cuda = check_cuda_availability(
        torch_cuda_available=torch_cuda_available,
        device_count=device_count,
        require_gpu=require_gpu,
    )
    result["warnings"].extend(w.message for w in cuda.warnings)
    if not cuda.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in cuda.errors)
        return result

    if functional_shape:
        mem = validate_gpu_memory_budget(
            shape=functional_shape,
            dtype_bytes=dtype_bytes,
            batch_size=batch_size,
            max_elements=25_000_000,
            max_bytes=512 * 1024 * 1024,
        )
        if not mem.ok:
            result["ok"] = False
            result["errors"].extend(e.message for e in mem.errors)
            return result
        result["estimated_bytes"] = mem.estimated_bytes

    tm = validate_gpu_timeout(timeout_seconds, max_timeout_seconds=120)
    if not tm.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in tm.errors)
        return result

    conc = validate_gpu_concurrency(active_jobs=active_jobs, max_concurrent_jobs=max_concurrent_jobs)
    if not conc.ok:
        result["ok"] = False
        result["errors"].extend(e.message for e in conc.errors)
        return result

    # ── Output scope ──
    output_dir = derivatives / "gpu" / "gpu_reho_subject" / run_id / subject_id
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "subject_id": subject_id, "run_id": run_id,
        "neighborhood": neighborhood,
        "device": device, "dry_run": dry_run,
    }
    if mask_path:
        provenance["mask"] = str(mask_path)
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    outputs = {
        "output_dir": str(output_dir),
        "provenance": str(output_dir / "provenance.json"),
    }
    if dry_run:
        outputs["reho_map"] = str(output_dir / "reho_map.nii.gz")
    else:
        result["stage"] = "preflight_completed"
        result["warnings"].append("ReHo computation not executed (runner is scaffold-only).")

    result["outputs"] = outputs
    return result


# Backward-compatibility alias for existing nodes/gpu_reho_node.py
run_reho_subject = run_gpu_reho_subject
