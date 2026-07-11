"""Native ROI time-series extraction from atlas-grounded labels."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.dpabi_compat.regressors import write_matrix_tsv
from src.backend.app.native_preproc.io.derivative_naming import derivative_path, nifti_stem
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.native_preproc import NativePreprocQC


@dataclass(frozen=True)
class RoiLabel:
    label: int
    name: str


def _safe_column_name(label: RoiLabel) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", label.name.strip()).strip("_") or f"ROI_{label.label}"
    return f"roi_{label.label}_{safe_name}"


def read_roi_labels(path: str | Path) -> list[RoiLabel]:
    label_path = Path(path)
    if label_path.suffix.lower() == ".json":
        payload = json.loads(label_path.read_text(encoding="utf-8"))
        rows = payload.get("labels", payload if isinstance(payload, list) else [])
        return [RoiLabel(label=int(row["label"]), name=str(row.get("name", f"ROI_{int(row['label'])}"))) for row in rows]

    labels: list[RoiLabel] = []
    lines = label_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 1:
            parts = line.split(",", maxsplit=1)
        try:
            label = int(parts[0].strip())
        except ValueError:
            continue
        name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else f"ROI_{label}"
        labels.append(RoiLabel(label=label, name=name))
    if not labels:
        raise ValueError(f"No ROI labels found in {label_path}.")
    return labels


def _label_definitions(atlas_3d: np.ndarray, labels_path: str | Path | None) -> tuple[list[RoiLabel], list[str]]:
    warnings: list[str] = []
    atlas_labels = sorted(int(value) for value in np.unique(atlas_3d) if int(value) > 0)
    if labels_path:
        definitions = read_roi_labels(labels_path)
        known = {label.label for label in definitions}
        for label in atlas_labels:
            if label not in known:
                definitions.append(RoiLabel(label=label, name=f"ROI_{label}"))
                warnings.append(f"atlas_label_{label}_missing_from_label_file")
        return sorted(definitions, key=lambda item: item.label), warnings
    return [RoiLabel(label=label, name=f"ROI_{label}") for label in atlas_labels], warnings


def extract_roi_timeseries(
    data_4d: np.ndarray,
    atlas_3d: np.ndarray,
    *,
    labels: list[RoiLabel],
) -> tuple[np.ndarray, dict[str, Any], list[str]]:
    warnings: list[str] = []
    data = np.asarray(data_4d, dtype=np.float32)
    atlas = np.asarray(atlas_3d)
    ensure_4d(data, stage_id="roi_timeseries")
    if atlas.shape != data.shape[:3]:
        raise ValueError(f"atlas shape {atlas.shape} does not match BOLD spatial shape {data.shape[:3]}.")
    if not labels:
        raise ValueError("At least one ROI label is required.")
    if not np.isfinite(data).all():
        warnings.append("input_contains_nan_or_inf_values_replaced_with_zero")
        data = np.where(np.isfinite(data), data, 0.0).astype(np.float32)

    flat = data.reshape((-1, data.shape[3]))
    atlas_flat = atlas.reshape((-1,))
    columns: list[np.ndarray] = []
    label_payload: list[dict[str, Any]] = []
    for label in labels:
        selected = atlas_flat == int(label.label)
        voxel_count = int(np.count_nonzero(selected))
        if voxel_count == 0:
            warnings.append(f"roi_{label.label}_empty")
            series = np.zeros(data.shape[3], dtype=np.float32)
        else:
            series = np.mean(flat[selected, :], axis=0).astype(np.float32)
            if not np.isfinite(series).all():
                warnings.append(f"roi_{label.label}_nonfinite_mean_replaced_with_zero")
                series = np.where(np.isfinite(series), series, 0.0).astype(np.float32)
        columns.append(series)
        label_payload.append({"label": int(label.label), "name": label.name, "voxel_count": voxel_count})

    matrix = np.column_stack(columns).astype(np.float32)
    qc = {
        "timepoints": int(data.shape[3]),
        "roi_count": int(len(labels)),
        "labels": label_payload,
        "orientation": "rows=timepoints_columns=rois",
        "matrix_shape": [int(value) for value in matrix.shape],
        "empty_roi_count": int(sum(1 for item in label_payload if item["voxel_count"] == 0)),
    }
    return matrix, qc, warnings


def run_roi_timeseries(
    input_bold: str | Path,
    atlas: str | Path,
    output_dir: str | Path,
    *,
    labels_path: str | Path | None = None,
    atlas_name: str = "custom",
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "roi_timeseries"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters: dict[str, Any] = {
        "atlas": str(atlas),
        "atlas_name": atlas_name,
        "labels_path": str(labels_path) if labels_path else None,
        "resource_policy": "caller_supplied_atlas_no_bundled_license_unconfirmed_resources",
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        atlas_image = load_nifti(atlas)
        if atlas_image.data.ndim != 3:
            raise ValueError(f"ROI time-series extraction requires 3D atlas input, got {atlas_image.data.shape}.")
        labels, label_warnings = _label_definitions(atlas_image.data, labels_path)
        warnings.extend(label_warnings)
        matrix, roi_qc, compute_warnings = extract_roi_timeseries(image.data, atlas_image.data, labels=labels)
        warnings.extend(compute_warnings)
        stage_dir = context.stage_artifact_dir(stage_id)
        tsv_path = derivative_path(stage_dir, image.path, stage_id=stage_id, suffix="roi_timeseries", extension=".tsv")
        label_json_path = stage_dir / f"{nifti_stem(image.path)}_desc-roi_labels.json"
        columns = [_safe_column_name(label) for label in labels]
        write_matrix_tsv(tsv_path, columns, matrix)
        atomic_write_json(
            label_json_path,
            {
                "atlas_name": atlas_name,
                "labels": roi_qc["labels"],
                "labels_path": str(labels_path) if labels_path else None,
                "resource_policy": parameters["resource_policy"],
            },
            schema_version=1,
        )
        output_refs = [
            build_artifact_ref(
                tsv_path,
                artifact_type="roi_timeseries",
                metadata={"columns": columns, **roi_qc},
            ),
            build_artifact_ref(
                label_json_path,
                artifact_type="roi_labels",
                metadata={"atlas_name": atlas_name, "label_count": len(labels)},
            ),
        ]
        qc = NativePreprocQC(
            status="warning" if warnings else "pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "atlas_shape": [int(value) for value in atlas_image.data.shape],
                "timeseries_stats": finite_stats(matrix),
                **roi_qc,
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, **roi_qc},
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
