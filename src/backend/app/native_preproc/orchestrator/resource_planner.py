"""Conservative resource planning for subject-level native preprocessing.

This module never changes scientific parameters.  It only derives a bounded
process and native-thread budget from a current machine snapshot and the
registered subject requests.
"""
from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.backend.app.schemas.native_preproc_api import (
    NativeCpuExecutionPolicy,
    NativeFullPreprocRequest,
)


@dataclass(frozen=True)
class ResourceSnapshot:
    logical_cpus: int
    cpu_percent: float | None
    total_memory_bytes: int | None
    available_memory_bytes: int | None
    source: str


@dataclass(frozen=True)
class ResourceDecision:
    scheduler_mode: str
    worker_count_requested: int | None
    worker_count_calculated: int
    worker_count_used: int
    threads_per_worker_calculated: int
    estimated_peak_bytes_per_subject: int
    available_memory_budget_bytes: int | None
    limiting_factors: list[str] = field(default_factory=list)
    calculation_inputs: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def capture_resource_snapshot() -> ResourceSnapshot:
    """Return a best-effort snapshot without making psutil a hard dependency."""
    logical_cpus = max(1, os.cpu_count() or 1)
    try:
        import psutil  # type: ignore[import-not-found]

        memory = psutil.virtual_memory()
        return ResourceSnapshot(
            logical_cpus=logical_cpus,
            cpu_percent=float(psutil.cpu_percent(interval=None)),
            total_memory_bytes=int(memory.total),
            available_memory_bytes=int(memory.available),
            source="psutil",
        )
    except Exception:
        return ResourceSnapshot(logical_cpus, None, None, None, "os.cpu_count")


def _input_bytes(request: NativeFullPreprocRequest) -> int:
    try:
        return max(1, Path(request.input_bold).stat().st_size)
    except OSError:
        # A dry-run or remote/temporarily unavailable input must stay safe.
        return 256 * 1024 * 1024


def estimate_peak_bytes_per_subject(requests: Iterable[NativeFullPreprocRequest]) -> int:
    """Conservative per-subject working-set estimate.

    Gzipped NIfTI files need an expansion allowance; spatial transforms and
    ReHo can retain additional arrays.  This deliberately overestimates rather
    than using a workstation-specific fixed worker count.
    """
    sizes = [_input_bytes(request) for request in requests]
    if not sizes:
        return 256 * 1024 * 1024
    stage_multiplier = 7
    return max(256 * 1024 * 1024, max(sizes) * stage_multiplier)


def plan_subject_execution(
    requests: list[NativeFullPreprocRequest], policy: NativeCpuExecutionPolicy
) -> ResourceDecision:
    snapshot = capture_resource_snapshot()
    subject_count = len(requests)
    estimated_peak = estimate_peak_bytes_per_subject(requests)
    requested = policy.max_subject_workers
    limiting: list[str] = []

    if policy.mode == "serial" or subject_count <= 1:
        limiting.append("serial_mode" if policy.mode == "serial" else "single_subject")
        return ResourceDecision(
            scheduler_mode=policy.mode,
            worker_count_requested=requested,
            worker_count_calculated=1,
            worker_count_used=1,
            threads_per_worker_calculated=1,
            estimated_peak_bytes_per_subject=estimated_peak,
            available_memory_budget_bytes=snapshot.available_memory_bytes,
            limiting_factors=limiting,
            calculation_inputs={**asdict(snapshot), "subject_count": subject_count},
        )

    reserve_cpu = policy.reserve_cpu_threads
    if reserve_cpu is None:
        reserve_cpu = max(1, min(2, snapshot.logical_cpus // 4))
    if snapshot.cpu_percent is not None and snapshot.cpu_percent >= 80:
        reserve_cpu = max(reserve_cpu, snapshot.logical_cpus // 2)
        limiting.append("high_system_cpu_load")
    usable_cpu = max(1, snapshot.logical_cpus - reserve_cpu)
    cpu_limited = max(1, usable_cpu)

    memory_budget = policy.memory_budget_bytes
    if memory_budget is None:
        memory_budget = snapshot.available_memory_bytes
    if memory_budget is None:
        # Resource visibility is required for automatic parallelism.
        limiting.append("memory_probe_unavailable_fallback_serial")
        worker_count = 1
    else:
        reserve_memory = max(512 * 1024 * 1024, int(memory_budget * 0.15))
        usable_memory = max(0, memory_budget - reserve_memory)
        memory_limited = usable_memory // estimated_peak
        if memory_limited < 1:
            limiting.append("available_memory")
        worker_count = max(1, min(subject_count, cpu_limited, max(1, memory_limited)))
        if worker_count == cpu_limited:
            limiting.append("available_cpu")
        if worker_count == max(1, memory_limited):
            limiting.append("available_memory")

    if requested is not None:
        worker_count = min(worker_count, requested)
        limiting.append("user_worker_ceiling")
    # A release safety boundary, not a normal operating default.
    worker_count = min(worker_count, 8)
    threads = policy.cpu_threads_per_worker or max(1, usable_cpu // worker_count)
    threads = max(1, min(threads, max(1, usable_cpu // worker_count)))
    return ResourceDecision(
        scheduler_mode=policy.mode,
        worker_count_requested=requested,
        worker_count_calculated=worker_count,
        worker_count_used=worker_count,
        threads_per_worker_calculated=threads,
        estimated_peak_bytes_per_subject=estimated_peak,
        available_memory_budget_bytes=memory_budget,
        limiting_factors=sorted(set(limiting)) or ["subject_count"],
        calculation_inputs={
            **asdict(snapshot),
            "subject_count": subject_count,
            "reserve_cpu_threads": reserve_cpu,
            "policy": policy.model_dump(mode="json"),
        },
    )


__all__ = ["ResourceDecision", "ResourceSnapshot", "capture_resource_snapshot", "plan_subject_execution"]
