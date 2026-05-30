"""GPU functional connectivity subject runner scaffold (M8-GPU-T010b).

Pure Python preflight — no torch import, no CUDA, no GPU allocation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from src.backend.app.safety.gpu_safety import (
    validate_gpu_device, check_cuda_availability,
    validate_gpu_memory_budget, validate_gpu_timeout,
    validate_gpu_concurrency,
)


def _is_scoped_path(path: Path, scope_dir: Path) -> bool:
    try:
        rp = path.resolve(); rs = scope_dir.resolve()
        rp.relative_to(rs)
    except ValueError:
        return False
    ps = str(rp).replace("\\", "/")
    if ".." in ps: return False
    if any(seg in ("rawdata", "data") for seg in rp.parts): return False
    return True


_ALLOWED_METHODS = frozenset({"pearson"})
_ALLOWED_ATLAS_SOURCES = frozenset({"approved_builtin_atlas", "scoped_derivatives_atlas"})
_MIN_ROI, _MAX_ROI = 2, 512


def run_gpu_functional_connectivity_subject(
    *, subject_id: str, derivatives_dir: str | Path, run_id: str,
    input_functional: str | Path | None = None,
    input_timeseries: str | Path | None = None,
    atlas_path: str | Path | None = None,
    atlas_source: str = "approved_builtin_atlas",
    roi_count: int | None = None, timepoints: int | None = None,
    correlation_method: str = "pearson", fisher_z: bool = True,
    output_format: str = "json_csv",
    device: str = "auto", functional_shape: Sequence[int] | None = None,
    dtype_bytes: int = 4, batch_size: int = 1, timeout_seconds: int = 60,
    require_gpu: bool = False, torch_cuda_available: bool | None = None,
    device_count: int | None = None, active_jobs: int = 0,
    max_concurrent_jobs: int = 1, approved: bool = True, dry_run: bool = False,
) -> dict:

    result: dict = {
        "ok": True, "node_id": "gpu_functional_connectivity_subject", "backend": "gpu",
        "subject_id": subject_id, "run_id": run_id,
        "cuda_called": False, "gpu_called": False, "tensor_allocated": False,
        "runs_training": False, "runs_model_inference": False,
        "runs_nuisance_regression": False, "runs_alff": False,
        "runs_reho": False, "runs_temporal_filtering": False,
        "writes_rawdata": False, "errors": [], "warnings": [],
    }

    if not approved:
        result["ok"] = False; result["errors"].append("GPU FC requires approved=true.")
        return result
    if not subject_id or not isinstance(subject_id, str):
        result["ok"] = False; result["errors"].append(f"Invalid subject_id: {subject_id!r}.")
        return result

    derivatives = Path(derivatives_dir)

    # Input
    if not input_functional and not input_timeseries:
        result["ok"] = False; result["errors"].append("Must provide input_functional or input_timeseries.")
        return result
    for label, p in [("functional", input_functional), ("timeseries", input_timeseries)]:
        if p and not _is_scoped_path(Path(p), derivatives):
            result["ok"] = False; result["errors"].append(f"Input {label} not under derivatives_dir: {p}")
            return result

    # Atlas
    if atlas_source not in _ALLOWED_ATLAS_SOURCES:
        result["ok"] = False; result["errors"].append(f"Invalid atlas_source: {atlas_source}.")
        return result
    if atlas_path and not _is_scoped_path(Path(atlas_path), derivatives):
        result["ok"] = False; result["errors"].append(f"Atlas not under derivatives_dir: {atlas_path}")
        return result

    # ROI
    if roi_count is not None:
        if not isinstance(roi_count, int) or roi_count < _MIN_ROI or roi_count > _MAX_ROI:
            result["ok"] = False; result["errors"].append(f"roi_count {roi_count} not in [{_MIN_ROI},{_MAX_ROI}].")
            return result
    if timepoints is not None and (not isinstance(timepoints, int) or timepoints < 2):
        result["ok"] = False; result["errors"].append(f"Invalid timepoints: {timepoints}.")
        return result

    # Correlation
    if correlation_method not in _ALLOWED_METHODS:
        result["ok"] = False; result["errors"].append(f"Invalid correlation_method: {correlation_method}. Allowed: pearson.")
        return result
    if not isinstance(fisher_z, bool):
        result["ok"] = False; result["errors"].append("fisher_z must be boolean.")
        return result

    # GPU guard
    dev = validate_gpu_device(device); result["gpu_guard"] = dev.to_dict()
    if not dev.ok:
        result["ok"] = False; result["errors"].extend(e.message for e in dev.errors)
        return result
    cuda = check_cuda_availability(torch_cuda_available=torch_cuda_available, device_count=device_count, require_gpu=require_gpu)
    result["warnings"].extend(w.message for w in cuda.warnings)
    if not cuda.ok:
        result["ok"] = False; result["errors"].extend(e.message for e in cuda.errors)
        return result
    if functional_shape:
        mem = validate_gpu_memory_budget(shape=functional_shape, dtype_bytes=dtype_bytes, batch_size=batch_size, max_elements=30_000_000, max_bytes=512*1024*1024)
        if not mem.ok:
            result["ok"] = False; result["errors"].extend(e.message for e in mem.errors)
            return result
        result["estimated_bytes"] = mem.estimated_bytes
    tm = validate_gpu_timeout(timeout_seconds, max_timeout_seconds=120)
    if not tm.ok:
        result["ok"] = False; result["errors"].extend(e.message for e in tm.errors)
        return result
    conc = validate_gpu_concurrency(active_jobs=active_jobs, max_concurrent_jobs=max_concurrent_jobs)
    if not conc.ok:
        result["ok"] = False; result["errors"].extend(e.message for e in conc.errors)
        return result

    # Output
    output_dir = derivatives / "gpu" / "gpu_functional_connectivity_subject" / run_id / subject_id
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "subject_id": subject_id, "run_id": run_id,
        "atlas_source": atlas_source, "roi_count": roi_count,
        "correlation_method": correlation_method, "fisher_z": fisher_z,
        "device": device, "dry_run": dry_run,
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    outputs = {"output_dir": str(output_dir), "provenance": str(output_dir / "provenance.json")}
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
