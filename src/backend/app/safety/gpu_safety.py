"""GPU runtime/resource safety guard (M8-GPU-T003).

Pure Python — no torch import, no CUDA, no GPU calls.
Works in CI, local dev, and GPU-absent environments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal, Sequence


# ── Data structures ──

@dataclass
class GpuSafetyIssue:
    code: str
    severity: Literal["error", "warning"]
    message: str

    def to_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class GpuSafetyResult:
    ok: bool = True
    errors: list[GpuSafetyIssue] = field(default_factory=list)
    warnings: list[GpuSafetyIssue] = field(default_factory=list)
    device: str | None = None
    estimated_bytes: int | None = None
    cleanup_recommended: bool = False

    def merge(self, other: GpuSafetyResult) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if self.device is None:
            self.device = other.device
        if self.estimated_bytes is None:
            self.estimated_bytes = other.estimated_bytes
        self.cleanup_recommended = self.cleanup_recommended or other.cleanup_recommended
        if self.ok and not other.ok:
            self.ok = False

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "device": self.device,
            "estimated_bytes": self.estimated_bytes,
            "cleanup_recommended": self.cleanup_recommended,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ── Allowed device set ──

_ALLOWED_DEVICES = frozenset({"auto", "cpu", "cuda:0"})

_FORBIDDEN_DEVICE_CHARS = frozenset({";", "&", "|", "`", "$", ">", "<", "\n", "\r"})


# ── Device validation ──

def validate_gpu_device(
    device: str | None,
    *,
    allow_cpu: bool = True,
    allow_cuda0: bool = True,
    allow_auto: bool = True,
) -> GpuSafetyResult:
    result = GpuSafetyResult()

    if device is None or not isinstance(device, str) or not device.strip():
        result.errors.append(GpuSafetyIssue(
            code="GPU_DEVICE_INVALID",
            severity="error",
            message=f"Invalid or empty device: {device!r}.",
        ))
        result.ok = False
        return result

    device = device.strip()

    if any(c in device for c in _FORBIDDEN_DEVICE_CHARS):
        result.errors.append(GpuSafetyIssue(
            code="GPU_DEVICE_HAS_FORBIDDEN_CHARS",
            severity="error",
            message=f"Device string contains forbidden characters: {device!r}.",
        ))
        result.ok = False
        return result

    if ".." in device or "/" in device or "\\" in device:
        result.errors.append(GpuSafetyIssue(
            code="GPU_DEVICE_INVALID",
            severity="error",
            message=f"Device string looks like a path: {device!r}.",
        ))
        result.ok = False
        return result

    allowed_set: set[str] = set()
    if allow_auto:
        allowed_set.add("auto")
    if allow_cpu:
        allowed_set.add("cpu")
    if allow_cuda0:
        allowed_set.add("cuda:0")

    if device not in allowed_set:
        result.errors.append(GpuSafetyIssue(
            code="GPU_DEVICE_NOT_ALLOWED",
            severity="error",
            message=f"Device not allowed: {device!r}. Allowed: {sorted(allowed_set)}.",
        ))
        result.ok = False
        return result

    result.device = device
    return result


# ── CUDA availability ──

def check_cuda_availability(
    *,
    torch_cuda_available: bool | None = None,
    device_count: int | None = None,
    require_gpu: bool = False,
) -> GpuSafetyResult:
    result = GpuSafetyResult()

    if torch_cuda_available is None:
        if require_gpu:
            result.errors.append(GpuSafetyIssue(
                code="GPU_UNAVAILABLE",
                severity="error",
                message="CUDA availability unknown and require_gpu=True.",
            ))
            result.ok = False
        else:
            result.warnings.append(GpuSafetyIssue(
                code="GPU_UNAVAILABLE",
                severity="warning",
                message="CUDA availability unknown.",
            ))
        return result

    if not torch_cuda_available:
        if require_gpu:
            result.errors.append(GpuSafetyIssue(
                code="GPU_UNAVAILABLE",
                severity="error",
                message="torch.cuda.is_available() is False and require_gpu=True.",
            ))
            result.ok = False
        else:
            result.warnings.append(GpuSafetyIssue(
                code="GPU_UNAVAILABLE",
                severity="warning",
                message="torch.cuda.is_available() is False.",
            ))
        return result

    if device_count is not None and device_count <= 0 and require_gpu:
        result.errors.append(GpuSafetyIssue(
            code="GPU_UNAVAILABLE",
            severity="error",
            message=f"device_count={device_count} and require_gpu=True.",
        ))
        result.ok = False
        return result

    return result


# ── Memory / tensor budget ──

def estimate_tensor_bytes(
    shape: Sequence[int],
    *,
    dtype_bytes: int = 4,
    batch_size: int = 1,
) -> int:
    total = 1
    for dim in shape:
        total *= dim
    return total * dtype_bytes * batch_size


def validate_gpu_memory_budget(
    shape: Sequence[int],
    *,
    dtype_bytes: int = 4,
    batch_size: int = 1,
    max_elements: int = 1_000_000,
    max_bytes: int = 256 * 1024 * 1024,
) -> GpuSafetyResult:
    result = GpuSafetyResult()

    if not isinstance(batch_size, int) or batch_size <= 0:
        result.errors.append(GpuSafetyIssue(
            code="GPU_BATCH_SIZE_INVALID",
            severity="error",
            message=f"Invalid batch_size: {batch_size}.",
        ))
        result.ok = False
        return result

    if not isinstance(dtype_bytes, int) or dtype_bytes <= 0:
        result.errors.append(GpuSafetyIssue(
            code="GPU_TENSOR_SHAPE_INVALID",
            severity="error",
            message=f"Invalid dtype_bytes: {dtype_bytes}.",
        ))
        result.ok = False
        return result

    if not shape or any(not isinstance(d, int) or d <= 0 for d in shape):
        result.errors.append(GpuSafetyIssue(
            code="GPU_TENSOR_SHAPE_INVALID",
            severity="error",
            message=f"Invalid tensor shape: {shape}.",
        ))
        result.ok = False
        return result

    elements = 1
    for dim in shape:
        elements *= dim

    if elements > max_elements:
        result.errors.append(GpuSafetyIssue(
            code="GPU_TENSOR_ELEMENTS_INVALID",
            severity="error",
            message=f"Tensor elements {elements} > max {max_elements}.",
        ))
        result.ok = False

    est_bytes = elements * dtype_bytes * batch_size
    result.estimated_bytes = est_bytes

    if est_bytes > max_bytes:
        result.errors.append(GpuSafetyIssue(
            code="GPU_MEMORY_BUDGET_EXCEEDED",
            severity="error",
            message=f"Estimated {est_bytes} bytes > max {max_bytes} bytes.",
        ))
        result.ok = False

    return result


def validate_live_gpu_memory(
    *,
    estimated_peak_bytes: int,
    free_vram_bytes: int | None,
    total_vram_bytes: int | None = None,
    user_budget_bytes: int | None = None,
) -> GpuSafetyResult:
    """Validate a planned peak against a fresh CuPy ``memGetInfo`` sample.

    This is intentionally separate from the old static tensor guard: a valid
    array shape can still be unsafe when a display workload or another process
    has consumed VRAM after planning.
    """
    result = GpuSafetyResult(estimated_bytes=estimated_peak_bytes)
    if estimated_peak_bytes <= 0:
        result.ok = False
        result.errors.append(GpuSafetyIssue("GPU_MEMORY_ESTIMATE_INVALID", "error", "Estimated GPU peak bytes must be positive."))
        return result
    if free_vram_bytes is None or free_vram_bytes < 0:
        result.ok = False
        result.errors.append(GpuSafetyIssue("GPU_VRAM_PROBE_FAILED", "error", "Live GPU free-memory probe is unavailable."))
        return result
    reserve = max(512 * 1024 * 1024, int((total_vram_bytes or free_vram_bytes) * 0.15))
    usable = max(0, free_vram_bytes - reserve)
    if user_budget_bytes is not None:
        usable = min(usable, user_budget_bytes)
    if estimated_peak_bytes > usable:
        result.ok = False
        result.cleanup_recommended = True
        result.errors.append(GpuSafetyIssue(
            "GPU_MEMORY_BUDGET_EXCEEDED",
            "error",
            f"Estimated peak {estimated_peak_bytes} bytes exceeds live usable VRAM {usable} bytes.",
        ))
    return result


# ── Timeout ──

def validate_gpu_timeout(
    timeout_seconds: int | float | None,
    *,
    max_timeout_seconds: int = 30,
) -> GpuSafetyResult:
    result = GpuSafetyResult()

    if timeout_seconds is None:
        return result

    if not isinstance(timeout_seconds, (int, float)):
        result.errors.append(GpuSafetyIssue(
            code="GPU_TIMEOUT_INVALID",
            severity="error",
            message=f"Non-numeric timeout: {timeout_seconds!r}.",
        ))
        result.ok = False
        return result

    if timeout_seconds <= 0:
        result.errors.append(GpuSafetyIssue(
            code="GPU_TIMEOUT_INVALID",
            severity="error",
            message=f"Timeout must be > 0, got: {timeout_seconds}.",
        ))
        result.ok = False
        return result

    if timeout_seconds > max_timeout_seconds:
        result.errors.append(GpuSafetyIssue(
            code="GPU_TIMEOUT",
            severity="error",
            message=f"Timeout {timeout_seconds}s > max {max_timeout_seconds}s.",
        ))
        result.ok = False

    return result


# ── Concurrency ──

def validate_gpu_concurrency(
    *,
    active_jobs: int = 0,
    max_concurrent_jobs: int = 1,
) -> GpuSafetyResult:
    result = GpuSafetyResult()

    if max_concurrent_jobs < 1:
        result.errors.append(GpuSafetyIssue(
            code="GPU_CONCURRENCY_BLOCKED",
            severity="error",
            message=f"Invalid max_concurrent_jobs: {max_concurrent_jobs}.",
        ))
        result.ok = False
        return result

    if active_jobs < 0:
        result.errors.append(GpuSafetyIssue(
            code="GPU_CONCURRENCY_BLOCKED",
            severity="error",
            message=f"Invalid active_jobs: {active_jobs}.",
        ))
        result.ok = False
        return result

    if active_jobs >= max_concurrent_jobs:
        result.errors.append(GpuSafetyIssue(
            code="GPU_CONCURRENCY_BLOCKED",
            severity="error",
            message=f"active_jobs={active_jobs} >= max={max_concurrent_jobs}.",
        ))
        result.ok = False

    return result


# ── OOM normalization ──

def normalize_gpu_exception(exc: BaseException) -> GpuSafetyResult:
    msg = str(exc).lower()
    if "out of memory" in msg:
        return GpuSafetyResult(
            ok=False,
            errors=[GpuSafetyIssue(
                code="GPU_OOM",
                severity="error",
                message=f"GPU out of memory: {exc}",
            )],
            cleanup_recommended=True,
        )
    if "dll" in msg or "driver" in msg or "cuda" in msg:
        return GpuSafetyResult(
            ok=False,
            errors=[GpuSafetyIssue(
                code="GPU_RUNTIME_UNAVAILABLE",
                severity="error",
                message=f"GPU CUDA runtime or driver is unavailable: {exc}",
            )],
        )
    return GpuSafetyResult(
        ok=False,
        errors=[GpuSafetyIssue(
            code="GPU_GUARD_FAILED",
            severity="error",
            message=f"Unexpected GPU error: {exc}",
        )],
    )


# ── Combined guard ──

def validate_gpu_runtime_request(
    *,
    device: str | None = None,
    shape: Sequence[int] | None = None,
    dtype_bytes: int = 4,
    batch_size: int = 1,
    timeout_seconds: int | float | None = 30,
    require_gpu: bool = False,
    torch_cuda_available: bool | None = None,
    device_count: int | None = None,
) -> GpuSafetyResult:
    result = GpuSafetyResult()

    if device is not None:
        dev_result = validate_gpu_device(device)
        result.merge(dev_result)

    cuda_result = check_cuda_availability(
        torch_cuda_available=torch_cuda_available,
        device_count=device_count,
        require_gpu=require_gpu,
    )
    result.merge(cuda_result)

    if shape is not None:
        mem_result = validate_gpu_memory_budget(
            shape=shape,
            dtype_bytes=dtype_bytes,
            batch_size=batch_size,
        )
        result.merge(mem_result)

    timeout_result = validate_gpu_timeout(timeout_seconds)
    result.merge(timeout_result)

    return result
