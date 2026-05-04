from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _subject_ids_from_derivatives(derivatives: Path) -> list[str]:
    ids = set()

    for path in (derivatives / "rsfmri_qc").glob("*/slice_timing_qc.json"):
        ids.add(path.parent.name)

    for path in (derivatives / "rsfmri_qc").glob("*/motion_qc.json"):
        ids.add(path.parent.name)

    for path in (derivatives / "rsfmri_preproc").glob("*/func/spm_realign_result.json"):
        ids.add(path.parent.parent.name)

    return sorted(ids)


def _chain_status(slice_ok: bool, realign_ok: bool, motion_ok: bool, motion_status: str | None) -> str:
    if not slice_ok or not realign_ok or not motion_ok:
        return "FAIL"
    if motion_status == "FAIL":
        return "FAIL"
    if motion_status == "WARNING":
        return "WARNING"
    return "PASS"


def write_st_realign_motion_chain_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    subjects: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for subject_id in _subject_ids_from_derivatives(derivatives):
        slice_qc = _read_json(
            derivatives / "rsfmri_qc" / subject_id / "slice_timing_qc.json"
        )
        realign = _read_json(
            derivatives / "rsfmri_preproc" / subject_id / "func" / "spm_realign_result.json"
        )
        motion_qc = _read_json(
            derivatives / "rsfmri_qc" / subject_id / "motion_qc.json"
        )

        slice_ok = bool(slice_qc and slice_qc.get("ok"))
        realign_ok = bool(realign and realign.get("ok"))
        motion_ok = bool(motion_qc and motion_qc.get("ok"))
        motion_status = motion_qc.get("motion_qc_status") if motion_qc else None

        item = {
            "subject_id": subject_id,
            "slice_timing_ok": slice_ok,
            "slice_timing_status": slice_qc.get("slice_timing_status") if slice_qc else "MISSING",
            "realign_ok": realign_ok,
            "realigned_file": (realign.get("realigned_files") or [None])[0] if realign else None,
            "mean_file": realign.get("mean_file") if realign else None,
            "motion_parameter_file": realign.get("motion_parameter_file") if realign else None,
            "motion_qc_ok": motion_ok,
            "motion_qc_status": motion_status or "MISSING",
            "mean_fd": motion_qc.get("mean_fd") if motion_qc else None,
            "max_fd": motion_qc.get("max_fd") if motion_qc else None,
            "chain_status": _chain_status(slice_ok, realign_ok, motion_ok, motion_status),
        }

        subjects.append(item)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item["chain_status"] == "PASS")
    warning_count = sum(1 for item in subjects if item["chain_status"] == "WARNING")
    fail_count = sum(1 for item in subjects if item["chain_status"] == "FAIL")

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "st_realign_motion_chain_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "subjects": subjects,
        "safety": {
            "rawdata_modified": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dparsfa_run_executed": False,
            "dpabi_gui_called": False,
            "files_deleted": False,
        },
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "st_realign_motion_chain_summary.json"
    report_path = report_out / "st_realign_motion_chain_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Slice Timing to Realignment to Motion QC Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Slice Timing | Realign | Motion QC | Mean FD | Max FD | Chain Status |")
    lines.append("|---|---|---:|---|---:|---:|---|")

    for item in subjects:
        lines.append(
            f"| {item['subject_id']} | {item['slice_timing_status']} | "
            f"{item['realign_ok']} | {item['motion_qc_status']} | "
            f"{item['mean_fd']} | {item['max_fd']} | {item['chain_status']} |"
        )

    lines.append("")
    lines.append("## Safety")
    lines.append("")
    for key, value in summary["safety"].items():
        lines.append(f"- {key}: {value}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "st_realign_motion_chain_report",
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
