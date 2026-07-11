"""Native realignment stage.

Phase 02 implements a truthful translation-only V1 baseline. It writes motion
parameters and transform matrices, but it does not claim SPM-equivalent 6DOF
rigid-body optimization.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.native_preproc.core.affine import voxel_sizes_from_affine
from src.backend.app.native_preproc.core.optimizer import estimate_translation_to_reference
from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.core.resampling import apply_volume_shifts
from src.backend.app.native_preproc.core.transforms import (
    motion_row_from_translation,
    translation_matrix_mm,
    voxel_shift_to_mm,
)
from src.backend.app.native_preproc.io.derivative_naming import derivative_path, nifti_stem
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def _write_motion_tsv(path: Path, rows: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "trans_x_mm\ttrans_y_mm\ttrans_z_mm\trot_x_rad\trot_y_rad\trot_z_rad"
    lines = [header]
    lines.extend("\t".join(f"{value:.8f}" for value in row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_realignment(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    reference_volume_index: int = 0,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "realignment"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "reference_volume_index": int(reference_volume_index),
        "model": "translation_only_v1",
        "interpolation": "linear",
    }
    warnings = ["translation_only_v1_no_rotation_estimation"]
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        ensure_4d(image.data, stage_id=stage_id)
        timepoints = int(image.data.shape[3])
        if reference_volume_index < 0 or reference_volume_index >= timepoints:
            raise ValueError("reference_volume_index is out of bounds.")
        reference = image.data[..., reference_volume_index]
        voxel_sizes = voxel_sizes_from_affine(image.affine)
        shifts_voxels = np.zeros((timepoints, 3), dtype=np.float32)
        motion_rows: list[list[float]] = []
        matrices = np.zeros((timepoints, 4, 4), dtype=np.float32)
        per_volume_warnings: list[str] = []

        for index in range(timepoints):
            shift_voxels, shift_warnings = estimate_translation_to_reference(image.data[..., index], reference)
            shifts_voxels[index] = shift_voxels
            translation_mm = voxel_shift_to_mm(shift_voxels, voxel_sizes)
            motion_rows.append(motion_row_from_translation(translation_mm))
            matrices[index] = translation_matrix_mm(translation_mm)
            per_volume_warnings.extend([f"volume_{index}:{warning}" for warning in shift_warnings])

        warnings.extend(per_volume_warnings)
        aligned = apply_volume_shifts(image.data, shifts_voxels, order=1)
        mean_functional = np.mean(aligned, axis=3).astype(np.float32)

        output_bold = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="realigned_bold",
        )
        mean_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="meanFunctional_bold",
        )
        motion_path = context.stage_artifact_dir(stage_id) / f"{nifti_stem(image.path)}_desc-motion_parameters.tsv"
        transforms_path = context.stage_artifact_dir(stage_id) / f"{nifti_stem(image.path)}_desc-transforms_matrices.npy"

        save_nifti(output_bold, aligned, image.affine, header=image.header)
        save_nifti(mean_path, mean_functional, image.affine, header=image.header)
        _write_motion_tsv(motion_path, motion_rows)
        transforms_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(transforms_path, matrices)

        output_refs = [
            build_artifact_ref(output_bold, artifact_type="bold_4d", metadata={"model": "translation_only_v1"}),
            build_artifact_ref(mean_path, artifact_type="mean_functional", metadata={"source": "mean_of_realigned_bold"}),
            build_artifact_ref(
                motion_path,
                artifact_type="motion_parameters",
                metadata={"rows": timepoints, "columns": 6, "units": ["mm", "mm", "mm", "rad", "rad", "rad"]},
            ),
            build_artifact_ref(
                transforms_path,
                artifact_type="transform_matrix",
                metadata={"matrix_count": timepoints, "matrix_shape": [4, 4], "model": "translation_only_v1"},
            ),
        ]
        max_translation = max(float(np.linalg.norm(row[:3])) for row in motion_rows) if motion_rows else 0.0
        qc = NativePreprocQC(
            status="warning",
            metrics={
                "model": "translation_only_v1",
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in aligned.shape],
                "timepoints": timepoints,
                "transform_matrix_count": int(matrices.shape[0]),
                "max_translation_mm": max_translation,
                "output_stats": finite_stats(aligned),
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
