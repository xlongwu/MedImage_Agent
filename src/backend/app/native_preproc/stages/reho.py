"""Native ReHo stage using tie-corrected Kendall W on CPU."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC
from src.backend.app.tools.reho_compute import compute_reho_numpy


def run_reho(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    neighborhood: int = 27,
    mask: str | Path | None = None,
    mask_threshold: float = 0.5,
    smoothing_policy: str = "not_applied_in_stage",
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "reho"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters: dict[str, Any] = {
        "neighborhood": int(neighborhood),
        "mask": str(mask) if mask else None,
        "mask_threshold": float(mask_threshold),
        "kendall_w_ties_handling": "average_ranks_with_tie_correction",
        "smoothing_policy": smoothing_policy,
        "implementation_note": "native_stage_uses_existing_tie_corrected_cpu_kernel_as_canonical_formula",
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        if neighborhood not in {7, 19, 27}:
            raise ValueError("ReHo neighborhood must be one of 7, 19, or 27.")
        image = load_nifti(input_bold)
        ensure_4d(image.data, stage_id=stage_id)
        if not np.isfinite(image.data).all():
            raise ValueError("input BOLD contains NaN or infinite values.")
        mask_data = None
        mask_voxel_count = None
        if mask:
            loaded_mask = load_nifti(mask).data
            if loaded_mask.shape != image.data.shape[:3]:
                raise ValueError(f"mask shape {loaded_mask.shape} does not match BOLD spatial shape {image.data.shape[:3]}.")
            mask_data = np.isfinite(loaded_mask) & (loaded_mask > float(mask_threshold))
            mask_voxel_count = int(np.count_nonzero(mask_data))
            if mask_voxel_count == 0:
                raise ValueError("mask contains no selected voxels.")

        compute = compute_reho_numpy(image.data, neighborhood=neighborhood, gm_mask=mask_data)
        warnings.extend(str(item) for item in compute.get("warnings", []))
        if not compute.get("ok"):
            errors.extend(str(item) for item in compute.get("errors", []))
            if not errors:
                errors.append("ReHo computation produced no valid voxels.")
            raise ValueError("; ".join(errors))
        reho_map = np.asarray(compute["reho"], dtype=np.float32)
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="reho_map",
        )
        save_nifti(output_path, reho_map, image.affine, header=image.header)
        metadata = {
            "neighborhood": int(neighborhood),
            "valid_voxel_count": int(compute.get("valid_voxel_count", 0)),
            "skipped_voxel_count": int(compute.get("skipped_voxel_count", 0)),
            "kendall_w_ties_handling": "average_ranks_with_tie_correction",
            "smoothing_policy": smoothing_policy,
        }
        output_ref = build_artifact_ref(output_path, artifact_type="reho_map", metadata=metadata)
        qc = NativePreprocQC(
            status="warning" if warnings else "pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in reho_map.shape],
                "mask_voxel_count": mask_voxel_count,
                "output_stats": finite_stats(reho_map),
                **metadata,
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters=parameters,
            status="warning" if warnings else "succeeded",
            capability_level="numerically_implemented",
            qc=qc,
            output_artifacts=[output_ref],
            warnings=warnings,
            errors=[],
        )
    except Exception as exc:
        if not errors:
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
