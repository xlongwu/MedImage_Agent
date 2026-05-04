from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _load_tissue_stats(path: Path, probability_threshold: float) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    img = nib.load(str(path))
    data = img.get_fdata(dtype="float32")
    zooms = list(img.header.get_zooms()[:3])
    voxel_volume = float(zooms[0] * zooms[1] * zooms[2])

    mask = data > probability_threshold
    voxel_count = int(np.count_nonzero(mask))

    return {
        "path": str(path),
        "shape": list(data.shape),
        "voxel_size": [float(x) for x in zooms],
        "mean_probability": float(np.mean(data)),
        "max_probability": float(np.max(data)),
        "voxel_count_over_threshold": voxel_count,
        "volume_mm3": float(voxel_count * voxel_volume),
    }


def compute_tissue_qc_for_subject(
    subject_id: str,
    gm_file: str,
    wm_file: str,
    csf_file: str,
    deformation_field: str,
    derivatives_dir: str,
    probability_threshold: float = 0.2,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "tissue_qc.json"
    qc_md = out_dir / "tissue_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    gm_path = Path(gm_file)
    wm_path = Path(wm_file)
    csf_path = Path(csf_file)
    deformation_path = Path(deformation_field)

    missing = [
        str(path)
        for path in [gm_path, wm_path, csf_path, deformation_path]
        if not path.exists()
    ]

    if missing:
        result = {
            "ok": False,
            "node_id": "tissue_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "segmentation_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            gm = _load_tissue_stats(gm_path, probability_threshold)
            wm = _load_tissue_stats(wm_path, probability_threshold)
            csf = _load_tissue_stats(csf_path, probability_threshold)

            shapes = {tuple(gm["shape"]), tuple(wm["shape"]), tuple(csf["shape"])}

            if len(shapes) != 1:
                status = "FAIL"
                errors.append("Tissue map shapes are inconsistent.")
            elif (
                gm["voxel_count_over_threshold"] == 0
                and wm["voxel_count_over_threshold"] == 0
                and csf["voxel_count_over_threshold"] == 0
            ):
                status = "WARNING"
                warnings.append("All tissue maps have zero voxels above threshold.")
            else:
                status = "PASS"

            result = {
                "ok": status != "FAIL",
                "node_id": "tissue_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "gm_file": str(gm_path),
                "wm_file": str(wm_path),
                "csf_file": str(csf_path),
                "deformation_field": str(deformation_path),
                "probability_threshold": probability_threshold,
                "gm_stats": gm,
                "wm_stats": wm,
                "csf_stats": csf,
                "gm_volume_mm3": gm["volume_mm3"],
                "wm_volume_mm3": wm["volume_mm3"],
                "csf_volume_mm3": csf["volume_mm3"],
                "segmentation_qc_status": status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "tissue_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "segmentation_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Tissue QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('segmentation_qc_status')}")
    lines.append(f"- GM volume mm3: {result.get('gm_volume_mm3')}")
    lines.append(f"- WM volume mm3: {result.get('wm_volume_mm3')}")
    lines.append(f"- CSF volume mm3: {result.get('csf_volume_mm3')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Tissue QC reads derivative tissue maps only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_tissue_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/tissue_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid tissue QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("segmentation_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("segmentation_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("segmentation_qc_status") == "FAIL")

    gm_volumes = [float(item["gm_volume_mm3"]) for item in subjects if item.get("gm_volume_mm3") is not None]
    wm_volumes = [float(item["wm_volume_mm3"]) for item in subjects if item.get("wm_volume_mm3") is not None]
    csf_volumes = [float(item["csf_volume_mm3"]) for item in subjects if item.get("csf_volume_mm3") is not None]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "tissue_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_gm_volume_mm3": float(mean(gm_volumes)) if gm_volumes else None,
        "mean_wm_volume_mm3": float(mean(wm_volumes)) if wm_volumes else None,
        "mean_csf_volume_mm3": float(mean(csf_volumes)) if csf_volumes else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "tissue_qc_summary.json"
    report_path = report_out / "tissue_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Tissue QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean GM volume mm3: {summary['mean_gm_volume_mm3']}")
    lines.append(f"- Mean WM volume mm3: {summary['mean_wm_volume_mm3']}")
    lines.append(f"- Mean CSF volume mm3: {summary['mean_csf_volume_mm3']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | GM Volume | WM Volume | CSF Volume |")
    lines.append("|---|---|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('segmentation_qc_status')} | "
            f"{item.get('gm_volume_mm3')} | {item.get('wm_volume_mm3')} | "
            f"{item.get('csf_volume_mm3')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative tissue QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "tissue_qc_dataset_report",
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
