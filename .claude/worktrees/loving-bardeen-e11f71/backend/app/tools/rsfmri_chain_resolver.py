from __future__ import annotations

from pathlib import Path
from typing import Any


def find_subject_raw_bold(subject_record: dict[str, Any]) -> str | None:
    for session in subject_record.get("sessions", []):
        for func in session.get("func", []):
            bold = func.get("bold")
            if bold:
                return bold
    return None


def is_safe_synthetic_raw_bold(path: str) -> bool:
    normalized = str(path).replace("\\", "/")
    return "examples/synthetic_bids/rawdata" in normalized and (
        normalized.endswith(".nii") or normalized.endswith(".nii.gz")
    )


def get_slice_timing_derivative(
    subject_id: str,
    derivatives_dir: str,
) -> str | None:
    path = (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    )

    return str(path) if path.exists() else None


def is_safe_slice_timing_derivative(
    path: str,
    subject_id: str,
    derivatives_dir: str,
) -> bool:
    target = Path(path).resolve()
    expected = (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    ).resolve()

    try:
        target.relative_to(Path(derivatives_dir).resolve())
    except ValueError:
        return False

    return target == expected and target.exists()


def resolve_realign_input(
    subject_id: str,
    subject_record: dict[str, Any],
    derivatives_dir: str,
    use_slice_timing_output: bool = True,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    raw_bold = find_subject_raw_bold(subject_record)

    if not raw_bold:
        return {
            "ok": False,
            "subject_id": subject_id,
            "input_type": None,
            "input_bold": None,
            "warnings": warnings,
            "errors": ["No raw BOLD found in subject record."],
        }

    if not is_safe_synthetic_raw_bold(raw_bold):
        return {
            "ok": False,
            "subject_id": subject_id,
            "input_type": None,
            "input_bold": None,
            "warnings": warnings,
            "errors": [f"Raw BOLD is not a safe synthetic input: {raw_bold}"],
        }

    if use_slice_timing_output:
        derivative = get_slice_timing_derivative(
            subject_id=subject_id,
            derivatives_dir=derivatives_dir,
        )

        if not derivative:
            return {
                "ok": False,
                "subject_id": subject_id,
                "input_type": "slice_timing_derivative",
                "input_bold": None,
                "raw_bold": raw_bold,
                "warnings": warnings,
                "errors": [
                    "Slice timing output was requested but not found.",
                    f"Expected: derivatives/rsfmri_preproc/{subject_id}/func/a{subject_id}_bold.nii",
                ],
            }

        if not is_safe_slice_timing_derivative(derivative, subject_id, derivatives_dir):
            return {
                "ok": False,
                "subject_id": subject_id,
                "input_type": "slice_timing_derivative",
                "input_bold": None,
                "raw_bold": raw_bold,
                "warnings": warnings,
                "errors": [f"Unsafe slice timing derivative: {derivative}"],
            }

        return {
            "ok": True,
            "subject_id": subject_id,
            "input_type": "slice_timing_derivative",
            "input_bold": derivative,
            "raw_bold": raw_bold,
            "warnings": warnings,
            "errors": errors,
        }

    return {
        "ok": True,
        "subject_id": subject_id,
        "input_type": "synthetic_raw_bold",
        "input_bold": raw_bold,
        "raw_bold": raw_bold,
        "warnings": warnings,
        "errors": errors,
    }
