from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from src.backend.app.tools.nuisance_regression_compute import (
    compute_nuisance_regression_backend,
    compute_nuisance_regression_numpy,
)


def _read_confounds(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)
    if not rows:
        raise ValueError("Confounds TSV is empty.")
    header = rows[0]
    matrix = [[float(v) for v in row] for row in rows[1:] if row]
    return header, matrix


def run_nuisance_regression_subject(
    subject_id: str,
    input_nii: str,
    confounds_tsv: str,
    derivatives_dir: str,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    benchmark_compare_cpu_gpu: bool = True,
) -> dict[str, Any]:
    """Run single-subject nuisance regression with optional GPU acceleration."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    confounds_path = Path(confounds_tsv)
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    result_json = func_dir / "nuisance_regression_result.json"
    qc_json = qc_dir / "nuisance_regression_qc.json"
    qc_md = qc_dir / "nuisance_regression_qc.md"

    if not input_path.exists():
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Input NIfTI not found: {input_path}"], warnings)
    if not confounds_path.exists():
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Confounds TSV not found: {confounds_path}"], warnings)

    try:
        columns, confounds = _read_confounds(confounds_path)
        X = np.asarray(confounds, dtype=np.float64)
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")
    except Exception as exc:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Failed to read input: {exc}"], warnings)

    if data.ndim != 4:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Input NIfTI must be 4D. Shape was: {data.shape}"], warnings)

    x, y, z, t_shape = data.shape
    if X.shape[0] != t_shape:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Confound rows {X.shape[0]} do not match timepoints {t_shape}."], warnings)

    result = compute_nuisance_regression_backend(
        data_4d=data,
        X=X,
        prefer_gpu=prefer_gpu,
        require_gpu=require_gpu,
    )

    if not result["ok"]:
        errors.extend(result.get("errors", []))
        return _fail(subject_id, result_json, qc_json, qc_md, errors, warnings)

    residual_4d = result["residual_4d"]
    output_path = input_path.with_name(f"resid_{input_path.name}")
    out_img = nib.Nifti1Image(residual_4d, affine=img.affine, header=img.header)
    nib.save(out_img, str(output_path))

    # Benchmark comparison
    benchmark = None
    if benchmark_compare_cpu_gpu and result["backend"] != "cpu-numpy":
        try:
            cpu_result = compute_nuisance_regression_numpy(data, X)
            if cpu_result["ok"] and cpu_result["residual_4d"] is not None:
                diff = np.abs(residual_4d - cpu_result["residual_4d"])
                benchmark = {
                    "gpu_backend": result["backend"],
                    "gpu_runtime_s": result["runtime_seconds"],
                    "cpu_runtime_s": cpu_result["runtime_seconds"],
                    "speedup": round(cpu_result["runtime_seconds"] / max(result["runtime_seconds"], 0.001), 2),
                    "max_abs_diff": float(np.max(diff)),
                    "mean_abs_diff": float(np.mean(diff)),
                }
                if benchmark["max_abs_diff"] > 1e-4:
                    warnings.append(
                        f"GPU vs CPU max_abs_diff = {benchmark['max_abs_diff']:.2e} exceeds 1e-4."
                    )
        except Exception as exc:
            warnings.append(f"CPU benchmark comparison failed: {exc}")

    input_std = result.get("input_std", float(np.std(data)))
    residual_std_val = result.get("residual_std", float(np.std(residual_4d)))
    finite_fraction = result.get("finite_fraction", 1.0)

    status = "PASS"
    if finite_fraction < 0.95:
        status = "WARNING"
        warnings.append(f"Residual finite fraction {finite_fraction:.4f} below 0.95.")
    if result.get("variance_ratio") is not None and result["variance_ratio"] > 1.2:
        status = "WARNING"
        warnings.append(f"Residual std larger than input std. Ratio={result['variance_ratio']:.4f}.")

    qc = {
        "ok": True, "node_id": "nuisance_regression_qc_subject",
        "backend": result["backend"], "subject_id": subject_id,
        "input_nii": str(input_path), "output_nii": str(output_path),
        "confounds_tsv": str(confounds_path),
        "input_shape": list(data.shape), "output_shape": list(residual_4d.shape),
        "confound_rows": int(X.shape[0]), "confound_columns": int(X.shape[1]),
        "confound_rank": result.get("confound_rank"),
        "finite_fraction": finite_fraction,
        "input_intensity_std": input_std, "residual_mean": float(np.mean(residual_4d)),
        "residual_std": residual_std_val, "variance_ratio": result.get("variance_ratio"),
        "gpu_backend": result["backend"], "runtime_seconds": result["runtime_seconds"],
        "benchmark": benchmark, "regression_qc_status": status,
        "outputs": [str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors,
    }

    output = {
        "ok": True, "node_id": "nuisance_regression_subject",
        "backend": result["backend"], "subject_id": subject_id,
        "input_nii": str(input_path), "output_nii": str(output_path),
        "confounds_tsv": str(confounds_path), "columns": columns, "qc": qc,
        "outputs": [str(output_path), str(result_json), str(qc_json), str(qc_md)],
        "gpu_backend": result["backend"], "runtime_seconds": result["runtime_seconds"],
        "benchmark": benchmark,
        "warnings": warnings, "errors": errors,
    }

    result_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qc_md, qc)
    return output


def _fail(subject_id: str, rj: Path, qj: Path, qm: Path,
          errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    w = warnings or []
    qc = {"ok": False, "node_id": "nuisance_regression_qc_subject", "backend": "unknown",
          "subject_id": subject_id, "regression_qc_status": "FAIL",
          "outputs": [str(qj), str(qm)], "warnings": w, "errors": errors}
    result = {"ok": False, "node_id": "nuisance_regression_subject", "backend": "unknown",
              "subject_id": subject_id, "outputs": [str(rj), str(qj), str(qm)],
              "warnings": w, "errors": errors}
    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc)
    return result


def _write_qc_md(path: Path, qc: dict[str, Any]) -> None:
    lines = [
        f"# Nuisance Regression QC: {qc.get('subject_id')}", "",
        f"- OK: {qc.get('ok')}",
        f"- Status: {qc.get('regression_qc_status')}",
        f"- Input: `{qc.get('input_nii')}`",
        f"- Output: `{qc.get('output_nii')}`",
        f"- Confounds: `{qc.get('confounds_tsv')}`",
        f"- Confound shape: {qc.get('confound_rows')} x {qc.get('confound_columns')}",
        f"- Confound rank: {qc.get('confound_rank')}",
        f"- Finite fraction: {qc.get('finite_fraction')}",
        f"- Residual std: {qc.get('residual_std')}",
        f"- Variance ratio: {qc.get('variance_ratio')}",
        f"- Backend: {qc.get('gpu_backend', 'unknown')}",
        f"- Runtime: {qc.get('runtime_seconds', 'N/A')}s",
        "", "## Safety Note", "",
        "Python nuisance regression reads derivative files only and does not modify rawdata.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
