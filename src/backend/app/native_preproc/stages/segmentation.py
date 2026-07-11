"""Native simplified tissue segmentation stage."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.native_preproc.core.masks import intensity_brain_mask, tissue_probabilities_from_intensity
from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def run_segmentation(
    t1w: str | Path,
    output_dir: str | Path,
    *,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "segmentation"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "model": "intensity_kmeans_v1",
        "classes": ["csf", "gm", "wm"],
        "brain_mask": "positive_intensity_threshold",
    }
    warnings = ["simplified_intensity_kmeans_not_spm_unified_segmentation"]
    errors: list[str] = []

    try:
        image = load_nifti(t1w)
        if image.data.ndim != 3:
            raise ValueError(f"segmentation requires 3D T1w input, got {image.data.shape}.")
        brain_mask = intensity_brain_mask(image.data)
        if int(np.count_nonzero(brain_mask)) == 0:
            raise ValueError("segmentation brain mask is empty.")
        csf, gm, wm, centers = tissue_probabilities_from_intensity(image.data, brain_mask)

        stage_dir = context.stage_artifact_dir(stage_id)
        mask_path = derivative_path(stage_dir, image.path, stage_id=stage_id, suffix="brainMask", extension=".nii.gz")
        csf_path = derivative_path(stage_dir, image.path, stage_id=stage_id, suffix="csfProb", extension=".nii.gz")
        gm_path = derivative_path(stage_dir, image.path, stage_id=stage_id, suffix="gmProb", extension=".nii.gz")
        wm_path = derivative_path(stage_dir, image.path, stage_id=stage_id, suffix="wmProb", extension=".nii.gz")
        save_nifti(mask_path, brain_mask.astype(np.float32), image.affine, header=image.header)
        save_nifti(csf_path, csf, image.affine, header=image.header)
        save_nifti(gm_path, gm, image.affine, header=image.header)
        save_nifti(wm_path, wm, image.affine, header=image.header)

        brain_voxels = int(np.count_nonzero(brain_mask))
        output_refs = [
            build_artifact_ref(mask_path, artifact_type="brain_mask", metadata={"threshold_model": "positive_intensity"}),
            build_artifact_ref(csf_path, artifact_type="csf_map", metadata={"model": parameters["model"]}),
            build_artifact_ref(gm_path, artifact_type="gm_map", metadata={"model": parameters["model"]}),
            build_artifact_ref(wm_path, artifact_type="wm_map", metadata={"model": parameters["model"]}),
        ]
        qc = NativePreprocQC(
            status="warning",
            metrics={
                "model": parameters["model"],
                "input_shape": [int(value) for value in image.data.shape],
                "brain_voxels": brain_voxels,
                "brain_fraction": float(brain_voxels / image.data.size),
                "class_centers": centers,
                "csf_probability_range": [float(np.min(csf)), float(np.max(csf))],
                "gm_probability_range": [float(np.min(gm)), float(np.max(gm))],
                "wm_probability_range": [float(np.min(wm)), float(np.max(wm))],
                "csf_volume_voxels": float(np.sum(csf)),
                "gm_volume_voxels": float(np.sum(gm)),
                "wm_volume_voxels": float(np.sum(wm)),
                "input_stats": finite_stats(image.data),
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
