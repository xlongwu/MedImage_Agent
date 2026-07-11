"""Native explicit detrending stage."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.dpabi_compat.regressors import polynomial_trends
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def detrend_4d(data_4d: np.ndarray, *, polynomial_order: int = 1, include_intercept: bool = True) -> np.ndarray:
    data = np.asarray(data_4d, dtype=np.float32)
    ensure_4d(data, stage_id="detrending")
    n_timepoints = int(data.shape[3])
    if polynomial_order < 0:
        raise ValueError("polynomial_order must be non-negative.")
    if n_timepoints <= polynomial_order + 1:
        raise ValueError("insufficient timepoints for requested polynomial trend order.")
    design = polynomial_trends(n_timepoints, order=polynomial_order, include_intercept=include_intercept).values
    flat = data.reshape((-1, n_timepoints))
    if not np.isfinite(flat).all():
        raise ValueError("input BOLD contains NaN or infinite values.")
    beta = np.linalg.lstsq(design.astype(np.float64), flat.T.astype(np.float64), rcond=None)[0]
    trend = design.astype(np.float64) @ beta
    return (flat.astype(np.float64) - trend.T).reshape(data.shape).astype(np.float32)


def run_detrending(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    polynomial_order: int = 1,
    include_intercept: bool = True,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "detrending"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "trend_model": "polynomial",
        "polynomial_order": int(polynomial_order),
        "include_intercept": include_intercept,
        "fit_space": "voxelwise_time_axis",
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        detrended = detrend_4d(image.data, polynomial_order=polynomial_order, include_intercept=include_intercept)
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="detrended_bold",
        )
        save_nifti(output_path, detrended, image.affine, header=image.header)
        output_ref = build_artifact_ref(
            output_path,
            artifact_type="detrended_bold",
            metadata={"trend_model": "polynomial", "polynomial_order": int(polynomial_order)},
        )
        qc = NativePreprocQC(
            status="pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in detrended.shape],
                "trend_model": "polynomial",
                "polynomial_order": int(polynomial_order),
                "timepoints_preserved": bool(detrended.shape[3] == image.data.shape[3]),
                "output_stats": finite_stats(detrended),
            },
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters=parameters,
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
