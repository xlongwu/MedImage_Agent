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


def _first_t1w(subject: dict[str, Any]) -> str | None:
    for session in subject.get("sessions", []):
        anat = session.get("anat", {})
        t1w = anat.get("t1w")
        if t1w:
            return t1w
    return None


def _first_bold_record(subject: dict[str, Any]) -> dict[str, Any] | None:
    for session in subject.get("sessions", []):
        for func in session.get("func", []):
            if func.get("bold"):
                return func
    return None


def build_dpabi_input_manifest(
    dataset_index_path: str,
    work_dir: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    dataset_path = Path(dataset_index_path)
    dataset_index = _read_json(dataset_path)

    if not dataset_index:
        return {
            "ok": False,
            "node_id": "dpabi_input_manifest",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid dataset index: {dataset_path}"],
        }

    dpabi_dir = Path(work_dir) / "dpabi"
    workspace_dir = dpabi_dir / "dpabi_workspace"

    for subdir in ["rawdata_links", "configs", "logs", "outputs"]:
        (workspace_dir / subdir).mkdir(parents=True, exist_ok=True)

    subjects_out: list[dict[str, Any]] = []

    for subject in dataset_index.get("subjects", []):
        subject_id = subject.get("subject_id")
        dataset_status = subject.get("status", "UNKNOWN")
        issues: list[str] = []

        t1w = _first_t1w(subject)
        bold_record = _first_bold_record(subject)
        bold = bold_record.get("bold") if bold_record else None
        bold_json = bold_record.get("json") if bold_record else None
        metadata = bold_record.get("metadata", {}) if bold_record else {}
        tr = metadata.get("RepetitionTime")

        if dataset_status != "COMPLETE":
            issues.append(f"dataset_status={dataset_status}")

        if not t1w:
            issues.append("missing T1w")

        if not bold:
            issues.append("missing BOLD")

        if tr is None:
            issues.append("missing RepetitionTime")

        if not t1w:
            status = "MISSING_T1W"
        elif not bold:
            status = "MISSING_BOLD"
        elif tr is None:
            status = "MISSING_TR"
        elif dataset_status != "COMPLETE":
            status = "INCOMPLETE"
        else:
            status = "READY_FOR_DPABI_DRY_RUN"

        subjects_out.append({
            "subject_id": subject_id,
            "dataset_status": dataset_status,
            "status": status,
            "t1w": t1w,
            "bold": bold,
            "bold_json": bold_json,
            "tr": tr,
            "issues": issues,
        })

    subjects_ready = sum(
        1 for item in subjects_out
        if item["status"] == "READY_FOR_DPABI_DRY_RUN"
    )

    manifest = {
        "ok": True,
        "node_id": "dpabi_input_manifest",
        "backend": "python",
        "dataset_index": str(dataset_path),
        "workspace_dir": str(workspace_dir),
        "subjects_total": len(subjects_out),
        "subjects_ready": subjects_ready,
        "subjects": subjects_out,
        "warnings": warnings,
        "errors": errors,
    }

    manifest_path = dpabi_dir / "dpabi_input_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "node_id": "dpabi_input_manifest",
        "backend": "python",
        "outputs": [str(manifest_path), str(workspace_dir)],
        "metrics": {
            "subjects_total": len(subjects_out),
            "subjects_ready": subjects_ready,
        },
        "warnings": warnings,
        "errors": errors,
        "manifest_path": str(manifest_path),
    }
