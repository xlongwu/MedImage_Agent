"""Conservative, auditable resource planning for optional CuPy stages.

The planner is deliberately independent of the scientific kernels.  It may
choose resources, but it never changes a scientific parameter or turns an
unsafe GPU request into a successful CPU execution.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

from src.backend.app.safety.gpu_safety import validate_live_gpu_memory
from src.backend.app.schemas.native_preproc_api import NativeComputePolicy
from src.backend.app.tools.gpu_utils import detect_gpu


GPU_CAPABLE_STAGES = frozenset({
    "alff", "falff", "temporal_filtering", "nuisance_regression", "functional_connectivity",
    "smoothing", "atlas_resampling",
})

# These are conservative peak-workspace multipliers, not hardware limits.  A
# kernel performs a second live preflight immediately before allocation.
_WORKSPACE_FACTORS = {
    "alff": 7.0,  # input, demeaned, rFFT complex workspace, amplitudes, outputs
    "falff": 7.0,
    "temporal_filtering": 5.0,
    "nuisance_regression": 4.0,
    "functional_connectivity": 3.0,
    "smoothing": 5.0,
    "atlas_resampling": 3.0,
}


@dataclass(frozen=True)
class GpuStagePlan:
    stage_id: str
    requested_backend: str
    selected_backend: str
    fallback_allowed: bool
    cupy_available: bool
    gpu_available: bool
    device_id: str | None
    device_name: str | None
    cupy_version: str | None
    cuda_runtime_version: int | None
    driver_version: int | None
    total_vram_bytes: int | None
    free_vram_bytes: int | None
    usable_vram_bytes: int | None
    estimated_input_bytes: int
    estimated_peak_bytes: int
    chunk_size: int
    gpu_jobs_calculated: int
    predicted_cpu_seconds: float | None
    predicted_gpu_seconds: float | None
    validation_level: str
    limiting_factors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)

    @property
    def require_gpu(self) -> bool:
        return self.requested_backend == "gpu"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _requested_backend(stage_id: str, policy: NativeComputePolicy) -> str:
    # CPU/control-plane stages are never coerced to GPU merely because the
    # run-level preference is GPU.  A future stage release must opt in here.
    if stage_id not in GPU_CAPABLE_STAGES:
        return "cpu"
    return policy.stage_backends.get(stage_id, policy.backend)


def _dtype_bytes(policy: NativeComputePolicy) -> int:
    return 8 if policy.precision == "float64" else 4


def _live_gpu_snapshot() -> dict[str, Any]:
    """Return CuPy capability plus live memory without importing CuPy on CPU use."""
    capability = detect_gpu()
    snapshot: dict[str, Any] = {**capability, "free_vram_bytes": None, "total_vram_bytes": None, "gpu_utilization_percent": None}
    if not capability.get("gpu_available"):
        return snapshot
    try:
        import cupy as cp

        snapshot["cupy_version"] = str(cp.__version__)

        with cp.cuda.Device(0):
            free_bytes, total_bytes = cp.cuda.runtime.memGetInfo()
        snapshot["free_vram_bytes"] = int(free_bytes)
        snapshot["total_vram_bytes"] = int(total_bytes)
    except Exception as exc:
        snapshot["gpu_available"] = False
        snapshot.setdefault("warnings", []).append(f"GPU memory preflight failed: {exc}")
    return snapshot


def plan_gpu_stage(
    stage_id: str,
    *,
    input_shape: tuple[int, ...],
    policy: NativeComputePolicy,
    subject_count: int = 1,
    validation_level: str = "reference_compared",
    allow_auto_gpu: bool = False,
) -> GpuStagePlan:
    """Make a deterministic decision from the policy, shape and live GPU state.

    ``auto`` intentionally remains CPU until a stage is explicitly released
    for auto-selection with real-device benchmark evidence.  Explicit ``gpu``
    still receives the full capability and memory preflight.
    """
    requested = _requested_backend(stage_id, policy)
    dtype_bytes = _dtype_bytes(policy)
    element_count = 1
    for dimension in input_shape:
        element_count *= max(1, int(dimension))
    input_bytes = element_count * dtype_bytes
    workspace_factor = _WORKSPACE_FACTORS.get(stage_id, 1.0)
    estimated_peak = int(input_bytes * workspace_factor)
    fallback_allowed = requested == "auto" and policy.allow_cpu_fallback
    base = dict(
        stage_id=stage_id,
        requested_backend=requested,
        fallback_allowed=fallback_allowed,
        estimated_input_bytes=input_bytes,
        estimated_peak_bytes=estimated_peak,
        validation_level=validation_level,
    )

    if stage_id not in GPU_CAPABLE_STAGES:
        return GpuStagePlan(
            **base,
            selected_backend="cpu",
            cupy_available=False,
            gpu_available=False,
            device_id=None,
            device_name=None,
            cupy_version=None,
            cuda_runtime_version=None,
            driver_version=None,
            total_vram_bytes=None,
            free_vram_bytes=None,
            usable_vram_bytes=None,
            chunk_size=max(1, input_shape[0] if input_shape else 1),
            gpu_jobs_calculated=0,
            predicted_cpu_seconds=None,
            predicted_gpu_seconds=None,
            limiting_factors=["stage_is_cpu_only"],
            blocking_issues=([] if requested != "gpu" else ["GPU backend is not released for this stage."]),
        )

    if requested == "cpu":
        return GpuStagePlan(
            **base,
            selected_backend="cpu",
            cupy_available=False,
            gpu_available=False,
            device_id=None,
            device_name=None,
            cupy_version=None,
            cuda_runtime_version=None,
            driver_version=None,
            total_vram_bytes=None,
            free_vram_bytes=None,
            usable_vram_bytes=None,
            chunk_size=max(1, input_shape[0] if input_shape else 1),
            gpu_jobs_calculated=0,
            predicted_cpu_seconds=None,
            predicted_gpu_seconds=None,
            limiting_factors=["requested_cpu"],
        )

    snapshot = _live_gpu_snapshot()
    cupy_available = bool(snapshot.get("cupy_available"))
    gpu_available = bool(snapshot.get("gpu_available"))
    free_bytes = snapshot.get("free_vram_bytes")
    total_bytes = snapshot.get("total_vram_bytes")
    warnings = [str(item) for item in snapshot.get("warnings", [])]
    limiting: list[str] = []
    blocking: list[str] = []
    if not cupy_available:
        limiting.append("cupy_unavailable")
    if not gpu_available:
        limiting.append("gpu_unavailable")

    # Keep a dynamic reserve: at least 512 MiB and at least 15 percent of the
    # live device.  A caller's budget can only tighten the usable amount.
    usable: int | None = None
    if isinstance(free_bytes, int) and isinstance(total_bytes, int):
        reserve = max(512 * 1024 * 1024, int(total_bytes * 0.15))
        usable = max(0, free_bytes - reserve)
        if policy.gpu_memory_budget_bytes is not None:
            usable = min(usable, policy.gpu_memory_budget_bytes)
    elif gpu_available:
        limiting.append("live_vram_probe_failed")

    spatial_items = max(1, int(input_shape[0]) * int(input_shape[1]) * int(input_shape[2])) if len(input_shape) >= 3 else max(1, element_count)
    per_item_peak = max(1, int(estimated_peak / spatial_items))
    max_chunk = spatial_items
    if policy.chunk_size is not None:
        max_chunk = min(max_chunk, policy.chunk_size)
    chunk = max_chunk
    jobs = 0
    if usable is not None:
        live_guard = validate_live_gpu_memory(
            estimated_peak_bytes=estimated_peak,
            free_vram_bytes=free_bytes if isinstance(free_bytes, int) else None,
            total_vram_bytes=total_bytes if isinstance(total_bytes, int) else None,
            user_budget_bytes=policy.gpu_memory_budget_bytes,
        )
        chunk = min(max_chunk, max(1, usable // per_item_peak))
        chunk_peak = min(estimated_peak, per_item_peak * chunk)
        if not live_guard.ok and chunk_peak > usable:
            limiting.append("insufficient_vram")
        else:
            jobs = max(1, usable // max(1, chunk_peak))
            jobs = min(jobs, max(1, subject_count))
            if policy.max_gpu_jobs is not None:
                jobs = min(jobs, policy.max_gpu_jobs)
    if requested == "auto" and not allow_auto_gpu:
        limiting.append("auto_gpu_not_released_for_stage")

    selected = "gpu"
    if not gpu_available or usable is None or "insufficient_vram" in limiting or (requested == "auto" and not allow_auto_gpu):
        selected = "cpu" if requested == "auto" else "blocked"
        if requested == "gpu":
            blocking.append("GPU backend preflight did not satisfy capability, validation, or memory requirements.")

    return GpuStagePlan(
        **base,
        selected_backend=selected,
        cupy_available=cupy_available,
        gpu_available=gpu_available,
        device_id="cuda:0" if gpu_available else None,
        device_name=str(snapshot.get("device_name")) if snapshot.get("device_name") else None,
        cupy_version=str(snapshot.get("cupy_version")) if snapshot.get("cupy_version") else None,
        cuda_runtime_version=int(snapshot["cuda_runtime_version"]) if isinstance(snapshot.get("cuda_runtime_version"), int) else None,
        driver_version=int(snapshot["driver_version"]) if isinstance(snapshot.get("driver_version"), int) else None,
        total_vram_bytes=int(total_bytes) if isinstance(total_bytes, int) else None,
        free_vram_bytes=int(free_bytes) if isinstance(free_bytes, int) else None,
        usable_vram_bytes=usable,
        chunk_size=int(chunk),
        gpu_jobs_calculated=int(jobs),
        predicted_cpu_seconds=None,
        predicted_gpu_seconds=None,
        limiting_factors=limiting,
        warnings=warnings,
        blocking_issues=blocking,
    )


@contextmanager
def gpu_device_lock(device_id: str = "cuda:0", *, max_jobs: int = 1) -> Iterator[None]:
    """Acquire a cross-process device token for one GPU stage.

    The lock has no scientific authority: failure is surfaced to the caller,
    which can fall back only when its policy is ``auto``.  A stale lock is
    discarded conservatively after an hour so a crashed desktop process cannot
    permanently block future reviewed runs.
    """
    safe_name = device_id.replace(":", "_")
    fd: int | None = None
    path: Path | None = None
    for slot in range(max(1, int(max_jobs))):
        candidate = Path(tempfile.gettempdir()) / f"medimage-agent-{safe_name}-slot-{slot}.lock"
        try:
            if candidate.exists() and time.time() - candidate.stat().st_mtime > 3600:
                candidate.unlink(missing_ok=True)
            fd = os.open(str(candidate), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            path = candidate
            break
        except FileExistsError:
            continue
    if fd is None or path is None:
        raise RuntimeError("GPU_DEVICE_BUSY: all reviewed GPU device tokens are currently held.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "device": device_id, "created_at": time.time(), "max_jobs": max_jobs}, handle)
        yield
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


__all__ = ["GPU_CAPABLE_STAGES", "GpuStagePlan", "gpu_device_lock", "plan_gpu_stage"]
