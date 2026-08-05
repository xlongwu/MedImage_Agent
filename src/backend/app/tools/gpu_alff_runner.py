"""GPU ALFF subject runner scaffold (M8-GPU-T007d).

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


def run_gpu_alff_subject(
    *,
    subject_id: str,
    input_functional: str | Path,
    derivatives_dir: str | Path,
    run_id: str,
    tr: float,
    frequency_band: tuple[float, float] = (0.01, 0.08),
    compute_falff: bool = True,
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
        "ok": True,
        "node_id": "gpu_alff_subject",
        "backend": "gpu",
        "subject_id": subject_id,
        "run_id": run_id,
        "cuda_called": False,
        "gpu_called": False,
        "tensor_allocated": False,
        "runs_training": False,
        "runs_model_inference": False,
        "writes_rawdata": False,
        "errors": [],
        "warnings": [],
    }

    if not approved:
        result["ok"] = False
        result["errors"].append("GPU ALFF subject requires approved=true.")
        return result

    if not subject_id or not isinstance(subject_id, str):
        result["ok"] = False
        result["errors"].append(f"Invalid subject_id: {subject_id!r}.")
        return result

    # ── Input validation ──
    derivatives = Path(derivatives_dir)
    input_path = Path(input_functional)
    if not is_scoped_derivative_path(input_path, derivatives):
        result["ok"] = False
        result["errors"].append(f"Input functional not under derivatives_dir: {input_functional}")
        return result

    # ── TR ──
    if not isinstance(tr, int | float) or tr != tr or tr == float("inf") or tr <= 0 or tr < 0.1 or tr > 10.0:
        result["ok"] = False
        result["errors"].append(f"Invalid TR: {tr}. Must be 0.1 <= TR <= 10.0.")
        return result

    # ── Frequency band ──
    if not isinstance(frequency_band, list | tuple) or len(frequency_band) != 2:
        result["ok"] = False
        result["errors"].append("frequency_band must be [low, high].")
        return result
    low, high = frequency_band
    nyquist = 1.0 / (2.0 * tr)
    if not isinstance(low, int | float) or not isinstance(high, int | float):
        result["ok"] = False
        result["errors"].append("Frequency band values must be numeric.")
        return result
    if low != low or high != high or low == float("inf") or high == float("inf"):
        result["ok"] = False
        result["errors"].append("Frequency band values must be finite.")
        return result
    if low <= 0 or high <= low or high >= nyquist:
        result["ok"] = False
        result["errors"].append(f"Invalid band [{low}, {high}] for TR={tr} (Nyquist={nyquist:.3f}). Need 0<low<high<Nyquist.")
        return result

    if not isinstance(compute_falff, bool):
        result["ok"] = False
        result["errors"].append("compute_falff must be a boolean.")
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
        max_elements=20_000_000,
        max_bytes=512 * 1024 * 1024,
    ):
        return result

    # ── Output scope ──
    output_dir = derivatives / "gpu" / "gpu_alff_subject" / run_id / subject_id
    provenance = {
        "subject_id": subject_id,
        "run_id": run_id,
        "tr": tr,
        "frequency_band": list(frequency_band),
        "compute_falff": compute_falff,
        "device": device,
        "dry_run": dry_run,
    }
    provenance_path = write_gpu_provenance(output_dir, provenance)

    outputs = {
        "output_dir": str(output_dir),
        "provenance": str(provenance_path),
    }
    if dry_run:
        outputs["alff_map"] = str(output_dir / "alff_map.nii.gz")
        if compute_falff:
            outputs["falff_map"] = str(output_dir / "falff_map.nii.gz")
    else:
        result["stage"] = "preflight_completed"
        result["warnings"].append("ALFF computation not executed (dry_run=False, but runner is scaffold-only).")

    result["outputs"] = outputs
    return result


# //@source://MedImage Agent/AUDIT
# Backward-compatibility alias for existing nodes/gpu_alff_node.py
run_alff_subject = run_gpu_alff_subject
