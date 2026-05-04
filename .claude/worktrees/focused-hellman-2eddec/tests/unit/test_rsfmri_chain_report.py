from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.rsfmri_chain_report import write_st_realign_motion_chain_report


def test_chain_report_aggregates_subject_status(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    reports = tmp_path / "reports"
    subject_id = "sub-001"

    qc_dir = derivatives / "rsfmri_qc" / subject_id
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    qc_dir.mkdir(parents=True)
    func_dir.mkdir(parents=True)

    (qc_dir / "slice_timing_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": subject_id,
            "slice_timing_status": "PASS",
        }),
        encoding="utf-8",
    )

    (func_dir / "spm_realign_result.json").write_text(
        json.dumps({
            "ok": True,
            "realigned_files": [str(func_dir / "rasub-001_bold.nii")],
            "mean_file": str(func_dir / "meanasub-001_bold.nii"),
            "motion_parameter_file": str(func_dir / "rp_asub-001_bold.txt"),
        }),
        encoding="utf-8",
    )

    (qc_dir / "motion_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": subject_id,
            "motion_qc_status": "PASS",
            "mean_fd": 0.1,
            "max_fd": 0.2,
        }),
        encoding="utf-8",
    )

    result = write_st_realign_motion_chain_report(
        derivatives_dir=str(derivatives),
        report_dir=str(reports),
    )

    assert result["ok"] is True

    summary_path = reports / "rsfmri" / "st_realign_motion_chain_summary.json"
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["subjects_total"] == 1
    assert summary["subjects_pass"] == 1
    assert summary["subjects"][0]["chain_status"] == "PASS"
