"""GPU functional connectivity subject runner scaffold (M8-GPU-T010b).

Pure Python preflight — no torch import, no CUDA, no GPU allocation.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from src.backend.app.tools.gpu_utils import (
    apply_gpu_guard,
    is_scoped_derivative_path,
    write_gpu_provenance,
)

_ALLOWED_METHODS = frozenset({"pearson"})
_ALLOWED_ATLAS_SOURCES = frozenset({"approved_builtin_atlas", "scoped_derivatives_atlas"})
_MIN_ROI, _MAX_ROI = 2, 512


def run_gpu_functional_connectivity_subject(
    *,
    subject_id: str,
    derivatives_dir: str | Path,
    run_id: str,
    input_functional: str | Path | None = None,
    input_timeseries: str | Path | None = None,
    atlas_path: str | Path | None = None,
    atlas_source: str = "approved_builtin_atlas",
    roi_count: int | None = None,
    timepoints: int | None = None,
    correlation_method: str = "pearson",
    fisher_z: bool = True,
    output_format: str = "json_csv",
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
        "node_id": "gpu_functional_connectivity_subject",
        "backend": "gpu",
        "subject_id": subject_id,
        "run_id": run_id,
        "cuda_called": False,
        "gpu_called": False,
        "tensor_allocated": False,
        "runs_training": False,
        "runs_model_inference": False,
        "runs_nuisance_regression": False,
        "runs_alff": False,
        "runs_reho": False,
        "runs_temporal_filtering": False,
        "writes_rawdata": False,
        "errors": [],
        "warnings": [],
    }

    if not approved:
        result["ok"] = False
        result["errors"].append("GPU FC requires approved=true.")
        return result
    if not subject_id or not isinstance(subject_id, str):
        result["ok"] = False
        result["errors"].append(f"Invalid subject_id: {subject_id!r}.")
        return result

    derivatives = Path(derivatives_dir)

    # Input
    if not input_functional and not input_timeseries:
        result["ok"] = False
        result["errors"].append("Must provide input_functional or input_timeseries.")
        return result
    for label, p in [("functional", input_functional), ("timeseries", input_timeseries)]:
        if p and not is_scoped_derivative_path(Path(p), derivatives):
            result["ok"] = False
            result["errors"].append(f"Input {label} not under derivatives_dir: {p}")
            return result

    # Atlas
    if atlas_source not in _ALLOWED_ATLAS_SOURCES:
        result["ok"] = False
        result["errors"].append(f"Invalid atlas_source: {atlas_source}.")
        return result
    if atlas_path and not is_scoped_derivative_path(Path(atlas_path), derivatives):
        result["ok"] = False
        result["errors"].append(f"Atlas not under derivatives_dir: {atlas_path}")
        return result

    # ROI
    if roi_count is not None:
        if not isinstance(roi_count, int) or roi_count < _MIN_ROI or roi_count > _MAX_ROI:
            result["ok"] = False
            result["errors"].append(f"roi_count {roi_count} not in [{_MIN_ROI},{_MAX_ROI}].")
            return result
    if timepoints is not None and (not isinstance(timepoints, int) or timepoints < 2):
        result["ok"] = False
        result["errors"].append(f"Invalid timepoints: {timepoints}.")
        return result

    # Correlation
    if correlation_method not in _ALLOWED_METHODS:
        result["ok"] = False
        result["errors"].append(
            f"Invalid correlation_method: {correlation_method}. Allowed: pearson."
        )
        return result
    if not isinstance(fisher_z, bool):
        result["ok"] = False
        result["errors"].append("fisher_z must be boolean.")
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
        max_elements=30_000_000,
        max_bytes=512 * 1024 * 1024,
    ):
        return result

    # Output
    output_dir = derivatives / "gpu" / "gpu_functional_connectivity_subject" / run_id / subject_id
    provenance = {
        "subject_id": subject_id,
        "run_id": run_id,
        "atlas_source": atlas_source,
        "roi_count": roi_count,
        "correlation_method": correlation_method,
        "fisher_z": fisher_z,
        "device": device,
        "dry_run": dry_run,
    }
    provenance_path = write_gpu_provenance(output_dir, provenance)
    outputs = {"output_dir": str(output_dir), "provenance": str(provenance_path)}
    if dry_run:
        outputs["fc_matrix_json"] = str(output_dir / "fc_matrix.json")
        outputs["fc_matrix_csv"] = str(output_dir / "fc_matrix.csv")
    else:
        result["stage"] = "preflight_completed"
        result["warnings"].append("FC not executed (runner is scaffold-only).")
    result["outputs"] = outputs
    return result


# Backward-compatibility alias for existing nodes/gpu_functional_connectivity_node.py
run_functional_connectivity_subject = run_gpu_functional_connectivity_subject
