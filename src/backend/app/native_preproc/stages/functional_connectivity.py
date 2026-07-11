"""Native ROI functional-connectivity stage."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def read_roi_timeseries_tsv(path: str | Path) -> tuple[list[str], np.ndarray]:
    rows: list[list[float]] = []
    columns: list[str] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        try:
            values = [float(value) for value in parts]
        except ValueError:
            if not columns:
                columns = [part.strip() for part in parts]
            continue
        rows.append(values)
    if not rows:
        raise ValueError(f"No numeric ROI time-series rows found in {path}.")
    matrix = np.asarray(rows, dtype=np.float32)
    if columns and len(columns) != matrix.shape[1]:
        raise ValueError("ROI time-series header column count does not match numeric matrix.")
    if not columns:
        columns = [f"roi_{index + 1}" for index in range(matrix.shape[1])]
    return columns, matrix


def fisher_z_transform(correlation: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(correlation, dtype=np.float64), -0.999999, 0.999999)
    transformed = np.arctanh(clipped).astype(np.float32)
    np.fill_diagonal(transformed, 0.0)
    return transformed


def compute_roi_functional_connectivity(
    roi_timeseries: np.ndarray,
    *,
    roi_names: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], list[str]]:
    warnings: list[str] = []
    matrix = np.asarray(roi_timeseries, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError("ROI time-series matrix must be 2D with rows=timepoints and columns=ROIs.")
    n_timepoints, n_rois = int(matrix.shape[0]), int(matrix.shape[1])
    if n_timepoints < 3:
        raise ValueError("Functional connectivity requires at least 3 timepoints.")
    if n_rois < 1:
        raise ValueError("Functional connectivity requires at least one ROI.")
    if not np.isfinite(matrix).all():
        raise ValueError("ROI time-series contains NaN or infinite values.")

    centered = matrix.astype(np.float64) - np.mean(matrix.astype(np.float64), axis=0, keepdims=True)
    stds = np.std(matrix.astype(np.float64), axis=0, ddof=1)
    constant = stds <= 1e-12
    if np.any(constant):
        names = roi_names or [f"roi_{idx + 1}" for idx in range(n_rois)]
        warnings.append(
            "constant_roi_timeseries:"
            + ",".join(str(names[index]) for index in np.flatnonzero(constant))
        )

    denom = np.outer(stds, stds) * float(n_timepoints - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = (centered.T @ centered) / denom
    corr = np.where(np.isfinite(corr), corr, 0.0).astype(np.float32)
    np.fill_diagonal(corr, 1.0)
    if np.any(constant):
        for index in np.flatnonzero(constant):
            corr[index, :] = 0.0
            corr[:, index] = 0.0
            corr[index, index] = 1.0
    fisher_z = fisher_z_transform(corr)
    qc = {
        "timepoints": n_timepoints,
        "roi_count": n_rois,
        "matrix_shape": [n_rois, n_rois],
        "correlation_method": "pearson",
        "standard_deviation_ddof": 1,
        "constant_roi_count": int(np.count_nonzero(constant)),
        "symmetric": bool(np.allclose(corr, corr.T, atol=1e-6)),
        "diagonal_all_ones": bool(np.allclose(np.diag(corr), 1.0, atol=1e-6)),
    }
    return corr, fisher_z, qc, warnings


def _write_square_tsv(path: str | Path, labels: list[str], matrix: np.ndarray) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = ["label\t" + "\t".join(labels)]
    for label, row in zip(labels, np.asarray(matrix, dtype=np.float64), strict=True):
        rows.append(label + "\t" + "\t".join(f"{float(value):.8f}" for value in row))
    target.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return target


def run_functional_connectivity(
    roi_timeseries: str | Path,
    output_dir: str | Path,
    *,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "functional_connectivity"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters: dict[str, Any] = {
        "roi_timeseries": str(roi_timeseries),
        "correlation_method": "pearson",
        "fisher_z": "arctanh_clipped_0_999999_diagonal_zero",
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        labels, matrix = read_roi_timeseries_tsv(roi_timeseries)
        corr, fisher_z, fc_qc, compute_warnings = compute_roi_functional_connectivity(matrix, roi_names=labels)
        warnings.extend(compute_warnings)
        stage_dir = context.stage_artifact_dir(stage_id)
        artifact_dir = stage_dir / stage_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        corr_npy = artifact_dir / "roi_timeseries_desc-pearson_fc.npy"
        z_npy = artifact_dir / "roi_timeseries_desc-fisher_z.npy"
        corr_tsv = artifact_dir / "roi_timeseries_desc-pearson_fc.tsv"
        z_tsv = artifact_dir / "roi_timeseries_desc-fisher_z.tsv"
        np.save(corr_npy, corr.astype(np.float32))
        np.save(z_npy, fisher_z.astype(np.float32))
        _write_square_tsv(corr_tsv, labels, corr)
        _write_square_tsv(z_tsv, labels, fisher_z)
        output_refs = [
            build_artifact_ref(
                corr_npy,
                artifact_type="fc_matrix",
                metadata={"labels": labels, "tsv_path": str(corr_tsv), **fc_qc},
            ),
            build_artifact_ref(
                z_npy,
                artifact_type="fisher_z_matrix",
                metadata={"labels": labels, "tsv_path": str(z_tsv), **fc_qc},
            ),
        ]
        qc = NativePreprocQC(
            status="warning" if warnings else "pass",
            metrics={
                "roi_timeseries_shape": [int(value) for value in matrix.shape],
                "correlation_stats": finite_stats(corr),
                "fisher_z_stats": finite_stats(fisher_z),
                **fc_qc,
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, **fc_qc},
            status="warning" if warnings else "succeeded",
            capability_level="numerically_implemented",
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
            capability_level="numerically_implemented",
            qc=qc,
            warnings=warnings,
            errors=errors,
        )
