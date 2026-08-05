"""Integration test validating end-to-end pipeline structure and connectivity."""

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np


def test_synthetic_bids_to_alff_integration(tmp_path: Path):
    """Validate the full chain: synthetic BIDS -> ALFF without MATLAB."""
    d = tmp_path / "derivatives"
    sid = "sub-001"
    # Setup minimal derivative structure
    fd = d / "rsfmri_preproc" / sid / "func"
    fd.mkdir(parents=True)
    qd = d / "rsfmri_qc" / sid
    qd.mkdir(parents=True)

    # Create synthetic filtered residual and residual (both needed by ALFF)
    nt = 16
    tr_data = np.random.default_rng(42).normal(size=(4, 4, 4, nt)).astype(np.float32)
    rp = fd / "resid_swrasub-001_bold.nii"
    ip = fd / "filt_resid_swrasub-001_bold.nii"
    nib.save(nib.Nifti1Image(tr_data, affine=np.eye(4)), str(rp))
    nib.save(nib.Nifti1Image(tr_data, affine=np.eye(4)), str(ip))

    # Slice timing QC for TR
    (qd / "slice_timing_qc.json").write_text(
        json.dumps({"ok": True, "subject_id": sid, "tr": 2.0, "slice_timing_status": "PASS"}),
        encoding="utf-8",
    )
    # Temporal filtering QC
    (qd / "temporal_filtering_qc.json").write_text(
        json.dumps(
            {
                "ok": True,
                "subject_id": sid,
                "tr": 2.0,
                "low_hz": 0.01,
                "high_hz": 0.08,
                "filtering_qc_status": "PASS",
            }
        ),
        encoding="utf-8",
    )

    # Test ALFF/fALFF
    from src.backend.app.tools.alff_falff import run_python_alff_falff_subject

    r = run_python_alff_falff_subject(subject_id=sid, derivatives_dir=str(d))
    assert r["ok"] is True
    assert (d / "rsfmri_metrics" / sid / "alff.nii").exists()
    assert (d / "rsfmri_metrics" / sid / "falff.nii").exists()

    # Test ReHo
    from src.backend.app.tools.reho import run_python_reho_subject

    r_reho = run_python_reho_subject(subject_id=sid, derivatives_dir=str(d), neighborhood=27)
    assert r_reho["ok"] is True
    assert (d / "rsfmri_metrics" / sid / "reho.nii").exists()

    # Test FC
    from src.backend.app.tools.functional_connectivity import (
        run_python_functional_connectivity_subject,
    )

    r_fc = run_python_functional_connectivity_subject(
        subject_id=sid, derivatives_dir=str(d), roi_count=2
    )
    assert r_fc["ok"] is True
    assert (d / "rsfmri_fc" / sid / "roi_timeseries.tsv").exists()
    assert (d / "rsfmri_fc" / sid / "correlation_matrix.tsv").exists()

    # Test confound matrix
    from src.backend.app.tools.confound_matrix import build_confound_matrix_for_subject

    mf = tmp_path / "rp_test.txt"
    mf.write_text("\n".join(["0 0 0 0 0 0", "0 0 0 0 0 0", "0 0 0 0 0 0"]), encoding="utf-8")
    r_cm = build_confound_matrix_for_subject(
        subject_id=sid, motion_parameter_file=str(mf), output_dir=str(d), model="friston24"
    )
    assert r_cm["ok"] is True
    assert r_cm["qc"]["columns"] == 26

    # Test group summary
    rpt = tmp_path / "reports"
    (rpt / "rsfmri" / "group_summary").mkdir(parents=True)
    (rpt / "rsfmri" / "group_summary" / "dataset_summary.json").write_text(
        json.dumps({"ok": True, "subjects_total": 1, "stage_status_counts": {}}), encoding="utf-8"
    )
    from src.backend.app.tools.group_dataset_summary import build_group_dataset_summary

    r_gs = build_group_dataset_summary(
        derivatives_dir=str(d), reports_dir=str(rpt), work_dir=str(tmp_path / "work")
    )
    assert r_gs["ok"] is True
