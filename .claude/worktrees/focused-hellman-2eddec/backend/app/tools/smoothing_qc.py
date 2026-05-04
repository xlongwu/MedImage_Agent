from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _load_nifti_stats(path: Path) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    img = nib.load(str(path))
    shape = list(img.shape)
    zooms = [float(x) for x in img.header.get_zooms()[:3]]
    affine = img.affine.tolist()

    data = img.get_fdata(dtype="float32")
    finite_mask = np.isfinite(data)
    finite_fraction = float(np.count_nonzero(finite_mask) / data.size) if data.size else 0.0

    if np.count_nonzero(finite_mask):
        finite_data = data[finite_mask]
        intensity_mean = float(np.mean(finite_data))
        intensity_std = float(np.std(finite_data))
    else:
        intensity_mean = None
        intensity_std = None

    return {
        "path": str(path),
        "shape": shape,
        "voxel_size": zooms,
        "affine": affine,
        "frames_total": int(shape[3]) if len(shape) >= 4 else 1,
        "finite_fraction": finite_fraction,
        "intensity_mean": intensity_mean,
        "intensity_std": intensity_std,
    }


def compute_smoothing_qc_for_subject(
    subject_id: str,
    input_nii: str,
    smoothed_nii: str,
    derivatives_dir: str,
    fwhm: list[float] | None = None,
    finite_fraction_warning: float = 0.95,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "smoothing_qc.json"
    qc_md = out_dir / "smoothing_qc.md"

    fwhm = fwhm or [6.0, 6.0, 6.0]

    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    smoothed_path = Path(smoothed_nii)

    missing = [
        str(path)
        for path in [input_path, smoothed_path]
        if not path.exists()
    ]

    if missing:
        result = {
            "ok": False,
            "node_id": "smoothing_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "smoothing_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            input_stats = _load_nifti_stats(input_path)
            smoothed_stats = _load_nifti_stats(smoothed_path)

            status = "PASS"

            if input_stats["shape"] != smoothed_stats["shape"]:
                status = "FAIL"
                errors.append("Input and smoothed output shapes differ.")

            if smoothed_stats["finite_fraction"] < finite_fraction_warning and status != "FAIL":
                status = "WARNING"
                warnings.append(
                    f"Finite fraction {smoothed_stats['finite_fraction']:.4f} below threshold {finite_fraction_warning}."
                )

            input_std = input_stats["intensity_std"]
            smoothed_std = smoothed_stats["intensity_std"]

            if input_std is None or input_std == 0 or smoothed_std is None:
                variance_reduction_ratio = None
            else:
                variance_reduction_ratio = float(smoothed_std / input_std)

            if (
                variance_reduction_ratio is not None
                and variance_reduction_ratio > 1.2
                and status != "FAIL"
            ):
                status = "WARNING"
                warnings.append(
                    f"Smoothed std appears larger than input std. Ratio={variance_reduction_ratio:.4f}."
                )

            filename_prefix_ok = smoothed_path.name.startswith("s")
            if not filename_prefix_ok and status != "FAIL":
                status = "WARNING"
                warnings.append("Smoothed output filename does not start with SPM prefix 's'.")

            result = {
                "ok": status != "FAIL",
                "node_id": "smoothing_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "input_nii": str(input_path),
                "smoothed_nii": str(smoothed_path),
                "input_shape": input_stats["shape"],
                "smoothed_shape": smoothed_stats["shape"],
                "input_voxel_size": input_stats["voxel_size"],
                "smoothed_voxel_size": smoothed_stats["voxel_size"],
                "frames_total": smoothed_stats["frames_total"],
                "fwhm": fwhm,
                "finite_fraction": smoothed_stats["finite_fraction"],
                "input_intensity_mean": input_stats["intensity_mean"],
                "input_intensity_std": input_stats["intensity_std"],
                "smoothed_intensity_mean": smoothed_stats["intensity_mean"],
                "smoothed_intensity_std": smoothed_stats["intensity_std"],
                "variance_reduction_ratio": variance_reduction_ratio,
                "filename_prefix_ok": filename_prefix_ok,
                "smoothing_qc_status": status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "smoothing_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "smoothing_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append(f"# Smoothing QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('smoothing_qc_status')}")
    lines.append(f"- Input: `{result.get('input_nii')}`")
    lines.append(f"- Smoothed: `{result.get('smoothed_nii')}`")
    lines.append(f"- FWHM: {result.get('fwhm')}")
    lines.append(f"- Shape: {result.get('smoothed_shape')}")
    lines.append(f"- Voxel size: {result.get('smoothed_voxel_size')}")
    lines.append(f"- Finite fraction: {result.get('finite_fraction')}")
    lines.append(f"- Variance reduction ratio: {result.get('variance_reduction_ratio')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Smoothing QC reads derivative files only and does not modify rawdata.")
    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None


def write_smoothing_qc_dataset_report(derivatives_dir: str, report_dir: str) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/smoothing_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid smoothing QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("smoothing_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("smoothing_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("smoothing_qc_status") == "FAIL")

    finite_fractions = [float(item["finite_fraction"]) for item in subjects if item.get("finite_fraction") is not None]
    variance_ratios = [float(item["variance_reduction_ratio"]) for item in subjects if item.get("variance_reduction_ratio") is not None]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "smoothing_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_finite_fraction": float(mean(finite_fractions)) if finite_fractions else None,
        "mean_variance_reduction_ratio": float(mean(variance_ratios)) if variance_ratios else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "smoothing_qc_summary.json"
    report_path = report_out / "smoothing_qc_report.md"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# rs-fMRI Smoothing QC Dataset Report", "", "## Summary", ""]
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean finite fraction: {summary['mean_finite_fraction']}")
    lines.append(f"- Mean variance reduction ratio: {summary['mean_variance_reduction_ratio']}")
    lines.append(""); lines.append("## Subjects"); lines.append("")
    lines.append("| Subject | Status | FWHM | Shape | Finite Fraction | Variance Ratio |")
    lines.append("|---|---|---|---|---:|---:|")

    for item in subjects:
        lines.append(f"| {item.get('subject_id')} | {item.get('smoothing_qc_status')} | {item.get('fwhm')} | {item.get('smoothed_shape')} | {item.get('finite_fraction')} | {item.get('variance_reduction_ratio')} |")

    lines.append(""); lines.append("## Safety Note"); lines.append("")
    lines.append("This report summarizes derivative smoothing QC outputs only. It does not modify rawdata.")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "smoothing_qc_dataset_report",
        "backend": "python",
        "outputs": [str(summary_path), str(report_path)],
        "metrics": {"subjects_total": subjects_total, "subjects_pass": pass_count, "subjects_warning": warning_count, "subjects_fail": fail_count},
        "warnings": warnings,
        "errors": errors,
    }
