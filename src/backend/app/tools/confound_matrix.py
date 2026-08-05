from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _read_motion_params(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        values = [float(item) for item in line.split()]
        if len(values) < 6:
            raise ValueError(f"Motion parameter row has fewer than 6 columns: {line}")
        rows.append(values[:6])
    if not rows:
        raise ValueError("Motion parameter file is empty.")
    return rows


def _diff_rows(rows: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for i, row in enumerate(rows):
        if i == 0:
            out.append([0.0] * len(row))
        else:
            prev = rows[i - 1]
            out.append([float(row[j] - prev[j]) for j in range(len(row))])
    return out


def _square_rows(rows: list[list[float]]) -> list[list[float]]:
    return [[float(value * value) for value in row] for row in rows]


def _matrix_qc(matrix: list[list[float]]) -> dict[str, Any]:
    import numpy as np

    arr = np.asarray(matrix, dtype=float)
    has_nan = bool(np.isnan(arr).any())
    has_inf = bool(np.isinf(arr).any())
    if arr.size == 0:
        rank = 0
        condition_number = None
    else:
        rank = int(np.linalg.matrix_rank(arr))
        try:
            condition_number = float(np.linalg.cond(arr))
        except Exception:
            condition_number = None
    return {
        "rows": int(arr.shape[0]) if arr.ndim == 2 else 0,
        "columns": int(arr.shape[1]) if arr.ndim == 2 else 0,
        "rank": rank,
        "condition_number": condition_number,
        "has_nan": has_nan,
        "has_inf": has_inf,
    }


def build_confound_matrix_for_subject(
    subject_id: str,
    motion_parameter_file: str,
    output_dir: str,
    model: str = "friston24",
    include_intercept: bool = True,
    include_linear_trend: bool = True,
    include_global_signal: bool = False,
) -> dict[str, Any]:
    out_dir = Path(output_dir) / "rsfmri_confounds" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)
    confounds_tsv = out_dir / "confounds.tsv"
    confounds_json = out_dir / "confounds.json"
    confound_qc_json = out_dir / "confound_qc.json"
    warnings: list[str] = []
    errors: list[str] = []
    motion_path = Path(motion_parameter_file)

    if not motion_path.exists():
        result = {
            "ok": False,
            "node_id": "confound_matrix_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "outputs": [],
            "warnings": warnings,
            "errors": [f"Motion parameter file not found: {motion_path}"],
        }
        confound_qc_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result

    try:
        motion = _read_motion_params(motion_path)
        n_tp = len(motion)
        base_names = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]
        motion_derivatives = _diff_rows(motion)
        columns: list[str] = []
        matrix_columns: list[list[float]] = []

        def add_family(names: list[str], rows: list[list[float]]):
            columns.extend(names)
            for col_idx in range(len(names)):
                matrix_columns.append([float(row[col_idx]) for row in rows])

        if include_intercept:
            columns.append("intercept")
            matrix_columns.append([1.0] * n_tp)
        if include_linear_trend:
            columns.append("linear_trend")
            if n_tp == 1:
                matrix_columns.append([0.0])
            else:
                matrix_columns.append([-1.0 + 2.0 * i / (n_tp - 1) for i in range(n_tp)])

        if model == "motion6":
            add_family(base_names, motion)
        elif model == "friston24":
            add_family(base_names, motion)
            add_family([f"{n}_derivative" for n in base_names], motion_derivatives)
            add_family([f"{n}_power2" for n in base_names], _square_rows(motion))
            add_family(
                [f"{n}_derivative_power2" for n in base_names], _square_rows(motion_derivatives)
            )
        else:
            raise ValueError(f"Unsupported nuisance model: {model}")

        if include_global_signal:
            warnings.append("global_signal requested but not implemented in Step 42.")

        matrix = [
            [matrix_columns[col_idx][row_idx] for col_idx in range(len(matrix_columns))]
            for row_idx in range(n_tp)
        ]
        qc = _matrix_qc(matrix)
        qc["column_names"] = columns

        with confounds_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(columns)
            writer.writerows(matrix)

        payload = {
            "subject_id": subject_id,
            "model": model,
            "include_intercept": include_intercept,
            "include_linear_trend": include_linear_trend,
            "include_global_signal": include_global_signal,
            "motion_parameter_file": str(motion_path),
            "confounds_tsv": str(confounds_tsv),
            "columns": columns,
            "qc": qc,
            "warnings": warnings,
            "errors": errors,
        }
        confounds_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        result = {
            "ok": not qc["has_nan"] and not qc["has_inf"],
            "node_id": "confound_matrix_subject",
            "backend": "python",
            "subject_id": subject_id,
            "model": model,
            "confounds_tsv": str(confounds_tsv),
            "confounds_json": str(confounds_json),
            "confound_qc_json": str(confound_qc_json),
            "qc": qc,
            "outputs": [str(confounds_tsv), str(confounds_json), str(confound_qc_json)],
            "warnings": warnings,
            "errors": errors,
        }
    except Exception as exc:
        result = {
            "ok": False,
            "node_id": "confound_matrix_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "outputs": [str(confound_qc_json)],
            "warnings": warnings,
            "errors": [str(exc)],
        }

    confound_qc_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
