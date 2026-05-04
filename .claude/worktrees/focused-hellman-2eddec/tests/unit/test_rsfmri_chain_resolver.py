from __future__ import annotations

from pathlib import Path

from backend.app.tools.rsfmri_chain_resolver import (
    is_safe_slice_timing_derivative,
    resolve_realign_input,
)


def test_resolve_realign_input_prefers_slice_timing_derivative(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    derivative = (
        derivatives
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    )
    derivative.parent.mkdir(parents=True)
    derivative.write_bytes(b"fake nii")

    raw_bold = (
        tmp_path
        / "examples"
        / "synthetic_bids"
        / "rawdata"
        / subject_id
        / "func"
        / f"{subject_id}_task-rest_bold.nii.gz"
    )
    raw_bold.parent.mkdir(parents=True)
    raw_bold.write_bytes(b"fake raw")

    subject_record = {
        "sessions": [
            {
                "func": [
                    {"bold": str(raw_bold)}
                ]
            }
        ]
    }

    result = resolve_realign_input(
        subject_id=subject_id,
        subject_record=subject_record,
        derivatives_dir=str(derivatives),
        use_slice_timing_output=True,
    )

    assert result["ok"] is True
    assert result["input_type"] == "slice_timing_derivative"
    assert result["input_bold"] == str(derivative)


def test_slice_timing_derivative_must_match_expected_path(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    good = (
        derivatives
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    )
    good.parent.mkdir(parents=True)
    good.write_bytes(b"fake")

    bad = (
        derivatives
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / "some_other_file.nii"
    )
    bad.write_bytes(b"fake")

    assert is_safe_slice_timing_derivative(str(good), subject_id, str(derivatives)) is True
    assert is_safe_slice_timing_derivative(str(bad), subject_id, str(derivatives)) is False
