from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _find_subject_dirs(rawdata_path: Path) -> list[Path]:
    """Find all subject directories (sub-*) in rawdata."""
    if not rawdata_path.exists():
        return []
    return sorted([d for d in rawdata_path.iterdir() if d.is_dir() and d.name.startswith("sub-")])


def _find_session_dirs(subject_dir: Path) -> list[Path]:
    """Find all session directories (ses-*) in subject directory."""
    if not subject_dir.exists():
        return []
    sessions = [d for d in subject_dir.iterdir() if d.is_dir() and d.name.startswith("ses-")]
    return sorted(sessions) if sessions else [subject_dir]


def _find_t1w(anat_dir: Path) -> str | None:
    """Find T1w file in anat directory."""
    if not anat_dir.exists():
        return None
    for ext in [".nii.gz", ".nii"]:
        for f in anat_dir.glob(f"*{ext}"):
            if "T1w" in f.name:
                return str(f)
    return None


def _find_bold_files(func_dir: Path) -> list[dict[str, Any]]:
    """Find BOLD files and their sidecar JSONs in func directory."""
    if not func_dir.exists():
        return []

    bold_files = []
    for ext in [".nii.gz", ".nii"]:
        for bold_file in func_dir.glob(f"*bold{ext}"):
            json_file = bold_file.with_suffix("").with_suffix(".json")
            if not json_file.exists():
                json_file = bold_file.with_suffix("").with_suffix("").with_suffix(".json")

            bold_info = {
                "bold": str(bold_file),
                "json": str(json_file) if json_file.exists() else None,
                "exists": bold_file.exists(),
                "metadata": {},
            }

            if json_file.exists():
                try:
                    bold_info["metadata"] = json.loads(json_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    bold_info["metadata"] = {}

            bold_files.append(bold_info)

    return bold_files


def _read_nifti_metadata(path: str) -> dict[str, Any]:
    """Read NIfTI file metadata using nibabel."""
    try:
        import nibabel as nib

        img = nib.load(path)
        return {
            "shape": list(img.shape),
            "dtype": str(img.get_fdata().dtype),
            "affine": img.affine.tolist(),
        }
    except Exception:
        return {}


def _determine_subject_status(t1w_exists: bool, bold_count: int, issues: list[str]) -> str:
    """Determine subject status based on file availability."""
    if not t1w_exists and bold_count == 0:
        return "INCOMPLETE"
    if not t1w_exists:
        return "MISSING_T1W"
    if bold_count == 0:
        return "MISSING_BOLD"
    if issues:
        return "WARNING"
    return "COMPLETE"


def inspect_dataset(
    rawdata_dir: str,
    output_dir: str,
    read_nifti_metadata: bool = True,
) -> dict[str, Any]:
    """Inspect BIDS-like dataset and generate index and completeness report."""
    try:
        import nibabel

        read_nifti_metadata = read_nifti_metadata and nibabel is not None
    except ImportError:
        read_nifti_metadata = False

    rawdata_path = Path(rawdata_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    errors: list[str] = []

    if not rawdata_path.exists():
        errors.append(f"Rawdata directory not found: {rawdata_dir}")
        return {
            "ok": False,
            "node_id": "data_inspection",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": errors,
        }

    subject_dirs = _find_subject_dirs(rawdata_path)
    if not subject_dirs:
        warnings.append(f"No subject directories found in {rawdata_dir}")

    subjects_data = []
    subject_table_rows = []

    for subject_dir in subject_dirs:
        subject_id = subject_dir.name
        subject_issues = []

        # Check for sessions or use subject dir directly
        session_dirs = _find_session_dirs(subject_dir)
        sessions_data = []

        for session_dir in session_dirs:
            session_id = session_dir.name if session_dir != subject_dir else None

            # Find anatomical data
            anat_dir = session_dir / "anat"
            t1w_path = _find_t1w(anat_dir)

            anat_data = {
                "t1w": t1w_path,
                "exists": t1w_path is not None,
            }

            if t1w_path and read_nifti_metadata:
                anat_data["metadata"] = _read_nifti_metadata(t1w_path)

            # Find functional data
            func_dir = session_dir / "func"
            bold_files = _find_bold_files(func_dir)

            if read_nifti_metadata:
                for bold_info in bold_files:
                    if bold_info["exists"]:
                        bold_info["nifti_metadata"] = _read_nifti_metadata(bold_info["bold"])

            sessions_data.append(
                {
                    "session_id": session_id,
                    "anat": anat_data,
                    "func": bold_files,
                }
            )

        # Determine subject status
        t1w_exists = any(s["anat"]["exists"] for s in sessions_data)
        bold_count = sum(len(s["func"]) for s in sessions_data)

        if not t1w_exists:
            subject_issues.append("Missing T1w")
        if bold_count == 0:
            subject_issues.append("Missing BOLD")

        status = _determine_subject_status(t1w_exists, bold_count, subject_issues)

        subjects_data.append(
            {
                "subject_id": subject_id,
                "sessions": sessions_data,
                "status": status,
                "issues": subject_issues,
            }
        )

        subject_table_rows.append(
            {
                "subject_id": subject_id,
                "status": status,
                "t1w_exists": t1w_exists,
                "bold_count": bold_count,
                "issues": "; ".join(subject_issues) if subject_issues else "",
            }
        )

    # Create dataset index
    dataset_index = {
        "dataset_root": str(rawdata_path),
        "subjects_total": len(subjects_data),
        "subjects": subjects_data,
    }

    # Create completeness report
    subjects_complete = sum(1 for s in subjects_data if s["status"] == "COMPLETE")
    subjects_missing_t1w = sum(1 for s in subjects_data if s["status"] == "MISSING_T1W")
    subjects_missing_bold = sum(1 for s in subjects_data if s["status"] == "MISSING_BOLD")
    subjects_with_issues = sum(1 for s in subjects_data if s["issues"])

    completeness_report = {
        "subjects_total": len(subjects_data),
        "subjects_complete": subjects_complete,
        "subjects_missing_t1w": subjects_missing_t1w,
        "subjects_missing_bold": subjects_missing_bold,
        "subjects_with_issues": subjects_with_issues,
        "issues": errors,
    }

    # Write outputs
    index_path = output_path / "dataset_index.json"
    report_path = output_path / "data_completeness_report.json"
    table_path = output_path / "subject_table.csv"

    index_path.write_text(json.dumps(dataset_index, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(
        json.dumps(completeness_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Write subject table CSV
    with table_path.open("w", newline="", encoding="utf-8") as f:
        if subject_table_rows:
            writer = csv.DictWriter(
                f, fieldnames=["subject_id", "status", "t1w_exists", "bold_count", "issues"]
            )
            writer.writeheader()
            writer.writerows(subject_table_rows)
        else:
            f.write("subject_id,status,t1w_exists,bold_count,issues\n")

    outputs = [
        str(index_path),
        str(report_path),
        str(table_path),
    ]

    return {
        "ok": True,
        "node_id": "data_inspection",
        "backend": "python",
        "outputs": outputs,
        "metrics": {
            "subjects_total": len(subjects_data),
            "subjects_complete": subjects_complete,
        },
        "warnings": warnings,
        "errors": errors,
    }
