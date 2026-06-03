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


def _compare_nifti(a_path: Path, b_path: Path) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError:
        return {
            "ok": False,
            "error": "Missing nibabel or numpy.",
        }

    if not a_path.exists() or not b_path.exists():
        return {
            "ok": False,
            "error": "One or both NIfTI files do not exist.",
        }

    a = nib.load(str(a_path)).get_fdata(dtype="float32")
    b = nib.load(str(b_path)).get_fdata(dtype="float32")

    if a.shape != b.shape:
        return {
            "ok": False,
            "shape_match": False,
            "a_shape": list(a.shape),
            "b_shape": list(b.shape),
        }

    diff = np.abs(a - b)

    return {
        "ok": True,
        "shape_match": True,
        "mean_abs_diff": float(np.mean(diff)),
        "max_abs_diff": float(np.max(diff)),
    }


def _find_spm_smooth_output(derivatives_dir: Path, subject_id: str) -> Path | None:
    candidates = list((derivatives_dir / "spm" / subject_id / "func").glob("*.nii"))
    if candidates:
        return candidates[0]
    candidates = list((derivatives_dir / "spm" / subject_id / "func").glob("*.nii.gz"))
    if candidates:
        return candidates[0]
    return None


def write_dpabi_subject_wrapper_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    # ── M7-DPABI-T007b: input/output scope hardening ──
    derivatives = Path(derivatives_dir)
    out_dir = Path(report_dir) / "dpabi"
    for path_val, label in [(derivatives, "derivatives_dir"), (out_dir.parent, "report_dir")]:
        resolved = path_val.resolve()
        rstr = str(resolved).replace("\\", "/")
        if ".." in rstr:
            return {"ok": False, "node_id": "dpabi_subject_wrapper_report",
                    "errors": [f"Path traversal rejected: {label}"], "outputs": []}
        if any(seg in ("rawdata", "data") for seg in resolved.parts):
            return {"ok": False, "node_id": "dpabi_subject_wrapper_report",
                    "errors": [f"{label} must not point to rawdata"], "outputs": []}
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "node_id": "dpabi_subject_wrapper_report",
                "errors": [f"Failed to create report directory: {exc}"], "outputs": []}

    summary_path = out_dir / "dpabi_subject_wrapper_summary.json"
    report_path = out_dir / "dpabi_subject_wrapper_report.md"

    result_paths = sorted(
        (derivatives / "dpabi_single_function").glob("*/func/dpabi_subject_wrapper_result.json")
    )

    subjects = []
    for rp in result_paths:
        data = _read_json(rp)
        if not data:
            continue
        subject_id = rp.parent.parent.name
        entry = {
            "subject_id": subject_id,
            "ok": bool(data.get("ok")),
            "function_name": data.get("function_name"),
            "metrics": data.get("metrics", {}),
            "errors": data.get("errors", []),
            "warnings": data.get("warnings", []),
            "result_json": str(rp),
        }

        dpabi_nii = derivatives / "dpabi_single_function" / subject_id / "func" / f"{subject_id}_dpabi_smooth.nii"
        spm_nii = _find_spm_smooth_output(derivatives, subject_id)

        if spm_nii and dpabi_nii.exists():
            comparison = _compare_nifti(dpabi_nii, spm_nii)
            entry["spm_comparison"] = comparison
        elif spm_nii:
            entry["spm_comparison"] = {"ok": False, "error": "DPABI output missing"}
        else:
            entry["spm_comparison"] = {"ok": False, "error": "SPM output not found for comparison"}

        subjects.append(entry)

    total = len(subjects)
    success = sum(1 for s in subjects if s["ok"])
    failed = total - success

    function_counts: dict[str, int] = {}
    for s in subjects:
        fn = s.get("function_name") or "unknown"
        function_counts[fn] = function_counts.get(fn, 0) + 1

    summary = {
        "ok": failed == 0 and total > 0,
        "subjects_total": total,
        "subjects_success": success,
        "subjects_failed": failed,
        "function_counts": function_counts,
        "subjects": subjects,
    }

    try:
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        return {"ok": False, "node_id": "dpabi_subject_wrapper_report",
                "errors": [f"Failed to write summary report: {exc}"], "outputs": []}

    lines = []
    lines.append("# DPABI Subject-Level Single-Function Wrapper Report")
    lines.append("")
    lines.append(f"- Total subjects: {total}")
    lines.append(f"- Success: {success}")
    lines.append(f"- Failed: {failed}")
    lines.append("")
    lines.append("## Function Counts")
    lines.append("")
    for fn, cnt in function_counts.items():
        lines.append(f"- {fn}: {cnt}")
    lines.append("")
    lines.append("## Subject Details")
    lines.append("")

    for s in subjects:
        lines.append(f"### {s['subject_id']}")
        lines.append(f"- OK: {s['ok']}")
        lines.append(f"- Function: {s.get('function_name', 'N/A')}")
        metrics = s.get("metrics", {})
        if metrics:
            lines.append("- Metrics:")
            for k, v in metrics.items():
                lines.append(f"  - {k}: {v}")
        comp = s.get("spm_comparison", {})
        if comp:
            lines.append("- SPM Comparison:")
            if comp.get("ok"):
                lines.append(f"  - Shape match: {comp.get('shape_match')}")
                lines.append(f"  - Mean abs diff: {comp.get('mean_abs_diff')}")
                lines.append(f"  - Max abs diff: {comp.get('max_abs_diff')}")
            else:
                lines.append(f"  - Error: {comp.get('error')}")
        if s.get("warnings"):
            lines.append("- Warnings:")
            for w in s["warnings"]:
                lines.append(f"  - {w}")
        if s.get("errors"):
            lines.append("- Errors:")
            for e in s["errors"]:
                lines.append(f"  - {e}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by MedImage Agent - DPABI Subject Wrapper*")

    try:
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "node_id": "dpabi_subject_wrapper_report",
                "errors": [f"Failed to write markdown report: {exc}"], "outputs": []}

    return {
        "ok": summary["ok"],
        "summary_json": str(summary_path),
        "report_md": str(report_path),
        "subjects_total": total,
        "subjects_success": success,
        "subjects_failed": failed,
    }
