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


def _voxel_size_close(actual: list[float], target: list[float], tolerance: float = 0.2) -> bool:
    if len(actual) < 3 or len(target) < 3:
        return False
    return all(abs(float(a) - float(t)) <= tolerance for a, t in zip(actual[:3], target[:3]))


def compute_normalization_qc_for_subject(
    subject_id: str,
    input_nii: str,
    deformation_field: str,
    normalized_nii: str,
    derivatives_dir: str,
    target_voxel_size: list[float] | None = None,
    finite_fraction_warning: float = 0.95,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "normalization_qc.json"
    qc_md = out_dir / "normalization_qc.md"

    target_voxel_size = target_voxel_size or [3.0, 3.0, 3.0]

    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    deformation_path = Path(deformation_field)
    normalized_path = Path(normalized_nii)

    missing = [
        str(path)
        for path in [input_path, deformation_path, normalized_path]
        if not path.exists()
    ]

    if missing:
        result = {
            "ok": False,
            "node_id": "normalization_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "normalization_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            input_stats = _load_nifti_stats(input_path)
            normalized_stats = _load_nifti_stats(normalized_path)

            status = "PASS"

            if normalized_stats["finite_fraction"] < finite_fraction_warning:
                status = "WARNING"
                warnings.append(
                    f"Finite fraction {normalized_stats['finite_fraction']:.4f} below threshold {finite_fraction_warning}."
                )

            if not _voxel_size_close(normalized_stats["voxel_size"], target_voxel_size):
                status = "WARNING"
                warnings.append(
                    f"Normalized voxel size {normalized_stats['voxel_size']} differs from target {target_voxel_size}."
                )

            result = {
                "ok": True,
                "node_id": "normalization_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "input_nii": str(input_path),
                "deformation_field": str(deformation_path),
                "normalized_nii": str(normalized_path),
                "input_shape": input_stats["shape"],
                "normalized_shape": normalized_stats["shape"],
                "input_voxel_size": input_stats["voxel_size"],
                "normalized_voxel_size": normalized_stats["voxel_size"],
                "target_voxel_size": target_voxel_size,
                "frames_total": normalized_stats["frames_total"],
                "finite_fraction": normalized_stats["finite_fraction"],
                "normalized_intensity_mean": normalized_stats["intensity_mean"],
                "normalized_intensity_std": normalized_stats["intensity_std"],
                "normalization_qc_status": status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "normalization_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "normalization_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Normalization QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('normalization_qc_status')}")
    lines.append(f"- Input: `{result.get('input_nii')}`")
    lines.append(f"- Deformation field: `{result.get('deformation_field')}`")
    lines.append(f"- Normalized: `{result.get('normalized_nii')}`")
    lines.append(f"- Input shape: {result.get('input_shape')}")
    lines.append(f"- Normalized shape: {result.get('normalized_shape')}")
    lines.append(f"- Normalized voxel size: {result.get('normalized_voxel_size')}")
    lines.append(f"- Finite fraction: {result.get('finite_fraction')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Normalization QC reads derivative files only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_normalization_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/normalization_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid normalization QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("normalization_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("normalization_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("normalization_qc_status") == "FAIL")

    finite_fractions = [
        float(item["finite_fraction"])
        for item in subjects
        if item.get("finite_fraction") is not None
    ]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "normalization_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_finite_fraction": float(mean(finite_fractions)) if finite_fractions else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "normalization_qc_summary.json"
    report_path = report_out / "normalization_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Normalization QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean finite fraction: {summary['mean_finite_fraction']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Shape | Voxel Size | Finite Fraction |")
    lines.append("|---|---|---|---|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('normalization_qc_status')} | "
            f"{item.get('normalized_shape')} | {item.get('normalized_voxel_size')} | "
            f"{item.get('finite_fraction')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative normalization QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "normalization_qc_dataset_report",
        "backend": "python",
        "outputs": [str(summary_path), str(report_path)],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_pass": pass_count,
            "subjects_warning": warning_count,
            "subjects_fail": fail_count,
        },
        "warnings": warnings,
        "errors": errors,
    }
