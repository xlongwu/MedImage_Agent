from __future__ import annotations

import csv
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


def _subject_id_from_record(record: dict[str, Any]) -> str:
    return str(record.get("subject_id") or record.get("id") or "")


def _load_subject_state(
    work_dir: str,
    run_id: str,
    subject_id: str,
    node_id: str,
) -> dict[str, Any] | None:
    path = Path(work_dir) / "states" / run_id / subject_id / f"{node_id}.json"
    return _read_json(path)


def _load_subject_qc(
    derivatives_dir: str,
    subject_id: str,
) -> dict[str, Any] | None:
    path = Path(derivatives_dir) / "qc" / subject_id / "subject_qc.json"
    return _read_json(path)


def _recommend_subject(
    dataset_status: str,
    smooth_state: dict[str, Any] | None,
    qc_state: dict[str, Any] | None,
    qc_payload: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if dataset_status != "COMPLETE":
        reasons.append(f"dataset_status={dataset_status}")
        return "MANUAL_REVIEW", reasons

    if not smooth_state:
        reasons.append("missing spm_smooth_subject state")
        return "EXCLUDE", reasons

    if smooth_state.get("status") != "SUCCESS":
        reasons.append("spm_smooth_subject did not succeed")
        return "EXCLUDE", reasons

    if not qc_state:
        reasons.append("missing subject_qc state")
        return "EXCLUDE", reasons

    if qc_state.get("status") != "SUCCESS":
        reasons.append("subject_qc did not succeed")
        return "EXCLUDE", reasons

    if not qc_payload:
        reasons.append("missing subject_qc payload")
        return "MANUAL_REVIEW", reasons

    if not qc_payload.get("ok"):
        reasons.append("subject_qc payload ok=false")
        return "EXCLUDE", reasons

    metrics = qc_payload.get("metrics", {})
    nan_count = metrics.get("nan_count")
    finite_voxel_count = metrics.get("finite_voxel_count")
    std = metrics.get("std")
    shape = metrics.get("shape")

    if nan_count is not None and int(nan_count) > 0:
        reasons.append(f"nan_count={nan_count}")
        return "EXCLUDE", reasons

    if finite_voxel_count is not None and int(finite_voxel_count) == 0:
        reasons.append("finite_voxel_count=0")
        return "EXCLUDE", reasons

    if std is None or float(std) == 0.0:
        reasons.append("std is missing or zero")
        return "MANUAL_REVIEW", reasons

    if not shape:
        reasons.append("shape is missing")
        return "MANUAL_REVIEW", reasons

    return "INCLUDE", reasons


def _compute_dataset_quality_score(
    subjects_total: int,
    subjects_complete: int,
    subjects_preprocess_success: int,
    subjects_qc_success: int,
    subjects_manual_review: int,
    subjects_exclude: int,
) -> int:
    if subjects_total <= 0:
        return 0

    completeness_score = 30.0 * subjects_complete / subjects_total
    preprocess_score = 30.0 * subjects_preprocess_success / subjects_total
    qc_score = 30.0 * subjects_qc_success / subjects_total
    warning_penalty = min(10.0, 10.0 * subjects_manual_review / subjects_total)
    exclude_penalty = min(20.0, 20.0 * subjects_exclude / subjects_total)

    score = completeness_score + preprocess_score + qc_score + 10.0
    score -= warning_penalty
    score -= exclude_penalty

    return max(0, min(100, int(round(score))))


def evaluate_dataset(
    run_id: str,
    work_dir: str,
    derivatives_dir: str,
    report_dir: str,
    dataset_index_path: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    dataset_index_file = Path(dataset_index_path) if dataset_index_path else Path(work_dir) / "dataset_index" / "dataset_index.json"
    dataset_index = _read_json(dataset_index_file)

    if not dataset_index:
        return {
            "ok": False,
            "node_id": "dataset_evaluation",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Dataset index not found or invalid: {dataset_index_file}"],
        }

    subjects = dataset_index.get("subjects", [])
    out_dir = Path(report_dir) / "dataset_evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)

    subject_rows: list[dict[str, Any]] = []
    recommendation_rows: list[dict[str, Any]] = []

    subjects_total = len(subjects)
    subjects_complete = 0
    subjects_preprocess_success = 0
    subjects_qc_success = 0
    subjects_include = 0
    subjects_manual_review = 0
    subjects_exclude = 0

    for subject_record in subjects:
        subject_id = _subject_id_from_record(subject_record)
        dataset_status = str(subject_record.get("status", "UNKNOWN"))

        if dataset_status == "COMPLETE":
            subjects_complete += 1

        smooth_state = _load_subject_state(work_dir, run_id, subject_id, "spm_smooth_subject")
        qc_state = _load_subject_state(work_dir, run_id, subject_id, "subject_qc")
        qc_payload = _load_subject_qc(derivatives_dir, subject_id)

        smooth_status = smooth_state.get("status") if smooth_state else "MISSING"
        qc_status = qc_state.get("status") if qc_state else "MISSING"

        if smooth_status == "SUCCESS":
            subjects_preprocess_success += 1
        if qc_status == "SUCCESS" and qc_payload and qc_payload.get("ok"):
            subjects_qc_success += 1

        recommendation, reasons = _recommend_subject(
            dataset_status=dataset_status,
            smooth_state=smooth_state,
            qc_state=qc_state,
            qc_payload=qc_payload,
        )

        if recommendation == "INCLUDE":
            subjects_include += 1
        elif recommendation == "MANUAL_REVIEW":
            subjects_manual_review += 1
        elif recommendation == "EXCLUDE":
            subjects_exclude += 1

        metrics = qc_payload.get("metrics", {}) if qc_payload else {}

        row = {
            "subject_id": subject_id,
            "dataset_status": dataset_status,
            "smooth_status": smooth_status,
            "qc_status": qc_status,
            "recommendation": recommendation,
            "reasons": "; ".join(reasons),
            "shape": json.dumps(metrics.get("shape"), ensure_ascii=False),
            "dtype": metrics.get("dtype"),
            "mean": metrics.get("mean"),
            "std": metrics.get("std"),
            "min": metrics.get("min"),
            "max": metrics.get("max"),
            "nan_count": metrics.get("nan_count"),
            "finite_voxel_count": metrics.get("finite_voxel_count"),
        }
        subject_rows.append(row)

        if recommendation != "INCLUDE":
            recommendation_rows.append({
                "subject_id": subject_id,
                "recommendation": recommendation,
                "reasons": "; ".join(reasons),
            })

    dataset_quality_score = _compute_dataset_quality_score(
        subjects_total=subjects_total,
        subjects_complete=subjects_complete,
        subjects_preprocess_success=subjects_preprocess_success,
        subjects_qc_success=subjects_qc_success,
        subjects_manual_review=subjects_manual_review,
        subjects_exclude=subjects_exclude,
    )

    dataset_summary = {
        "run_id": run_id,
        "dataset_index": str(dataset_index_file),
        "subjects_total": subjects_total,
        "subjects_complete": subjects_complete,
        "subjects_preprocess_success": subjects_preprocess_success,
        "subjects_qc_success": subjects_qc_success,
        "subjects_include": subjects_include,
        "subjects_manual_review": subjects_manual_review,
        "subjects_exclude": subjects_exclude,
        "dataset_quality_score": dataset_quality_score,
        "warnings": warnings,
        "errors": errors,
        "disclaimer": "This report is for engineering QC and research preprocessing support only. It is not a clinical diagnosis.",
    }

    dataset_summary_path = out_dir / "dataset_summary.json"
    subject_qc_table_path = out_dir / "subject_qc_table.csv"
    exclusion_path = out_dir / "exclusion_recommendations.csv"

    dataset_summary_path.write_text(
        json.dumps(dataset_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if subject_rows:
        with subject_qc_table_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(subject_rows[0].keys()))
            writer.writeheader()
            writer.writerows(subject_rows)
    else:
        subject_qc_table_path.write_text("", encoding="utf-8")

    rec_fields = ["subject_id", "recommendation", "reasons"]
    with exclusion_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rec_fields)
        writer.writeheader()
        writer.writerows(recommendation_rows)

    return {
        "ok": True,
        "node_id": "dataset_evaluation",
        "backend": "python",
        "outputs": [
            str(dataset_summary_path),
            str(subject_qc_table_path),
            str(exclusion_path),
        ],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_complete": subjects_complete,
            "subjects_preprocess_success": subjects_preprocess_success,
            "subjects_qc_success": subjects_qc_success,
            "subjects_include": subjects_include,
            "subjects_manual_review": subjects_manual_review,
            "subjects_exclude": subjects_exclude,
            "dataset_quality_score": dataset_quality_score,
        },
        "warnings": warnings,
        "errors": errors,
    }
