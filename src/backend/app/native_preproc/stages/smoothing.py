"""Native spatial smoothing stage."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from src.backend.app.native_preproc.core.affine import fwhm_mm_to_sigma_voxels
from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


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


def run_smoothing(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    fwhm_mm: float | Sequence[float] = 6.0,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "smoothing"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {"fwhm_mm": list(fwhm_mm) if not isinstance(fwhm_mm, (int, float)) else float(fwhm_mm)}
    warnings: list[str] = []
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        sigma = fwhm_mm_to_sigma_voxels(fwhm_mm, image.affine)
        smoothed = smooth_spatial(image.data, sigma)
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
            },
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, "sigma_voxels": [float(value) for value in sigma]},
            status="succeeded",
            capability_level="numerically_implemented",
            qc=qc,
            output_artifacts=[output_ref],
            warnings=warnings,
            errors=errors,
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
