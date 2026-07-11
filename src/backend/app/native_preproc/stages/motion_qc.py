"""Native motion QC stage."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.native_preproc.io.derivative_naming import nifti_stem
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def load_motion_parameters(path: str | Path) -> np.ndarray:
    rows: list[list[float]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parts = line.replace(",", "\t").split()
        try:
            values = [float(value) for value in parts[:6]]
        except ValueError:
            continue
        if len(values) < 6:
            raise ValueError(f"Motion parameter row has fewer than 6 values: {line}")
        rows.append(values)
    if not rows:
        raise ValueError("Motion parameter file is empty or has no numeric rows.")
    return np.asarray(rows, dtype=np.float32)


def compute_framewise_displacement(motion_parameters: np.ndarray, *, head_radius_mm: float = 50.0) -> np.ndarray:
    params = np.asarray(motion_parameters, dtype=np.float32)
    if params.ndim != 2 or params.shape[1] < 6:
        raise ValueError("motion_parameters must have shape (timepoints, 6).")
    diffs = np.zeros_like(params[:, :6], dtype=np.float32)
    diffs[1:] = np.diff(params[:, :6], axis=0)
    trans = np.sum(np.abs(diffs[:, :3]), axis=1)
    rot = np.sum(np.abs(diffs[:, 3:6]), axis=1) * float(head_radius_mm)
    return (trans + rot).astype(np.float32)


def compute_friston_24(motion_parameters: np.ndarray) -> np.ndarray:
    params = np.asarray(motion_parameters[:, :6], dtype=np.float32)
    previous = np.vstack([np.zeros((1, 6), dtype=np.float32), params[:-1]])
    return np.hstack([params, previous, params**2, previous**2]).astype(np.float32)


def _write_tsv(path: Path, header: list[str], rows: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(header)]
    for row in rows:
        lines.append("\t".join(f"{float(value):.8f}" for value in row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_motion_qc(
    motion_parameters: str | Path,
    output_dir: str | Path,
    *,
    fd_threshold_mm: float = 0.5,
    head_radius_mm: float = 50.0,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "motion_qc"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {"fd_threshold_mm": float(fd_threshold_mm), "head_radius_mm": float(head_radius_mm)}
    warnings: list[str] = []
    errors: list[str] = []

    try:
        params = load_motion_parameters(motion_parameters)
        fd = compute_framewise_displacement(params, head_radius_mm=head_radius_mm)
        friston = compute_friston_24(params)
        high_motion = fd > float(fd_threshold_mm)
        stage_dir = context.stage_artifact_dir(stage_id)
        stem = nifti_stem(motion_parameters)
        fd_path = stage_dir / f"{stem}_desc-framewise_displacement.tsv"
        friston_path = stage_dir / f"{stem}_desc-friston24_regressors.tsv"
        qc_md_path = context.qc_markdown_path(stage_id)

        _write_tsv(fd_path, ["framewise_displacement"], fd.reshape((-1, 1)))
        _write_tsv(
            friston_path,
            [f"motion_{idx + 1:02d}" for idx in range(6)]
            + [f"motion_prev_{idx + 1:02d}" for idx in range(6)]
            + [f"motion_sq_{idx + 1:02d}" for idx in range(6)]
            + [f"motion_prev_sq_{idx + 1:02d}" for idx in range(6)],
            friston,
        )
        lines = [
            "# Native Motion QC",
            "",
            f"- Frames: {params.shape[0]}",
            f"- Mean FD: {float(np.mean(fd)):.6f}",
            f"- Max FD: {float(np.max(fd)):.6f}",
            f"- FD threshold: {fd_threshold_mm}",
            f"- High-motion frames: {int(np.count_nonzero(high_motion))}",
        ]
        qc_md_path.parent.mkdir(parents=True, exist_ok=True)
        qc_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        if np.any(high_motion):
            warnings.append("fd_threshold_exceeded")
        status = "warning" if warnings else "succeeded"
        qc_status = "warning" if warnings else "pass"
        output_refs = [
            build_artifact_ref(
                fd_path,
                artifact_type="fd_timeseries",
                metadata={"rows": int(fd.shape[0]), "first_frame_strategy": "zero", "units": "mm"},
            ),
            build_artifact_ref(
                friston_path,
                artifact_type="motion_parameters",
                metadata={"rows": int(friston.shape[0]), "columns": int(friston.shape[1]), "model": "Friston24"},
            ),
            build_artifact_ref(qc_md_path, artifact_type="qc_md", metadata={"format": "markdown"}),
        ]
        qc = NativePreprocQC(
            status=qc_status,
            metrics={
                "frames": int(params.shape[0]),
                "fd_first_frame": float(fd[0]),
                "mean_fd": float(np.mean(fd)),
                "max_fd": float(np.max(fd)),
                "fd_threshold_mm": float(fd_threshold_mm),
                "high_motion_frame_count": int(np.count_nonzero(high_motion)),
                "high_motion_fraction": float(np.count_nonzero(high_motion) / fd.shape[0]),
                "friston24_shape": [int(value) for value in friston.shape],
                "first_frame_strategy": "zero",
            },
            thresholds={"fd_threshold_mm": float(fd_threshold_mm)},
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters=parameters,
            status=status,
            capability_level="numerically_implemented",
            qc=qc,
            output_artifacts=output_refs,
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
