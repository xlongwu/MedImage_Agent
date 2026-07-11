"""Regressor construction helpers for DPABI-like native nuisance regression."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from src.backend.app.native_preproc.dpabi_compat.qc_rules import rank_qc


MOTION_COLUMNS = ("trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z")


@dataclass(frozen=True)
class RegressorMatrix:
    values: np.ndarray
    columns: list[str]
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def qc(self) -> dict[str, Any]:
        payload = rank_qc(self.values)
        payload["column_names"] = list(self.columns)
        payload.update(self.metadata)
        return payload


def read_numeric_tsv(path: str | Path, *, min_columns: int = 1) -> np.ndarray:
    rows: list[list[float]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parts = line.replace(",", "\t").split()
        try:
            values = [float(value) for value in parts]
        except ValueError:
            continue
        if len(values) < min_columns:
            raise ValueError(f"Numeric row has fewer than {min_columns} columns: {line}")
        rows.append(values)
    if not rows:
        raise ValueError(f"No numeric rows found in {path}.")
    return np.asarray(rows, dtype=np.float32)


def write_matrix_tsv(path: str | Path, columns: list[str], matrix: np.ndarray) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    values = np.asarray(matrix, dtype=np.float64)
    lines = ["\t".join(columns)]
    for row in values:
        lines.append("\t".join(f"{float(value):.8f}" for value in row))
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def polynomial_trends(
    n_timepoints: int,
    *,
    order: int = 1,
    include_intercept: bool = True,
) -> RegressorMatrix:
    if n_timepoints <= 0:
        raise ValueError("n_timepoints must be positive.")
    if order < 0:
        raise ValueError("polynomial order must be non-negative.")
    x = np.linspace(-1.0, 1.0, int(n_timepoints), dtype=np.float32)
    columns: list[str] = []
    parts: list[np.ndarray] = []
    start_power = 0 if include_intercept else 1
    for power in range(start_power, order + 1):
        columns.append("intercept" if power == 0 else f"poly{power}_trend")
        parts.append((x**power).reshape((-1, 1)).astype(np.float32))
    if not parts:
        return RegressorMatrix(np.zeros((n_timepoints, 0), dtype=np.float32), [])
    return RegressorMatrix(np.hstack(parts).astype(np.float32), columns)


def motion_regressors(motion_parameters: np.ndarray, *, model: str = "friston24") -> RegressorMatrix:
    motion = np.asarray(motion_parameters, dtype=np.float32)
    if motion.ndim != 2 or motion.shape[1] < 6:
        raise ValueError("motion_parameters must have shape (timepoints, >=6).")
    base = motion[:, :6]
    derivative = np.vstack([np.zeros((1, 6), dtype=np.float32), np.diff(base, axis=0)])
    normalized = model.lower().replace("_", "").replace("-", "")
    parts: list[np.ndarray] = []
    columns: list[str] = []

    def add(suffix: str, values: np.ndarray) -> None:
        parts.append(values.astype(np.float32))
        columns.extend([f"{name}{suffix}" for name in MOTION_COLUMNS])

    if normalized in {"motion6", "friston6"}:
        add("", base)
    elif normalized in {"motion12", "friston12"}:
        add("", base)
        add("_derivative", derivative)
    elif normalized == "friston24":
        add("", base)
        add("_derivative", derivative)
        add("_power2", base**2)
        add("_derivative_power2", derivative**2)
    else:
        raise ValueError(f"Unsupported motion regressor model: {model}")
    return RegressorMatrix(np.hstack(parts).astype(np.float32), columns, metadata={"motion_model": model})


def load_motion_regressors(path: str | Path, *, model: str = "friston24") -> RegressorMatrix:
    return motion_regressors(read_numeric_tsv(path, min_columns=6), model=model)


def extract_mask_mean_signal(
    bold_4d: np.ndarray,
    mask_3d: np.ndarray,
    *,
    column_name: str,
    threshold: float = 0.5,
) -> RegressorMatrix:
    data = np.asarray(bold_4d, dtype=np.float32)
    mask = np.asarray(mask_3d, dtype=np.float32)
    if data.ndim != 4:
        raise ValueError(f"{column_name} extraction requires 4D BOLD input.")
    if mask.shape != data.shape[:3]:
        raise ValueError(f"{column_name} mask shape {mask.shape} does not match BOLD spatial shape {data.shape[:3]}.")
    selected = np.isfinite(mask) & (mask > float(threshold))
    if int(np.count_nonzero(selected)) == 0:
        raise ValueError(f"{column_name} mask is empty at threshold {threshold}.")
    signal = np.nanmean(data[selected, :], axis=0).reshape((-1, 1)).astype(np.float32)
    return RegressorMatrix(
        signal,
        [column_name],
        metadata={f"{column_name}_voxel_count": int(np.count_nonzero(selected))},
    )


def extract_global_signal(
    bold_4d: np.ndarray,
    *,
    brain_mask_3d: np.ndarray | None = None,
    threshold: float = 0.5,
) -> RegressorMatrix:
    data = np.asarray(bold_4d, dtype=np.float32)
    if data.ndim != 4:
        raise ValueError("global signal extraction requires 4D BOLD input.")
    if brain_mask_3d is None:
        selected = np.all(np.isfinite(data), axis=3)
    else:
        mask = np.asarray(brain_mask_3d, dtype=np.float32)
        if mask.shape != data.shape[:3]:
            raise ValueError(f"global signal mask shape {mask.shape} does not match BOLD spatial shape {data.shape[:3]}.")
        selected = np.isfinite(mask) & (mask > float(threshold))
    if int(np.count_nonzero(selected)) == 0:
        raise ValueError("global signal mask is empty.")
    signal = np.nanmean(data[selected, :], axis=0).reshape((-1, 1)).astype(np.float32)
    return RegressorMatrix(
        signal,
        ["global_signal"],
        metadata={"global_signal_voxel_count": int(np.count_nonzero(selected))},
    )


def scrubbing_regressors(
    fd_timeseries: np.ndarray,
    *,
    threshold_mm: float,
    n_timepoints: int | None = None,
) -> RegressorMatrix:
    fd = np.asarray(fd_timeseries, dtype=np.float32).reshape((-1,))
    if n_timepoints is not None and fd.shape[0] != int(n_timepoints):
        raise ValueError(f"FD length {fd.shape[0]} does not match timepoints {n_timepoints}.")
    high_motion = np.flatnonzero(fd > float(threshold_mm))
    matrix = np.zeros((fd.shape[0], len(high_motion)), dtype=np.float32)
    columns: list[str] = []
    for col_idx, frame_idx in enumerate(high_motion):
        matrix[frame_idx, col_idx] = 1.0
        columns.append(f"scrub_frame_{int(frame_idx):04d}")
    metadata = {
        "scrubbing_strategy": "spike_regressors_preserve_timepoints",
        "scrub_threshold_mm": float(threshold_mm),
        "scrubbed_frame_count": int(len(high_motion)),
        "scrubbed_frames": [int(value) for value in high_motion],
    }
    return RegressorMatrix(matrix, columns, metadata=metadata)


def combine_regressor_matrices(*matrices: RegressorMatrix) -> RegressorMatrix:
    included = [matrix for matrix in matrices if matrix.values.shape[1] > 0]
    if not included:
        raise ValueError("At least one confound regressor column is required.")
    n_rows = included[0].values.shape[0]
    for matrix in included:
        if matrix.values.shape[0] != n_rows:
            raise ValueError("Confound regressor row counts do not match.")
    values = np.hstack([matrix.values for matrix in included]).astype(np.float32)
    columns: list[str] = []
    warnings: list[str] = []
    metadata: dict[str, Any] = {}
    for matrix in included:
        columns.extend(matrix.columns)
        warnings.extend(matrix.warnings)
        metadata.update(matrix.metadata)
    if not np.isfinite(values).all():
        raise ValueError("Confound matrix contains NaN or infinite values.")
    return RegressorMatrix(values, columns, warnings=warnings, metadata=metadata)


def build_confound_matrix(
    *,
    n_timepoints: int,
    motion: np.ndarray | None = None,
    motion_model: str = "friston24",
    tissue_signals: Mapping[str, np.ndarray] | None = None,
    global_signal: np.ndarray | None = None,
    polynomial_order: int = 1,
    include_intercept: bool = True,
    fd_timeseries: np.ndarray | None = None,
    scrub_threshold_mm: float | None = None,
) -> RegressorMatrix:
    parts: list[RegressorMatrix] = [
        polynomial_trends(n_timepoints, order=polynomial_order, include_intercept=include_intercept)
    ]
    if motion is not None:
        parts.append(motion_regressors(motion, model=motion_model))
    for name, signal in (tissue_signals or {}).items():
        values = np.asarray(signal, dtype=np.float32).reshape((-1, 1))
        parts.append(RegressorMatrix(values, [name]))
    if global_signal is not None:
        parts.append(RegressorMatrix(np.asarray(global_signal, dtype=np.float32).reshape((-1, 1)), ["global_signal"]))
    if fd_timeseries is not None and scrub_threshold_mm is not None:
        parts.append(scrubbing_regressors(fd_timeseries, threshold_mm=scrub_threshold_mm, n_timepoints=n_timepoints))
    return combine_regressor_matrices(*parts)
