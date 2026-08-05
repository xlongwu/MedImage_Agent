"""Versioned, path-free local performance feedback for GPU stage planning."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from src.backend.app.runtime.atomic_file import atomic_write_json

MODEL_VERSION = 1
MODEL_FILENAME = "gpu_performance_profiles.json"
_MAX_SAMPLES_PER_PROFILE = 32


def performance_model_path(root: str | Path) -> Path:
    return Path(root) / MODEL_FILENAME


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    if not isinstance(payload, dict) or payload.get("model_version") != MODEL_VERSION:
        return {"model_version": MODEL_VERSION, "profiles": {}}
    if not isinstance(payload.get("profiles"), dict):
        payload["profiles"] = {}
    return payload


def workload_fingerprint(compute: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return a stable fingerprint without recording machine-local paths."""
    validation = compute.get("validation") if isinstance(compute.get("validation"), dict) else {}
    plan = validation.get("plan") if isinstance(validation.get("plan"), dict) else {}
    identity = {
        "stage_id": plan.get("stage_id"),
        "device_name": plan.get("device_name"),
        "cupy_version": plan.get("cupy_version"),
        "cuda_runtime_version": plan.get("cuda_runtime_version"),
        "driver_version": plan.get("driver_version"),
        "algorithm_version": validation.get("algorithm_version"),
        "dtype": validation.get("dtype"),
        "estimated_input_bytes": plan.get("estimated_input_bytes"),
        "estimated_peak_bytes": plan.get("estimated_peak_bytes"),
        "chunk_size": plan.get("chunk_size"),
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24], identity


def record_gpu_measurement(root: str | Path, compute: dict[str, Any]) -> dict[str, Any] | None:
    """Persist one completed GPU stage measurement for later conservative use."""
    if compute.get("actual_backend") != "gpu-cupy":
        return None
    runtime = compute.get("runtime") if isinstance(compute.get("runtime"), dict) else {}
    total = runtime.get("total_seconds")
    if not isinstance(total, float | int) or total < 0:
        return None
    path = performance_model_path(root)
    model = _load(path)
    fingerprint, identity = workload_fingerprint(compute)
    profiles: dict[str, Any] = model["profiles"]
    profile = profiles.setdefault(fingerprint, {"identity": identity, "samples": []})
    samples = profile.setdefault("samples", [])
    if not isinstance(samples, list):
        samples = profile["samples"] = []
    memory = compute.get("memory") if isinstance(compute.get("memory"), dict) else {}
    samples.append({
        "total_seconds": float(total),
        "transfer_seconds": float(runtime.get("transfer_seconds") or 0.0),
        "compute_seconds": float(runtime.get("compute_seconds") or 0.0),
        "estimated_peak_bytes": memory.get("estimated_peak_bytes"),
        "cold": len(samples) == 0,
    })
    del samples[:-_MAX_SAMPLES_PER_PROFILE]
    totals = [float(sample["total_seconds"]) for sample in samples if isinstance(sample.get("total_seconds"), int | float)]
    profile["summary"] = {
        "sample_count": len(totals),
        "median_total_seconds": float(median(totals)) if totals else None,
        "cold_sample_count": sum(bool(sample.get("cold")) for sample in samples),
    }
    atomic_write_json(path, model, schema_version=1)
    return {"fingerprint": fingerprint, **profile["summary"]}


def clear_gpu_performance_model(root: str | Path) -> bool:
    path = performance_model_path(root)
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


__all__ = [
    "MODEL_FILENAME", "MODEL_VERSION", "clear_gpu_performance_model",
    "performance_model_path", "record_gpu_measurement", "workload_fingerprint",
]
