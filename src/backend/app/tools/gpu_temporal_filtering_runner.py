"""GPU temporal filtering subject runner scaffold (M8-GPU-T009b).

Pure Python preflight — no torch import, no CUDA, no GPU allocation.
Uses gpu_safety.py guards. Bans mixed processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from src.backend.app.tools.gpu_utils import (
    apply_gpu_guard,
    is_scoped_derivative_path,
    write_gpu_provenance,
)


_ALLOWED_MODES = frozenset({"bandpass"})
_ALLOWED_METHODS = frozenset({"butterworth"})


def run_gpu_temporal_filtering_subject(
    *, subject_id: str, input_functional: str | Path, derivatives_dir: str | Path,
    run_id: str, tr: float, frequency_band: tuple[float, float] = (0.01, 0.08),
    filter_mode: str = "bandpass", filter_method: str = "butterworth",
    filter_order: int = 2, device: str = "auto",
    functional_shape: Sequence[int] | None = None, dtype_bytes: int = 4,
    batch_size: int = 1, timeout_seconds: int = 60,
    require_gpu: bool = False, torch_cuda_available: bool | None = None,
    device_count: int | None = None, active_jobs: int = 0,
    max_concurrent_jobs: int = 1, approved: bool = True, dry_run: bool = False,
) -> dict:

    result: dict = {
        "ok": True, "node_id": "gpu_temporal_filtering_subject", "backend": "gpu",
        "subject_id": subject_id, "run_id": run_id,
        "cuda_called": False, "gpu_called": False, "tensor_allocated": False,
        "runs_training": False, "runs_model_inference": False,
        "runs_nuisance_regression": False, "runs_alff": False,
        "runs_reho": False, "runs_functional_connectivity": False,
        "writes_rawdata": False, "errors": [], "warnings": [],
    }

    if not approved:
        result["ok"] = False; result["errors"].append("GPU temporal filtering requires approved=true.")
        return result
    if not subject_id or not isinstance(subject_id, str):
        result["ok"] = False; result["errors"].append(f"Invalid subject_id: {subject_id!r}.")
        return result

    # Input
    derivatives = Path(derivatives_dir)
    input_path = Path(input_functional)
    if not is_scoped_derivative_path(input_path, derivatives):
        result["ok"] = False; result["errors"].append(f"Input not under derivatives_dir: {input_functional}")
        return result

    # TR
    if not isinstance(tr, (int, float)) or tr != tr or tr == float("inf") or tr <= 0 or tr < 0.1 or tr > 10.0:
        result["ok"] = False; result["errors"].append(f"Invalid TR: {tr}. Must be 0.1 <= TR <= 10.0.")
        return result

    # Band + Nyquist
    if not isinstance(frequency_band, (list, tuple)) or len(frequency_band) != 2:
        result["ok"] = False; result["errors"].append("frequency_band must be [low, high].")
        return result
    low, high = frequency_band
    nyquist = 1.0 / (2.0 * tr)
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)) or low != low or high != high or low == float("inf") or high == float("inf"):
        result["ok"] = False; result["errors"].append("Frequency band values must be finite numeric.")
        return result
    if low <= 0 or high <= low or high >= nyquist:
        result["ok"] = False; result["errors"].append(f"Invalid band [{low},{high}] TR={tr} Nyq={nyquist:.3f}. Need 0<low<high<Nyquist.")
        return result

    # Filter params
    if filter_mode not in _ALLOWED_MODES:
        result["ok"] = False; result["errors"].append(f"Invalid filter_mode: {filter_mode}. Allowed: bandpass.")
        return result
    if filter_method not in _ALLOWED_METHODS:
        result["ok"] = False; result["errors"].append(f"Invalid filter_method: {filter_method}. Allowed: butterworth.")
        return result
    if not isinstance(filter_order, int) or filter_order < 1 or filter_order > 4:
        result["ok"] = False; result["errors"].append(f"Invalid filter_order: {filter_order}. Must be 1–4.")
        return result

    # GPU guard
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

    # Output
    output_dir = derivatives / "gpu" / "gpu_temporal_filtering_subject" / run_id / subject_id
    provenance = {
        "subject_id": subject_id, "run_id": run_id, "tr": tr,
        "frequency_band": list(frequency_band), "filter_mode": filter_mode,
        "filter_method": filter_method, "filter_order": filter_order,
        "device": device, "dry_run": dry_run,
    }
    provenance_path = write_gpu_provenance(output_dir, provenance)
    outputs = {"output_dir": str(output_dir), "provenance": str(provenance_path)}
    if dry_run:
        outputs["filtered_functional"] = str(output_dir / "filtered_func.nii.gz")
    else:
        result["stage"] = "preflight_completed"
        result["warnings"].append("Temporal filtering not executed (runner is scaffold-only).")
    result["outputs"] = outputs
    return result


# Backward-compatibility alias for existing nodes/gpu_temporal_filtering_node.py
run_temporal_filtering_subject = run_gpu_temporal_filtering_subject
