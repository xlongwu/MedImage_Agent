"""Native slice-timing correction stage."""
from __future__ import annotations

from pathlib import Path

from src.backend.app.native_preproc.core.interpolation import slice_timing_correct_4d
from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.io.sidecar import read_bids_metadata, require_repetition_time, require_slice_timing
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def run_slice_timing_correction(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    sidecar_path: str | Path | None = None,
    reference_time: float | None = None,
    reference_slice_index: int | None = None,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "slice_timing"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "sidecar_path": str(sidecar_path) if sidecar_path else "",
        "reference_time": reference_time,
        "reference_slice_index": reference_slice_index,
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        ensure_4d(image.data, stage_id=stage_id)
        metadata = read_bids_metadata(input_bold, sidecar_path)
        tr = require_repetition_time(metadata)
        slice_timing = require_slice_timing(metadata, nslices=int(image.data.shape[2]))
        if reference_time is None:
            if reference_slice_index is not None:
                if reference_slice_index < 0 or reference_slice_index >= len(slice_timing):
                    raise ValueError("reference_slice_index is out of bounds.")
                reference_time = float(slice_timing[reference_slice_index])
            else:
                reference_time = float(slice_timing[len(slice_timing) // 2])
        corrected = slice_timing_correct_4d(
            image.data,
            tr=tr,
            slice_timing=slice_timing,
            reference_time=float(reference_time),
        )
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="sliceTiming_bold",
        )
        save_nifti(output_path, corrected, image.affine, header=image.header)
        output_ref = build_artifact_ref(
            output_path,
            artifact_type="bold_4d",
            metadata={
                "tr": tr,
                "slice_timing": slice_timing,
                "reference_time": float(reference_time),
                "sidecar_path": metadata.get("_sidecar_path", ""),
            },
        )
        qc = NativePreprocQC(
            status="pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in corrected.shape],
                "tr": tr,
                "slice_count": int(image.data.shape[2]),
                "reference_time": float(reference_time),
                "output_stats": finite_stats(corrected),
            },
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, "tr": tr, "slice_timing": slice_timing, "reference_time": float(reference_time)},
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
