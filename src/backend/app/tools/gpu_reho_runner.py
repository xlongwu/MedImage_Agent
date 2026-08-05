"""GPU ReHo subject runner scaffold (M8-GPU-T008b).

Pure Python preflight — no torch import, no CUDA, no GPU allocation.
Uses gpu_safety.py guards for device, memory, timeout, concurrency.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from src.backend.app.tools.gpu_utils import (
    apply_gpu_guard,
    is_scoped_derivative_path,
    write_gpu_provenance,
)

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
    if not is_scoped_derivative_path(input_path, derivatives):
        result["ok"] = False
        result["errors"].append(f"Input functional not under derivatives_dir: {input_functional}")
        return result

    # ── Mask ──
    if mask_path:
        mp = Path(mask_path)
        if not is_scoped_derivative_path(mp, derivatives):
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
    if not apply_gpu_guard(
        result,
        device=device,
        functional_shape=functional_shape,
        dtype_bytes=dtype_bytes,
        batch_size=batch_size,
        timeout_seconds=timeout_seconds,
        require_gpu=require_gpu,
        torch_cuda_available=torch_cuda_available,
        device_count=device_count,
        active_jobs=active_jobs,
        max_concurrent_jobs=max_concurrent_jobs,
        max_elements=25_000_000,
        max_bytes=512 * 1024 * 1024,
    ):
        return result

    # ── Output scope ──
    output_dir = derivatives / "gpu" / "gpu_reho_subject" / run_id / subject_id
    provenance = {
        "subject_id": subject_id, "run_id": run_id,
        "neighborhood": neighborhood,
        "device": device, "dry_run": dry_run,
    }
    if mask_path:
        provenance["mask"] = str(mask_path)
    provenance_path = write_gpu_provenance(output_dir, provenance)

    outputs = {
        "output_dir": str(output_dir),
        "provenance": str(provenance_path),
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
