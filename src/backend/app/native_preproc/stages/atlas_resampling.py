"""Native atlas resampling stage."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.core.compute_backend import (
    GpuComputeError,
    compute_atlas_resampling_gpu,
    cpu_compute_provenance,
)
from src.backend.app.native_preproc.core.resampling import _output_to_input_voxel_mapping, resample_spatial_to_reference
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.orchestrator.gpu_resource_planner import plan_gpu_stage
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC
from src.backend.app.schemas.native_preproc_api import NativeComputePolicy


def resample_atlas_with_backend(
    atlas_data: np.ndarray,
    atlas_affine: np.ndarray,
    reference_shape: tuple[int, int, int],
    reference_affine: np.ndarray,
    *,
    reference_transform: np.ndarray | None = None,
    compute_policy: NativeComputePolicy | None = None,
) -> tuple[np.ndarray, dict[str, object]]:
    policy = compute_policy or NativeComputePolicy()
    plan = plan_gpu_stage("atlas_resampling", input_shape=tuple(int(item) for item in atlas_data.shape), policy=policy)
    if plan.selected_backend == "blocked":
        raise ValueError("; ".join(plan.blocking_issues))
    if plan.selected_backend == "gpu":
        matrix, offset = _output_to_input_voxel_mapping(
            atlas_affine, reference_affine, reference_transform
        )
        try:
            gpu = compute_atlas_resampling_gpu(
                atlas_data, matrix=matrix, offset=offset, output_shape=reference_shape, plan=plan
            )
        except GpuComputeError as exc:
            if not plan.fallback_allowed:
                raise ValueError(str(exc)) from exc
            started_at = perf_counter()
            output = resample_spatial_to_reference(
                atlas_data, atlas_affine, reference_shape, reference_affine,
                input_to_reference_affine=reference_transform, order=0, output_dtype=np.int16,
            )
            return output, cpu_compute_provenance(plan, started_at=started_at, fallback_reason=str(exc))
        return gpu.arrays["resampled"], gpu.provenance()
    started_at = perf_counter()
    output = resample_spatial_to_reference(
        atlas_data, atlas_affine, reference_shape, reference_affine,
        input_to_reference_affine=reference_transform, order=0, output_dtype=np.int16,
    )
    return output, cpu_compute_provenance(
        plan,
        started_at=started_at,
        fallback_reason=",".join(plan.limiting_factors)
        if plan.requested_backend == "auto" and plan.limiting_factors
        else None,
    )


def run_atlas_resampling(
    atlas: str | Path,
    reference_image: str | Path,
    output_dir: str | Path,
    *,
    reference_transform: np.ndarray | None = None,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
    compute_policy: NativeComputePolicy | None = None,
):
    stage_id = "atlas_resampling"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "interpolation": "nearest_neighbor",
        "reference_transform": "provided" if reference_transform is not None else "identity",
        "atlas_resource_policy": "caller_supplied_no_bundled_atlas",
    }
    warnings = ["atlas_must_be_caller_supplied_and_license_reviewed_before_packaging"]
    errors: list[str] = []

    try:
        atlas_image = load_nifti(atlas)
        reference = load_nifti(reference_image)
        if atlas_image.data.ndim != 3:
            raise ValueError(f"atlas_resampling requires 3D atlas input, got {atlas_image.data.shape}.")
        reference_shape = reference.data.shape[:3]
        resampled, compute_provenance = resample_atlas_with_backend(
            atlas_image.data,
            atlas_image.affine,
            reference_shape,
            reference.affine,
            reference_transform=reference_transform,
            compute_policy=compute_policy,
        )
        if compute_provenance.get("fallback_reason"):
            warnings.append(f"gpu_fallback:{compute_provenance['fallback_reason']}")
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            atlas_image.path,
            stage_id=stage_id,
            suffix="resampled_atlas",
        )
        rounded = np.rint(resampled).astype(np.int16)
        save_nifti(output_path, rounded, reference.affine, header=atlas_image.header, dtype=np.int16)

        input_labels = sorted(float(value) for value in np.unique(atlas_image.data))
        output_labels = sorted(float(value) for value in np.unique(rounded))
        fractional_voxels = int(np.count_nonzero(np.abs(rounded.astype(np.float32) - resampled.astype(np.float32)) > 1e-6))
        output_ref = build_artifact_ref(
            output_path,
            artifact_type="atlas_resampled",
            metadata={
                "interpolation": "nearest_neighbor",
                "input_labels": input_labels,
                "output_labels": output_labels,
            },
        )
        qc = NativePreprocQC(
            status="warning",
            metrics={
                "input_shape": [int(value) for value in atlas_image.data.shape],
                "reference_shape": [int(value) for value in reference_shape],
                "output_shape": [int(value) for value in rounded.shape],
                "input_labels": input_labels,
                "output_labels": output_labels,
                "fractional_label_voxels": fractional_voxels,
                "output_stats": finite_stats(rounded),
                "compute": compute_provenance,
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, "compute": compute_provenance},
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
        qc = NativePreprocQC(status="fail", warnings=warnings, errors=errors)
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
