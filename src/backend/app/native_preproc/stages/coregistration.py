"""Native coregistration stage.

Phase 03 implements a truthful translation-only affine baseline. It estimates a
world-space center-of-mass transform from T1w to mean functional space and
reports normalized mutual information before and after resampling.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.native_preproc.core.affine import (
    affine_is_invertible,
    translation_affine_from_centers,
    world_center_of_mass,
)
from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.core.resampling import resample_spatial_to_reference
from src.backend.app.native_preproc.io.derivative_naming import derivative_path, nifti_stem
from src.backend.app.native_preproc.io.nifti_io import load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def normalized_mutual_information(reference: np.ndarray, moving: np.ndarray, *, bins: int = 64) -> float:
    ref = np.asarray(reference, dtype=np.float32).ravel()
    mov = np.asarray(moving, dtype=np.float32).ravel()
    finite = np.isfinite(ref) & np.isfinite(mov)
    if np.count_nonzero(finite) < 2:
        return 0.0
    ref = ref[finite]
    mov = mov[finite]
    hist_2d, _, _ = np.histogram2d(ref, mov, bins=int(bins))
    total = float(np.sum(hist_2d))
    if total <= 0:
        return 0.0
    pxy = hist_2d / total
    px = np.sum(pxy, axis=1)
    py = np.sum(pxy, axis=0)

    def _entropy(probabilities: np.ndarray) -> float:
        values = probabilities[probabilities > 0]
        return float(-np.sum(values * np.log(values)))

    joint_entropy = _entropy(pxy)
    if joint_entropy <= 0:
        return 0.0
    return float((_entropy(px) + _entropy(py)) / joint_entropy)


def run_coregistration(
    mean_functional: str | Path,
    t1w: str | Path,
    output_dir: str | Path,
    *,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "coregistration"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "model": "translation_only_affine_v1",
        "cost_function": "normalized_mutual_information",
        "interpolation": "linear",
    }
    warnings = ["translation_only_affine_v1_not_spm_coregister_equivalent"]
    errors: list[str] = []

    try:
        reference = load_nifti(mean_functional)
        moving = load_nifti(t1w)
        if reference.data.ndim != 3:
            raise ValueError(f"coregistration requires 3D mean functional input, got {reference.data.shape}.")
        if moving.data.ndim != 3:
            raise ValueError(f"coregistration requires 3D T1w input, got {moving.data.shape}.")

        reference_center = world_center_of_mass(reference.data, reference.affine)
        moving_center = world_center_of_mass(moving.data, moving.affine)
        if reference_center is None or moving_center is None:
            raise ValueError("Cannot estimate coregistration center of mass from empty images.")

        transform = translation_affine_from_centers(moving_center, reference_center)
        before = resample_spatial_to_reference(
            moving.data,
            moving.affine,
            reference.data.shape,
            reference.affine,
            order=1,
        )
        coregistered = resample_spatial_to_reference(
            moving.data,
            moving.affine,
            reference.data.shape,
            reference.affine,
            input_to_reference_affine=transform,
            order=1,
        )
        nmi_before = normalized_mutual_information(reference.data, before)
        nmi_after = normalized_mutual_information(reference.data, coregistered)
        if nmi_after + 1e-6 < nmi_before:
            warnings.append("normalized_mutual_information_not_improved")

        output_t1 = derivative_path(
            context.stage_artifact_dir(stage_id),
            moving.path,
            stage_id=stage_id,
            suffix="coregistered_t1w",
        )
        transform_path = context.stage_artifact_dir(stage_id) / f"{nifti_stem(moving.path)}_desc-t1w_to_mean_transform.npy"
        save_nifti(output_t1, coregistered, reference.affine, header=moving.header)
        transform_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(transform_path, transform.astype(np.float32))

        output_refs = [
            build_artifact_ref(
                output_t1,
                artifact_type="t1w",
                metadata={"role": "coregistered_t1w", "reference_grid": "mean_functional"},
            ),
            build_artifact_ref(
                transform_path,
                artifact_type="transform_matrix",
                metadata={"matrix_shape": [4, 4], "maps": "t1w_world_to_mean_functional_world"},
            ),
        ]
        qc = NativePreprocQC(
            status="warning" if warnings else "pass",
            metrics={
                "model": parameters["model"],
                "cost_function": parameters["cost_function"],
                "nmi_before": float(nmi_before),
                "nmi_after": float(nmi_after),
                "nmi_delta": float(nmi_after - nmi_before),
                "translation_mm": [float(value) for value in transform[:3, 3]],
                "transform_invertible": affine_is_invertible(transform),
                "output_stats": finite_stats(coregistered),
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters=parameters,
            status="simplified",
            capability_level="simplified",
            qc=qc,
            output_artifacts=output_refs,
            warnings=warnings,
            errors=errors,
        )
    except Exception as exc:
        errors.append(str(exc))
        qc = NativePreprocQC(status="fail", warnings=warnings, errors=errors)
        return stage_result(
            context,
            stage_id=stage_id,
            parameters=parameters,
            status="blocked",
            capability_level="simplified",
            qc=qc,
            warnings=warnings,
            errors=errors,
        )
