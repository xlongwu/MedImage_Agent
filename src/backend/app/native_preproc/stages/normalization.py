"""Native affine-only normalization stage."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.native_preproc.core.affine import (
    affine_is_invertible,
    translation_affine_from_centers,
    world_center_of_mass,
)
from src.backend.app.native_preproc.core.masks import nonzero_fraction
from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.core.resampling import resample_spatial_to_reference
from src.backend.app.native_preproc.io.derivative_naming import derivative_path, nifti_stem
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def estimate_affine_to_template(t1_data: np.ndarray, t1_affine: np.ndarray, template_data: np.ndarray, template_affine: np.ndarray) -> np.ndarray:
    moving_center = world_center_of_mass(t1_data, t1_affine)
    template_center = world_center_of_mass(template_data, template_affine)
    if moving_center is None or template_center is None:
        raise ValueError("Cannot estimate normalization transform from empty T1/template images.")
    return translation_affine_from_centers(moving_center, template_center)


def run_affine_normalization(
    t1w: str | Path,
    bold_4d: str | Path,
    template: str | Path,
    output_dir: str | Path,
    *,
    wm_map: str | Path | None = None,
    csf_map: str | Path | None = None,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "normalization"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "model": "center_of_mass_affine_v1",
        "normalization_scope": "affine_only",
        "template_resource_policy": "caller_supplied_no_bundled_template",
        "interpolation": "linear",
        "tissue_mask_interpolation": "nearest",
    }
    warnings = [
        "affine_only_no_nonlinear_deformation",
        "template_must_be_caller_supplied_and_license_reviewed_before_packaging",
    ]
    errors: list[str] = []

    try:
        t1 = load_nifti(t1w)
        bold = load_nifti(bold_4d)
        template_image = load_nifti(template)
        if t1.data.ndim != 3:
            raise ValueError(f"normalization requires 3D T1w input, got {t1.data.shape}.")
        ensure_4d(bold.data, stage_id=stage_id)
        if template_image.data.ndim != 3:
            raise ValueError(f"normalization requires 3D template input, got {template_image.data.shape}.")

        transform = estimate_affine_to_template(t1.data, t1.affine, template_image.data, template_image.affine)
        normalized = resample_spatial_to_reference(
            bold.data,
            bold.affine,
            template_image.data.shape,
            template_image.affine,
            input_to_reference_affine=transform,
            order=1,
        )

        output_bold = derivative_path(
            context.stage_artifact_dir(stage_id),
            bold.path,
            stage_id=stage_id,
            suffix="affineNormalized_bold",
        )
        transform_path = context.stage_artifact_dir(stage_id) / f"{nifti_stem(t1.path)}_desc-subject_to_template_affine.npy"
        save_nifti(output_bold, normalized, template_image.affine, header=bold.header)
        transform_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(transform_path, transform.astype(np.float32))

        output_refs = [
            build_artifact_ref(
                output_bold,
                artifact_type="normalized_bold",
                metadata={"model": parameters["model"], "template_path": str(template)},
            ),
            build_artifact_ref(
                transform_path,
                artifact_type="transform_matrix",
                metadata={"matrix_shape": [4, 4], "maps": "subject_world_to_template_world"},
            ),
        ]
        resampled_tissue_shapes: dict[str, list[int]] = {}
        for tissue_type, tissue_path in (("wm_map", wm_map), ("csf_map", csf_map)):
            if not tissue_path:
                continue
            tissue = load_nifti(tissue_path)
            if tissue.data.ndim != 3:
                raise ValueError(
                    f"normalization requires a 3D {tissue_type}, got {tissue.data.shape}."
                )
            normalized_tissue = np.clip(
                resample_spatial_to_reference(
                    tissue.data,
                    tissue.affine,
                    template_image.data.shape,
                    template_image.affine,
                    input_to_reference_affine=transform,
                    order=0,
                ),
                0.0,
                1.0,
            ).astype(np.float32, copy=False)
            tissue_name = tissue_type.removesuffix("_map")
            tissue_output = (
                context.stage_artifact_dir(stage_id)
                / f"{tissue_name}_desc-affineNormalized_probseg.nii.gz"
            )
            save_nifti(
                tissue_output,
                normalized_tissue,
                template_image.affine,
                header=tissue.header,
            )
            output_refs.append(
                build_artifact_ref(
                    tissue_output,
                    artifact_type=tissue_type,
                    metadata={
                        "model": parameters["model"],
                        "reference_grid": "template",
                        "interpolation": parameters["tissue_mask_interpolation"],
                    },
                )
            )
            resampled_tissue_shapes[tissue_type] = [
                int(value) for value in normalized_tissue.shape
            ]
        qc = NativePreprocQC(
            status="warning",
            metrics={
                "model": parameters["model"],
                "input_bold_shape": [int(value) for value in bold.data.shape],
                "output_bold_shape": [int(value) for value in normalized.shape],
                "template_shape": [int(value) for value in template_image.data.shape],
                "template_nonzero_fraction": nonzero_fraction(template_image.data),
                "normalized_nonzero_fraction": nonzero_fraction(normalized),
                "translation_mm": [float(value) for value in transform[:3, 3]],
                "transform_invertible": affine_is_invertible(transform),
                "output_stats": finite_stats(normalized),
                "resampled_tissue_shapes": resampled_tissue_shapes,
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, "template_path": str(template)},
            status="simplified",
            capability_level="affine_only",
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
            parameters={**parameters, "template_path": str(template)},
            status="blocked",
            capability_level="affine_only",
            qc=qc,
            warnings=warnings,
            errors=errors,
        )
