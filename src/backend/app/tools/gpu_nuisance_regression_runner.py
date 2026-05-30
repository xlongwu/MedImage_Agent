"""GPU nuisance regression subject runner scaffold (M8-GPU-T011b).

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


_ALLOWED_MODES = frozenset({"ols"})
_MIN_CONF, _MAX_CONF = 1, 64


def run_gpu_nuisance_regression_subject(
    *, subject_id: str, input_functional: str | Path,
    confounds_path: str | Path, derivatives_dir: str | Path, run_id: str,
    confound_columns: list[str] | None = None,
    regression_mode: str = "ols", include_intercept: bool = True,
    standardize_confounds: bool = True, allow_global_signal: bool = False,
    allow_scrubbing: bool = False, device: str = "auto",
    functional_shape: Sequence[int] | None = None, timepoints: int | None = None,
    n_confounds: int | None = None, dtype_bytes: int = 4, batch_size: int = 1,
    timeout_seconds: int = 60, require_gpu: bool = False,
    torch_cuda_available: bool | None = None, device_count: int | None = None,
    active_jobs: int = 0, max_concurrent_jobs: int = 1,
    approved: bool = True, dry_run: bool = False,
) -> dict:

    result: dict = {
        "ok": True, "node_id": "gpu_nuisance_regression_subject", "backend": "gpu",
        "subject_id": subject_id, "run_id": run_id,
        "cuda_called": False, "gpu_called": False, "tensor_allocated": False,
        "runs_training": False, "runs_model_inference": False,
        "runs_temporal_filtering": False, "runs_functional_connectivity": False,
        "runs_alff": False, "runs_reho": False,
        "allow_global_signal": allow_global_signal,
        "allow_scrubbing": allow_scrubbing,
        "writes_rawdata": False, "errors": [], "warnings": [],
    }

    if not approved:
        result["ok"] = False; result["errors"].append("GPU nuisance regression requires approved=true.")
        return result
    if not subject_id or not isinstance(subject_id, str):
        result["ok"] = False; result["errors"].append(f"Invalid subject_id: {subject_id!r}.")
        return result

    derivatives = Path(derivatives_dir)

    # Input
    for label, p in [("functional", input_functional), ("confounds", confounds_path)]:
        if not _is_scoped_path(Path(p), derivatives):
            result["ok"] = False; result["errors"].append(f"Input {label} not under derivatives_dir: {p}")
            return result

    # Confound columns
    if confound_columns is not None:
        if not isinstance(confound_columns, list) or not confound_columns:
            result["ok"] = False; result["errors"].append("confound_columns must be non-empty list.")
            return result
        if any(not isinstance(c, str) for c in confound_columns):
            result["ok"] = False; result["errors"].append("confound_columns must contain strings.")
            return result
        if len(set(confound_columns)) != len(confound_columns):
            result["ok"] = False; result["errors"].append("confound_columns must have unique names.")
            return result
        nc = len(confound_columns)
    elif n_confounds is not None:
        nc = n_confounds
    else:
        nc = 0

    if not isinstance(nc, int) or nc > _MAX_CONF:
        result["ok"] = False; result["errors"].append(f"n_confounds {nc} must be <= {_MAX_CONF}.")
        return result

    # Design matrix
    if timepoints is not None:
        if not isinstance(timepoints, int) or timepoints <= 2:
            result["ok"] = False; result["errors"].append(f"Invalid timepoints: {timepoints}.")
            return result
        n_reg = nc + int(include_intercept)
        if n_reg >= timepoints:
            result["ok"] = False; result["errors"].append(
                f"n_regressors({n_reg}) >= timepoints({timepoints}).")
            return result

    # Regression mode + policies
    if regression_mode not in _ALLOWED_MODES:
        result["ok"] = False; result["errors"].append(f"Invalid regression_mode: {regression_mode}. Allowed: ols.")
        return result
    if not isinstance(include_intercept, bool) or not isinstance(standardize_confounds, bool):
        result["ok"] = False; result["errors"].append("include_intercept and standardize_confounds must be bool.")
        return result
    if allow_global_signal:
        result["ok"] = False; result["errors"].append("Global signal regression blocked in first rollout.")
        return result
    if allow_scrubbing:
        result["ok"] = False; result["errors"].append("Scrubbing/censoring blocked in first rollout.")
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
    output_dir = derivatives / "gpu" / "gpu_nuisance_regression_subject" / run_id / subject_id
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "subject_id": subject_id, "run_id": run_id,
        "confound_columns": confound_columns, "n_confounds": nc,
        "timepoints": timepoints, "regression_mode": regression_mode,
        "include_intercept": include_intercept, "standardize_confounds": standardize_confounds,
        "allow_global_signal": allow_global_signal, "allow_scrubbing": allow_scrubbing,
        "device": device, "dry_run": dry_run,
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    outputs = {"output_dir": str(output_dir), "provenance": str(output_dir / "provenance.json")}
    if dry_run:
        outputs["cleaned_functional"] = str(output_dir / "cleaned_func.nii.gz")
    else:
        result["stage"] = "preflight_completed"
        result["warnings"].append("Nuisance regression not executed (runner is scaffold-only).")
    result["outputs"] = outputs
    return result


# Backward-compatibility alias for existing nodes/gpu_nuisance_regression_node.py
run_nuisance_regression_subject = run_gpu_nuisance_regression_subject
