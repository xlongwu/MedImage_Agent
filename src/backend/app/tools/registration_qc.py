from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False


class _NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if _HAS_NUMPY:
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        return super().default(obj)


def _load_meta(path: Path) -> dict[str, Any]:
    if not _HAS_NUMPY:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.")

    try:
        import nibabel as nib
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel is required.") from exc

    img = nib.load(str(path))
    shape = list(img.shape)
    affine = img.affine
    zooms = list(img.header.get_zooms())

    voxel_center = np.array([(dim - 1) / 2.0 for dim in shape[:3]] + [1.0])
    world_center = affine @ voxel_center

    return {
        "path": str(path),
        "shape": shape,
        "voxel_size": zooms[:3],
        "affine": affine.tolist(),
        "world_center": [float(x) for x in world_center[:3]],
        "translation": [float(x) for x in affine[:3, 3]],
    }


def _euclidean(a: list[float], b: list[float]) -> float:
    return float(sum((x - y) ** 2 for x, y in zip(a, b, strict=False)) ** 0.5)


def compute_registration_qc_for_subject(
    subject_id: str,
    reference_nii: str,
    source_nii: str,
    coregistered_nii: str,
    derivatives_dir: str,
    center_distance_warning_mm: float = 30.0,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "registration_qc.json"
    qc_md = out_dir / "registration_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    reference_path = Path(reference_nii)
    source_path = Path(source_nii)
    coreg_path = Path(coregistered_nii)

    missing = [str(path) for path in [reference_path, source_path, coreg_path] if not path.exists()]

    if missing:
        result = {
            "ok": False,
            "node_id": "registration_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "registration_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            reference_meta = _load_meta(reference_path)
            source_meta = _load_meta(source_path)
            coreg_meta = _load_meta(coreg_path)

            affine_translation_distance_mm = _euclidean(
                source_meta["translation"],
                coreg_meta["translation"],
            )

            center_of_mass_distance_mm = _euclidean(
                reference_meta["world_center"],
                coreg_meta["world_center"],
            )

            if center_of_mass_distance_mm > center_distance_warning_mm:
                registration_qc_status = "WARNING"
                warnings.append(
                    f"Center distance {center_of_mass_distance_mm:.3f} exceeds warning threshold {center_distance_warning_mm}."
                )
            else:
                registration_qc_status = "PASS"

            result = {
                "ok": True,
                "node_id": "registration_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "reference_nii": str(reference_path),
                "source_nii": str(source_path),
                "coregistered_nii": str(coreg_path),
                "reference_shape": reference_meta["shape"],
                "source_shape": source_meta["shape"],
                "coregistered_shape": coreg_meta["shape"],
                "reference_voxel_size": reference_meta["voxel_size"],
                "source_voxel_size": source_meta["voxel_size"],
                "coregistered_voxel_size": coreg_meta["voxel_size"],
                "affine_translation_distance_mm": affine_translation_distance_mm,
                "center_of_mass_distance_mm": center_of_mass_distance_mm,
                "center_distance_warning_mm": center_distance_warning_mm,
                "registration_qc_status": registration_qc_status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "registration_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "registration_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, cls=_NpEncoder),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Registration QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('registration_qc_status')}")
    lines.append(f"- Reference: `{result.get('reference_nii')}`")
    lines.append(f"- Source: `{result.get('source_nii')}`")
    lines.append(f"- Coregistered: `{result.get('coregistered_nii')}`")
    lines.append(
        f"- Affine translation distance mm: {result.get('affine_translation_distance_mm')}"
    )
    lines.append(f"- Center distance mm: {result.get('center_of_mass_distance_mm')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Registration QC reads derivative headers only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_registration_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/registration_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid registration QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("registration_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("registration_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("registration_qc_status") == "FAIL")

    center_distances = [
        float(item["center_of_mass_distance_mm"])
        for item in subjects
        if item.get("center_of_mass_distance_mm") is not None
    ]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "registration_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_center_distance_mm": float(mean(center_distances)) if center_distances else None,
        "max_center_distance_mm": float(max(center_distances)) if center_distances else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "registration_qc_summary.json"
    report_path = report_out / "registration_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, cls=_NpEncoder),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Registration QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean center distance mm: {summary['mean_center_distance_mm']}")
    lines.append(f"- Max center distance mm: {summary['max_center_distance_mm']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Center Distance mm | Affine Translation Distance mm |")
    lines.append("|---|---|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('registration_qc_status')} | "
            f"{item.get('center_of_mass_distance_mm')} | "
            f"{item.get('affine_translation_distance_mm')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append(
        "This report summarizes derivative registration QC outputs only. It does not modify rawdata."
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "registration_qc_dataset_report",
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
