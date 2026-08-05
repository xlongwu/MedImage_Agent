"""Backend-neutral numerical boundary for released native GPU stages.

All functions return NumPy arrays at this boundary.  Native stages remain the
sole owners of NIfTI/TSV writing, artifact registration and provenance, so a
GPU computation cannot create a sidecar pipeline or bypass run manifests.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.backend.app.native_preproc.orchestrator.gpu_resource_planner import (
    GpuStagePlan,
    gpu_device_lock,
)
from src.backend.app.tools.gpu_utils import configure_cupy_cache_dir


@dataclass
class BackendComputeResult:
    ok: bool
    backend: str
    arrays: dict[str, np.ndarray] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    runtime: dict[str, float] = field(default_factory=dict)
    memory: dict[str, int | None] = field(default_factory=dict)
    fallback_reason: str | None = None
    validation: dict[str, Any] = field(default_factory=dict)

    def provenance(self) -> dict[str, Any]:
        return {
            "requested_backend": self.validation.get("requested_backend", self.backend),
            "actual_backend": self.backend,
            "fallback_reason": self.fallback_reason,
            "runtime": self.runtime,
            "memory": self.memory,
            "validation": self.validation,
        }


@dataclass
class GpuOperationResult:
    """Arrays plus synchronized device-transfer and kernel timings."""

    arrays: dict[str, np.ndarray]
    transfer_seconds: float
    compute_seconds: float


class GpuComputeError(RuntimeError):
    """Structured failure which a stage may only fall back from in auto mode."""


def cpu_compute_provenance(
    plan: GpuStagePlan,
    *,
    started_at: float,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    """Return the same timing shape as GPU provenance for a CPU reference call.

    CPU timings intentionally cover only the numerical operation.  File I/O,
    planning, and artifact registration are owned by the native stage and are
    not comparable to the GPU transfer/compute boundary.
    """
    elapsed = round(time.perf_counter() - started_at, 6)
    return {
        "requested_backend": plan.requested_backend,
        "actual_backend": "cpu-numpy",
        "fallback_reason": fallback_reason,
        "runtime": {
            "transfer_seconds": 0.0,
            "compute_seconds": elapsed,
            "total_seconds": elapsed,
        },
        "memory": {
            "estimated_peak_bytes": plan.estimated_peak_bytes,
            "chunk_size": plan.chunk_size,
        },
        "validation": {
            "requested_backend": plan.requested_backend,
            "validation_level": plan.validation_level,
            "algorithm_version": "native_numpy_phase02_v1",
            "dtype": "float32",
            "plan": plan.as_dict(),
        },
    }


def _runtime(start: float, transfer: float = 0.0, compute: float = 0.0) -> dict[str, float]:
    return {
        "transfer_seconds": round(transfer, 6),
        "compute_seconds": round(compute, 6),
        "total_seconds": round(time.perf_counter() - start, 6),
    }


def _gpu_result(
    plan: GpuStagePlan,
    operation: Callable[[Any], GpuOperationResult],
) -> BackendComputeResult:
    if plan.selected_backend != "gpu":
        raise GpuComputeError("; ".join(plan.blocking_issues or ["GPU backend was not selected by preflight."]))
    start = time.perf_counter()
    try:
        configure_cupy_cache_dir()
        import cupy as cp

        with gpu_device_lock(plan.device_id or "cuda:0", max_jobs=plan.gpu_jobs_calculated), cp.cuda.Device(0):
            before_free, total = cp.cuda.runtime.memGetInfo()
            operation_result = operation(cp)
            cp.cuda.Stream.null.synchronize()
            after_free, _ = cp.cuda.runtime.memGetInfo()
            cp.get_default_memory_pool().free_all_blocks()
            cp.get_default_pinned_memory_pool().free_all_blocks()
        return BackendComputeResult(
            ok=True,
            backend="gpu-cupy",
            arrays=operation_result.arrays,
            runtime=_runtime(
                start,
                transfer=operation_result.transfer_seconds,
                compute=operation_result.compute_seconds,
            ),
            memory={
                "free_vram_before_bytes": int(before_free),
                "free_vram_after_bytes": int(after_free),
                "total_vram_bytes": int(total),
                "estimated_peak_bytes": plan.estimated_peak_bytes,
                "chunk_size": plan.chunk_size,
            },
            validation={
                "requested_backend": plan.requested_backend,
                "validation_level": plan.validation_level,
                "algorithm_version": "native_cupy_tier1_v1",
                "cpu_reference_algorithm_version": "native_numpy_phase02_v1",
                "dtype": "float32",
                "plan": plan.as_dict(),
            },
        )
    except Exception as exc:
        try:
            import cupy as cp
            cp.get_default_memory_pool().free_all_blocks()
            cp.get_default_pinned_memory_pool().free_all_blocks()
        except Exception:
            pass
        message = str(exc)
        code = "GPU_OOM" if "out of memory" in message.lower() else "GPU_COMPUTE_FAILED"
        raise GpuComputeError(f"{code}: {message}") from exc


def compute_alff_falff_gpu(
    data: np.ndarray,
    *,
    tr: float,
    numerator_mask: np.ndarray,
    denominator_mask: np.ndarray,
    plan: GpuStagePlan,
) -> BackendComputeResult:
    shape = data.shape
    flat = np.asarray(data, dtype=np.float32).reshape((-1, shape[3]))

    def operation(cp: Any) -> GpuOperationResult:
        alff = np.empty(flat.shape[0], dtype=np.float32)
        band_sum = np.empty(flat.shape[0], dtype=np.float32)
        denominator_sum = np.empty(flat.shape[0], dtype=np.float32)
        transfer_seconds = 0.0
        compute_seconds = 0.0
        started_at = time.perf_counter()
        num = cp.asarray(numerator_mask)
        den = cp.asarray(denominator_mask)
        cp.cuda.Stream.null.synchronize()
        transfer_seconds += time.perf_counter() - started_at
        for start in range(0, flat.shape[0], plan.chunk_size):
            stop = min(flat.shape[0], start + plan.chunk_size)
            started_at = time.perf_counter()
            block = cp.asarray(flat[start:stop], dtype=cp.float32)
            cp.cuda.Stream.null.synchronize()
            transfer_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            block = block - cp.mean(block, axis=1, keepdims=True)
            amplitude = cp.abs(cp.fft.rfft(block, axis=1)).astype(cp.float32)
            band = amplitude[:, num]
            block_alff = cp.mean(band, axis=1)
            block_band_sum = cp.sum(band, axis=1)
            block_denominator_sum = cp.sum(amplitude[:, den], axis=1)
            cp.cuda.Stream.null.synchronize()
            compute_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            alff[start:stop] = cp.asnumpy(block_alff).astype(np.float32)
            band_sum[start:stop] = cp.asnumpy(block_band_sum).astype(np.float32)
            denominator_sum[start:stop] = cp.asnumpy(block_denominator_sum).astype(np.float32)
            transfer_seconds += time.perf_counter() - started_at
        return GpuOperationResult(
            arrays={
                "raw_alff": alff.reshape(shape[:3]),
                "band_sum": band_sum.reshape(shape[:3]),
                "denominator_sum": denominator_sum.reshape(shape[:3]),
            },
            transfer_seconds=transfer_seconds,
            compute_seconds=compute_seconds,
        )

    return _gpu_result(plan, operation)


def compute_temporal_filter_gpu(
    data: np.ndarray,
    *,
    frequency_mask: np.ndarray,
    plan: GpuStagePlan,
) -> BackendComputeResult:
    shape = data.shape
    flat = np.asarray(data, dtype=np.float32).reshape((-1, shape[3]))

    def operation(cp: Any) -> GpuOperationResult:
        filtered = np.empty_like(flat, dtype=np.float32)
        transfer_seconds = 0.0
        compute_seconds = 0.0
        started_at = time.perf_counter()
        mask = cp.asarray(frequency_mask)
        cp.cuda.Stream.null.synchronize()
        transfer_seconds += time.perf_counter() - started_at
        for start in range(0, flat.shape[0], plan.chunk_size):
            stop = min(flat.shape[0], start + plan.chunk_size)
            started_at = time.perf_counter()
            block = cp.asarray(flat[start:stop], dtype=cp.float32)
            cp.cuda.Stream.null.synchronize()
            transfer_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            spectrum = cp.fft.rfft(block, axis=1)
            spectrum[:, ~mask] = 0.0
            restored = cp.fft.irfft(spectrum, n=shape[3], axis=1)
            cp.cuda.Stream.null.synchronize()
            compute_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            filtered[start:stop] = cp.asnumpy(restored).astype(np.float32)
            transfer_seconds += time.perf_counter() - started_at
        return GpuOperationResult(
            arrays={"filtered": filtered.reshape(shape)},
            transfer_seconds=transfer_seconds,
            compute_seconds=compute_seconds,
        )

    return _gpu_result(plan, operation)


def compute_nuisance_regression_gpu(
    data: np.ndarray,
    design: np.ndarray,
    *,
    plan: GpuStagePlan,
) -> BackendComputeResult:
    shape = data.shape
    flat = np.asarray(data, dtype=np.float32).reshape((-1, shape[3]))
    matrix = np.asarray(design, dtype=np.float64)
    # NumPy's ``rcond=None`` policy is max(M, N) * float64 epsilon.  Pass the
    # value explicitly: CuPy 13 on Python 3.13 otherwise builds it with a
    # NumPy longdouble scalar that cannot multiply a CuPy array.
    rcond = float(max(matrix.shape) * np.finfo(np.float64).eps)

    def operation(cp: Any) -> GpuOperationResult:
        residual = np.empty_like(flat, dtype=np.float32)
        transfer_seconds = 0.0
        compute_seconds = 0.0
        started_at = time.perf_counter()
        x = cp.asarray(matrix, dtype=cp.float64)
        cp.cuda.Stream.null.synchronize()
        transfer_seconds += time.perf_counter() - started_at
        # The rank/pseudoinverse contract is fixed by the CPU-side matrix and
        # explicitly matches numpy's least-squares formulation.
        for start in range(0, flat.shape[0], plan.chunk_size):
            stop = min(flat.shape[0], start + plan.chunk_size)
            started_at = time.perf_counter()
            y = cp.asarray(flat[start:stop].T, dtype=cp.float64)
            cp.cuda.Stream.null.synchronize()
            transfer_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            beta, _, _, _ = cp.linalg.lstsq(x, y, rcond=rcond)
            device_residual = (y - x @ beta).T
            cp.cuda.Stream.null.synchronize()
            compute_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            residual[start:stop] = cp.asnumpy(device_residual).astype(np.float32)
            transfer_seconds += time.perf_counter() - started_at
        return GpuOperationResult(
            arrays={"residual": residual.reshape(shape)},
            transfer_seconds=transfer_seconds,
            compute_seconds=compute_seconds,
        )

    return _gpu_result(plan, operation)


def compute_functional_connectivity_gpu(
    matrix: np.ndarray,
    *,
    plan: GpuStagePlan,
) -> BackendComputeResult:
    values = np.asarray(matrix, dtype=np.float32)
    n_timepoints = values.shape[0]

    def operation(cp: Any) -> GpuOperationResult:
        started_at = time.perf_counter()
        x = cp.asarray(values, dtype=cp.float64)
        cp.cuda.Stream.null.synchronize()
        transfer_seconds = time.perf_counter() - started_at
        started_at = time.perf_counter()
        centered = x - cp.mean(x, axis=0, keepdims=True)
        stds = cp.std(x, axis=0, ddof=1)
        denominator = cp.outer(stds, stds) * float(n_timepoints - 1)
        corr = (centered.T @ centered) / denominator
        corr = cp.where(cp.isfinite(corr), corr, 0.0)
        cp.fill_diagonal(corr, 1.0)
        cp.cuda.Stream.null.synchronize()
        compute_seconds = time.perf_counter() - started_at
        started_at = time.perf_counter()
        constant = cp.asnumpy(stds <= 1e-12)
        transfer_seconds += time.perf_counter() - started_at
        started_at = time.perf_counter()
        if np.any(constant):
            indices = np.flatnonzero(constant)
            corr[indices, :] = 0.0
            corr[:, indices] = 0.0
            corr[indices, indices] = 1.0
        fisher_z = cp.arctanh(cp.clip(corr, -0.999999, 0.999999))
        cp.fill_diagonal(fisher_z, 0.0)
        cp.cuda.Stream.null.synchronize()
        compute_seconds += time.perf_counter() - started_at
        started_at = time.perf_counter()
        correlation = cp.asnumpy(corr).astype(np.float32)
        fisher_z_output = cp.asnumpy(fisher_z).astype(np.float32)
        transfer_seconds += time.perf_counter() - started_at
        return GpuOperationResult(
            arrays={"correlation": correlation, "fisher_z": fisher_z_output},
            transfer_seconds=transfer_seconds,
            compute_seconds=compute_seconds,
        )

    return _gpu_result(plan, operation)


def compute_smoothing_gpu(
    data: np.ndarray,
    *,
    sigma_voxels: tuple[float, float, float],
    plan: GpuStagePlan,
) -> BackendComputeResult:
    """Gaussian smoothing with SciPy-compatible nearest boundary semantics."""
    source = np.asarray(data, dtype=np.float32)
    if source.ndim not in {3, 4}:
        raise ValueError(f"smoothing requires 3D or 4D input, got shape {source.shape}.")

    def operation(cp: Any) -> GpuOperationResult:
        from cupyx.scipy.ndimage import gaussian_filter

        transfer_seconds = 0.0
        compute_seconds = 0.0
        if source.ndim == 3:
            started_at = time.perf_counter()
            values = cp.asarray(source, dtype=cp.float32)
            cp.cuda.Stream.null.synchronize()
            transfer_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            output = gaussian_filter(values, sigma=sigma_voxels, mode="nearest")
            cp.cuda.Stream.null.synchronize()
            compute_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            smoothed = cp.asnumpy(output).astype(np.float32)
            transfer_seconds += time.perf_counter() - started_at
            return GpuOperationResult(
                arrays={"smoothed": smoothed},
                transfer_seconds=transfer_seconds,
                compute_seconds=compute_seconds,
            )
        # Never smooth across time.  The time chunk is derived from the
        # preflight spatial chunk and bounded by the actual time dimension.
        spatial_voxels = max(1, int(np.prod(source.shape[:3])))
        time_chunk = max(1, min(source.shape[3], plan.chunk_size // spatial_voxels))
        output = np.empty_like(source, dtype=np.float32)
        for start in range(0, source.shape[3], time_chunk):
            stop = min(source.shape[3], start + time_chunk)
            started_at = time.perf_counter()
            values = cp.asarray(source[..., start:stop], dtype=cp.float32)
            cp.cuda.Stream.null.synchronize()
            transfer_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            filtered = gaussian_filter(values, sigma=(*sigma_voxels, 0.0), mode="nearest")
            cp.cuda.Stream.null.synchronize()
            compute_seconds += time.perf_counter() - started_at
            started_at = time.perf_counter()
            output[..., start:stop] = cp.asnumpy(filtered).astype(np.float32)
            transfer_seconds += time.perf_counter() - started_at
        return GpuOperationResult(
            arrays={"smoothed": output},
            transfer_seconds=transfer_seconds,
            compute_seconds=compute_seconds,
        )

    return _gpu_result(plan, operation)


def compute_atlas_resampling_gpu(
    data: np.ndarray,
    *,
    matrix: np.ndarray,
    offset: np.ndarray,
    output_shape: tuple[int, int, int],
    plan: GpuStagePlan,
) -> BackendComputeResult:
    """Nearest-neighbour label resampling with the canonical voxel mapping."""
    source = np.asarray(data)
    if source.ndim != 3:
        raise ValueError(f"atlas resampling requires 3D labels, got shape {source.shape}.")

    def operation(cp: Any) -> GpuOperationResult:
        from cupyx.scipy.ndimage import affine_transform

        started_at = time.perf_counter()
        labels = cp.asarray(source, dtype=cp.float32)
        device_matrix = cp.asarray(matrix, dtype=cp.float64)
        device_offset = cp.asarray(offset, dtype=cp.float64)
        cp.cuda.Stream.null.synchronize()
        transfer_seconds = time.perf_counter() - started_at
        started_at = time.perf_counter()
        result = affine_transform(
            labels,
            matrix=device_matrix,
            offset=device_offset,
            output_shape=output_shape,
            order=0,
            mode="constant",
            cval=0.0,
            prefilter=False,
        )
        cp.cuda.Stream.null.synchronize()
        compute_seconds = time.perf_counter() - started_at
        started_at = time.perf_counter()
        resampled = cp.asnumpy(result).astype(np.float32)
        transfer_seconds += time.perf_counter() - started_at
        return GpuOperationResult(
            arrays={"resampled": resampled},
            transfer_seconds=transfer_seconds,
            compute_seconds=compute_seconds,
        )

    return _gpu_result(plan, operation)


__all__ = [
    "BackendComputeResult",
    "GpuOperationResult",
    "GpuComputeError",
    "compute_alff_falff_gpu",
    "compute_functional_connectivity_gpu",
    "compute_nuisance_regression_gpu",
    "compute_smoothing_gpu",
    "compute_atlas_resampling_gpu",
    "compute_temporal_filter_gpu",
]
