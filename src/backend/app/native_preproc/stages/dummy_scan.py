"""Native dummy-scan removal stage."""
from __future__ import annotations

from pathlib import Path

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def run_dummy_scan_removal(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    remove_first: int,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "dummy_scan_removal"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {"remove_first": int(remove_first)}
    warnings: list[str] = []
    errors: list[str] = []

    try:
        if remove_first < 0:
            raise ValueError("remove_first must be non-negative.")
        image = load_nifti(input_bold)
        ensure_4d(image.data, stage_id=stage_id)
        timepoints = int(image.data.shape[3])
        if remove_first >= timepoints:
            raise ValueError("remove_first must be smaller than the number of timepoints.")
        output_data = image.data[..., remove_first:].astype("float32", copy=False)
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="dummyRemoved_bold",
        )
        save_nifti(output_path, output_data, image.affine, header=image.header)
        output_ref = build_artifact_ref(
            output_path,
            artifact_type="bold_4d",
            metadata={
                "removed_timepoints": remove_first,
                "retained_timepoints": int(output_data.shape[3]),
                "input_timepoints": timepoints,
            },
        )
        qc = NativePreprocQC(
            status="pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in output_data.shape],
                "removed_timepoints": remove_first,
                "output_stats": finite_stats(output_data),
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
