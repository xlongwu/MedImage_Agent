from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median
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


def _framewise_displacement(
    rows: list[list[float]],
    head_radius_mm: float,
) -> list[float]:
    fd = [0.0]

    for i in range(1, len(rows)):
        prev = rows[i - 1]
        curr = rows[i]

        trans = sum(abs(curr[j] - prev[j]) for j in range(3))
        rot = sum(abs(curr[j] - prev[j]) for j in range(3, 6)) * head_radius_mm

        fd.append(float(trans + rot))

    return fd


def compute_motion_qc_for_subject(
    subject_id: str,
    motion_parameter_file: str,
    derivatives_dir: str,
    fd_threshold: float = 0.5,
    head_radius_mm: float = 50.0,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "motion_qc.json"
    qc_md = out_dir / "motion_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    motion_path = Path(motion_parameter_file)

    if not motion_path.exists():
        result = {
            "ok": False,
            "node_id": "motion_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": motion_parameter_file,
            "outputs": [],
            "warnings": warnings,
            "errors": [f"Motion parameter file not found: {motion_path}"],
        }
        qc_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        rows = _read_motion_params(motion_path)
        fd = _framewise_displacement(rows, head_radius_mm=head_radius_mm)

        high_motion = [value for value in fd if value > fd_threshold]
        translations = [[row[0], row[1], row[2]] for row in rows]
        rotations = [[row[3], row[4], row[5]] for row in rows]

        translation_max_abs_mm = max(abs(value) for row in translations for value in row)
        rotation_max_abs_rad = max(abs(value) for row in rotations for value in row)

        mean_fd = float(mean(fd))
        median_fd = float(median(fd))
        max_fd = float(max(fd))
        high_motion_frame_count = len(high_motion)
        high_motion_fraction = high_motion_frame_count / len(fd)

        if high_motion_fraction >= 0.2:
            motion_qc_status = "FAIL"
        elif high_motion_frame_count > 0:
            motion_qc_status = "WARNING"
        else:
            motion_qc_status = "PASS"

        result = {
            "ok": True,
            "node_id": "motion_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "frames_total": len(fd),
            "fd": fd,
            "fd_threshold": fd_threshold,
            "head_radius_mm": head_radius_mm,
            "mean_fd": mean_fd,
            "median_fd": median_fd,
            "max_fd": max_fd,
            "high_motion_frame_count": high_motion_frame_count,
            "high_motion_fraction": high_motion_fraction,
            "translation_max_abs_mm": float(translation_max_abs_mm),
            "rotation_max_abs_rad": float(rotation_max_abs_rad),
            "motion_qc_status": motion_qc_status,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        result = {
            "ok": False,
            "node_id": "motion_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [str(exc)],
        }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Motion QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('motion_qc_status')}")
    lines.append(f"- Frames total: {result.get('frames_total')}")
    lines.append(f"- Mean FD: {result.get('mean_fd')}")
    lines.append(f"- Median FD: {result.get('median_fd')}")
    lines.append(f"- Max FD: {result.get('max_fd')}")
    lines.append(f"- FD threshold: {result.get('fd_threshold')}")
    lines.append(f"- High-motion frames: {result.get('high_motion_frame_count')}")
    lines.append(f"- High-motion fraction: {result.get('high_motion_fraction')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Motion QC reads derivative motion parameters only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_motion_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/motion_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("motion_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("motion_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("motion_qc_status") == "FAIL")

    mean_fds = [float(item.get("mean_fd")) for item in subjects if item.get("mean_fd") is not None]
    max_fds = [float(item.get("max_fd")) for item in subjects if item.get("max_fd") is not None]

    summary = {
        "ok": fail_count == 0 and subjects_total > 0,
        "node_id": "motion_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "group_mean_fd": float(mean(mean_fds)) if mean_fds else None,
        "group_max_fd": float(max(max_fds)) if max_fds else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "motion_qc_summary.json"
    report_path = report_out / "motion_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Motion QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Group mean FD: {summary['group_mean_fd']}")
    lines.append(f"- Group max FD: {summary['group_max_fd']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Mean FD | Max FD | High-motion frames |")
    lines.append("|---|---|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('motion_qc_status')} | "
            f"{item.get('mean_fd')} | {item.get('max_fd')} | "
            f"{item.get('high_motion_frame_count')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative motion QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "motion_qc_dataset_report",
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
