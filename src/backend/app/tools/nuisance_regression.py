from __future__ import annotations
import csv, json
from pathlib import Path
from statistics import mean
from typing import Any

from src.backend.app.runtime.atomic_file import atomic_write_json


def _read_confounds(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t"); rows = list(reader)
    if not rows: raise ValueError("Confounds TSV is empty.")
    header = rows[0]; matrix = [[float(v) for v in row] for row in rows[1:] if row]
    return header, matrix

def _safe_input_path(path: Path, subject_id: str, derivatives_dir: str) -> bool:
    func_dir = (Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func").resolve()
    resolved = path.resolve()
    suffixes = "".join(path.suffixes).lower()
    is_nifti = path.suffix.lower() == ".nii" or suffixes.endswith(".nii.gz")
    if not is_nifti or not path.name.startswith(("swr", "swra", "r", "ra", "realigned_")):
        return False
    if any(part.lower() == "rawdata" for part in resolved.parts):
        return False
    try:
        resolved.relative_to(func_dir)
        return True
    except ValueError:
        pass
    project_root = Path(derivatives_dir).resolve().parent
    try:
        resolved.relative_to(project_root / "preprocessing_runs")
        return True
    except ValueError:
        return False


def run_python_nuisance_regression_subject(
    subject_id: str, input_nii: str, confounds_tsv: str, derivatives_dir: str,
) -> dict[str, Any]:
    try: import nibabel as nib; import numpy as np
    except ImportError as exc: raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    input_path = Path(input_nii); confounds_path = Path(confounds_tsv)
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True, exist_ok=True); qc_dir.mkdir(parents=True, exist_ok=True)
    result_json = func_dir / "nuisance_regression_result.json"
    qc_json = qc_dir / "nuisance_regression_qc.json"; qc_md = qc_dir / "nuisance_regression_qc.md"
    warnings: list[str] = []; errors: list[str] = []

    if not input_path.exists():
        return _write_failure(subject_id, result_json, qc_json, qc_md, [f"Input NIfTI not found: {input_path}"])
    if not _safe_input_path(input_path, subject_id, derivatives_dir):
        return _write_failure(subject_id, result_json, qc_json, qc_md, [f"Unsafe nuisance regression input: {input_path}"])
    if not confounds_path.exists():
        return _write_failure(subject_id, result_json, qc_json, qc_md, [f"Confounds TSV not found: {confounds_path}"])

    try:
        columns, confounds = _read_confounds(confounds_path)
        X = np.asarray(confounds, dtype=np.float64)
        img = nib.load(str(input_path)); data = img.get_fdata(dtype="float32")
        if data.ndim != 4: raise ValueError(f"Input NIfTI must be 4D. Shape was: {data.shape}")
        x, y, z, t = data.shape
        if X.shape[0] != t: raise ValueError(f"Confound rows {X.shape[0]} do not match timepoints {t}.")
        Y = data.reshape((-1, t)).T.astype(np.float64)
        beta = np.linalg.pinv(X) @ Y; fitted = X @ beta; residual = Y - fitted
        residual_4d = residual.T.reshape((x, y, z, t)).astype("float32")
        output_path = func_dir / f"resid_{input_path.name}"
        out_img = nib.Nifti1Image(residual_4d, affine=img.affine, header=img.header)
        nib.save(out_img, str(output_path))

        finite_mask = np.isfinite(residual_4d)
        finite_fraction = float(np.count_nonzero(finite_mask) / residual_4d.size) if residual_4d.size else 0.0
        input_std = float(np.std(data)); residual_std_val = float(np.std(residual_4d))
        variance_ratio = float(residual_std_val / input_std) if input_std > 0 else None
        rank = int(np.linalg.matrix_rank(X))

        status = "PASS"
        if finite_fraction < 0.95: status = "WARNING"; warnings.append(f"Residual finite fraction {finite_fraction:.4f} below 0.95.")
        if variance_ratio is not None and variance_ratio > 1.2: status = "WARNING"; warnings.append(f"Residual std larger than input std. Ratio={variance_ratio:.4f}.")

        qc = {"ok": True, "node_id": "nuisance_regression_qc_subject", "backend": "python", "subject_id": subject_id, "input_nii": str(input_path), "output_nii": str(output_path), "confounds_tsv": str(confounds_path), "input_shape": list(data.shape), "output_shape": list(residual_4d.shape), "confound_rows": int(X.shape[0]), "confound_columns": int(X.shape[1]), "confound_rank": rank, "finite_fraction": finite_fraction, "input_intensity_std": input_std, "residual_mean": float(np.mean(residual_4d)), "residual_std": residual_std_val, "variance_ratio": variance_ratio, "regression_qc_status": status, "outputs": [str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors}
        result = {"ok": True, "node_id": "python_nuisance_regression_subject", "backend": "python", "subject_id": subject_id, "input_nii": str(input_path), "output_nii": str(output_path), "confounds_tsv": str(confounds_path), "columns": columns, "qc": qc, "outputs": [str(output_path), str(result_json), str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors}
    except Exception as exc:
        return _write_failure(subject_id, result_json, qc_json, qc_md, [str(exc)])

    atomic_write_json(result_json, result, schema_version=1)
    atomic_write_json(qc_json, qc, schema_version=1)
    _write_qc_markdown(qc_md, qc)
    return result


def _write_failure(subject_id: str, result_json: Path, qc_json: Path, qc_md: Path, errors: list[str]) -> dict[str, Any]:
    qc = {"ok": False, "node_id": "nuisance_regression_qc_subject", "backend": "python", "subject_id": subject_id, "regression_qc_status": "FAIL", "outputs": [str(qc_json), str(qc_md)], "warnings": [], "errors": errors}
    result = {"ok": False, "node_id": "python_nuisance_regression_subject", "backend": "python", "subject_id": subject_id, "outputs": [str(result_json), str(qc_json), str(qc_md)], "warnings": [], "errors": errors}
    atomic_write_json(result_json, result, schema_version=1)
    atomic_write_json(qc_json, qc, schema_version=1)
    _write_qc_markdown(qc_md, qc)
    return result

def _write_qc_markdown(path: Path, qc: dict[str, Any]) -> None:
    lines = [f"# Nuisance Regression QC: {qc.get('subject_id')}", "", f"- OK: {qc.get('ok')}", f"- Status: {qc.get('regression_qc_status')}", f"- Input: `{qc.get('input_nii')}`", f"- Output: `{qc.get('output_nii')}`", f"- Confounds: `{qc.get('confounds_tsv')}`", f"- Confound shape: {qc.get('confound_rows')} x {qc.get('confound_columns')}", f"- Confound rank: {qc.get('confound_rank')}", f"- Finite fraction: {qc.get('finite_fraction')}", f"- Residual std: {qc.get('residual_std')}", f"- Variance ratio: {qc.get('variance_ratio')}", "", "## Safety Note", "", "Python nuisance regression reads derivative files only and does not modify rawdata."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def write_nuisance_regression_dataset_report(derivatives_dir: str, report_dir: str) -> dict[str, Any]:
    derivatives = Path(derivatives_dir); report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)
    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/nuisance_regression_qc.json"))
    subjects = []; warnings: list[str] = []; errors: list[str] = []
    for path in qc_paths:
        payload = _read_json(path)
        if not payload: warnings.append(f"Invalid nuisance regression QC JSON: {path}"); continue
        subjects.append(payload)
    subjects_total = len(subjects)
    pass_count = sum(1 for s in subjects if s.get("regression_qc_status") == "PASS")
    warning_count = sum(1 for s in subjects if s.get("regression_qc_status") == "WARNING")
    fail_count = sum(1 for s in subjects if s.get("regression_qc_status") == "FAIL")
    variance_ratios = [float(s["variance_ratio"]) for s in subjects if s.get("variance_ratio") is not None]
    summary = {"ok": subjects_total > 0 and fail_count == 0, "node_id": "nuisance_regression_qc_dataset_report", "backend": "python", "subjects_total": subjects_total, "subjects_pass": pass_count, "subjects_warning": warning_count, "subjects_fail": fail_count, "mean_variance_ratio": float(mean(variance_ratios)) if variance_ratios else None, "subjects": subjects, "warnings": warnings, "errors": errors}
    summary_path = report_out / "nuisance_regression_qc_summary.json"; report_path = report_out / "nuisance_regression_qc_report.md"
    atomic_write_json(summary_path, summary, schema_version=1)
    lines = ["# rs-fMRI Nuisance Regression QC Dataset Report", "", "## Summary", "", f"- Subjects total: {subjects_total}", f"- PASS: {pass_count}", f"- WARNING: {warning_count}", f"- FAIL: {fail_count}", f"- Mean variance ratio: {summary['mean_variance_ratio']}", "", "## Subjects", "", "| Subject | Status | Confounds | Rank | Variance Ratio |", "|---|---|---:|---:|---:|"]
    for item in subjects:
        lines.append(f"| {item.get('subject_id')} | {item.get('regression_qc_status')} | {item.get('confound_columns')} | {item.get('confound_rank')} | {item.get('variance_ratio')} |")
    lines += ["", "## Safety Note", "", "This report summarizes derivative nuisance regression QC outputs only. It does not modify rawdata."]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "node_id": "nuisance_regression_qc_dataset_report", "backend": "python", "outputs": [str(summary_path), str(report_path)], "metrics": {"subjects_total": subjects_total, "subjects_pass": pass_count, "subjects_warning": warning_count, "subjects_fail": fail_count}, "warnings": warnings, "errors": errors}
