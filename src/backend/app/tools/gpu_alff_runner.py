"""GPU ALFF subject runner scaffold (M8-GPU-T007d).

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
    """Check if path is under the scoped directory (no rawdata, no traversal)."""
    try:
        resolved_path = path.resolve()
        resolved_scope = scope_dir.resolve()
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
    if not _is_scoped_path(input_path, derivatives):
        result["ok"] = False
        result["errors"].append(f"Input functional not under derivatives_dir: {input_functional}")
        return result

    # ── TR ──
    if not isinstance(tr, (int, float)) or tr != tr or tr == float("inf") or tr <= 0 or tr < 0.1 or tr > 10.0:
        result["ok"] = False
        result["errors"].append(f"Invalid TR: {tr}. Must be 0.1 <= TR <= 10.0.")
        return result

    # ── Frequency band ──
    if not isinstance(frequency_band, (list, tuple)) or len(frequency_band) != 2:
        result["ok"] = False
        result["errors"].append("frequency_band must be [low, high].")
        return result
    low, high = frequency_band
    nyquist = 1.0 / (2.0 * tr)
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
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
            max_elements=20_000_000,
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
    output_dir = derivatives / "gpu" / "gpu_alff_subject" / run_id / subject_id
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "subject_id": subject_id,
        "run_id": run_id,
        "tr": tr,
        "frequency_band": list(frequency_band),
        "compute_falff": compute_falff,
        "device": device,
        "dry_run": dry_run,
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    outputs = {
        "output_dir": str(output_dir),
        "provenance": str(output_dir / "provenance.json"),
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
