"""Native spatial smoothing stage."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np

from src.backend.app.native_preproc.core.affine import fwhm_mm_to_sigma_voxels
from src.backend.app.native_preproc.core.compute_backend import (
    GpuComputeError,
    compute_smoothing_gpu,
    cpu_compute_provenance,
)
from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.orchestrator.gpu_resource_planner import plan_gpu_stage
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC
from src.backend.app.schemas.native_preproc_api import NativeComputePolicy


def smooth_spatial(data: np.ndarray, sigma_voxels: Sequence[float]) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    source = np.asarray(data, dtype=np.float32)
    if source.ndim == 4:
        sigma = tuple(float(value) for value in sigma_voxels) + (0.0,)
    elif source.ndim == 3:
        sigma = tuple(float(value) for value in sigma_voxels)
    else:
        raise ValueError(f"smoothing requires 3D or 4D input, got shape {source.shape}.")
    return gaussian_filter(source, sigma=sigma, mode="nearest").astype(np.float32)


def smooth_spatial_with_backend(
    data: np.ndarray,
    sigma_voxels: Sequence[float],
    *,
    compute_policy: NativeComputePolicy | None = None,
) -> tuple[np.ndarray, dict[str, object]]:
    source = np.asarray(data, dtype=np.float32)
    policy = compute_policy or NativeComputePolicy()
    plan = plan_gpu_stage("smoothing", input_shape=tuple(int(item) for item in source.shape), policy=policy)
    if plan.selected_backend == "blocked":
        raise ValueError("; ".join(plan.blocking_issues))
    if plan.selected_backend == "gpu":
        try:
            gpu = compute_smoothing_gpu(source, sigma_voxels=tuple(float(item) for item in sigma_voxels), plan=plan)
        except GpuComputeError as exc:
            if not plan.fallback_allowed:
                raise ValueError(str(exc)) from exc
            started_at = perf_counter()
            return smooth_spatial(source, sigma_voxels), cpu_compute_provenance(
                plan, started_at=started_at, fallback_reason=str(exc)
            )
        return gpu.arrays["smoothed"], gpu.provenance()
    started_at = perf_counter()
    return smooth_spatial(source, sigma_voxels), cpu_compute_provenance(
        plan,
        started_at=started_at,
        fallback_reason=",".join(plan.limiting_factors)
        if plan.requested_backend == "auto" and plan.limiting_factors
        else None,
    )


def run_smoothing(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    fwhm_mm: float | Sequence[float] = 6.0,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
    compute_policy: NativeComputePolicy | None = None,
):
    stage_id = "smoothing"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {"fwhm_mm": list(fwhm_mm) if not isinstance(fwhm_mm, (int, float)) else float(fwhm_mm)}
    warnings: list[str] = []
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        sigma = fwhm_mm_to_sigma_voxels(fwhm_mm, image.affine)
        smoothed, compute_provenance = smooth_spatial_with_backend(
            image.data, sigma, compute_policy=compute_policy
        )
        if compute_provenance.get("fallback_reason"):
            warnings.append(f"gpu_fallback:{compute_provenance['fallback_reason']}")
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="smoothed_bold",
        )
        save_nifti(output_path, smoothed, image.affine, header=image.header)
        output_ref = build_artifact_ref(
            output_path,
            artifact_type="smoothed_bold",
            metadata={
                "fwhm_mm": parameters["fwhm_mm"],
                "sigma_voxels": [float(value) for value in sigma],
                "spatial_only": True,
            },
        )
        qc = NativePreprocQC(
            status="pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in smoothed.shape],
                "timepoints_preserved": bool(image.data.ndim != 4 or image.data.shape[3] == smoothed.shape[3]),
                "sigma_voxels": [float(value) for value in sigma],
                "output_stats": finite_stats(smoothed),
                "compute": compute_provenance,
            },
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, "sigma_voxels": [float(value) for value in sigma], "compute": compute_provenance},
            status="succeeded",
            capability_level="numerically_implemented",
            qc=qc,
            output_artifacts=[output_ref],
            warnings=warnings,
            errors=errors,
            backend="gpu" if compute_provenance.get("actual_backend") == "gpu-cupy" else "native_python",
        )
    except Exception as exc:
        errors.append(str(exc))
        qc = NativePreprocQC(status="fail", errors=errors)
        return stage_result(
            context,
            stage_id=stage_id,
            parameters=parameters,
            status="blocked",
            capability_level="numerically_implemented",
            qc=qc,
            warnings=warnings,
            errors=errors,
        )
