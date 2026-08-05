from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from src.backend.app.tools.temporal_filtering import run_python_temporal_filter_subject


def test_python_temporal_filter_outputs_filtered_nifti(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    qc_dir = derivatives / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True)
    qc_dir.mkdir(parents=True)
    input_nii = func_dir / "resid_swrasub-001_bold.nii"
    tr = 2.0
    n_time = 32
    t = np.arange(n_time) * tr
    signal = (np.sin(2 * np.pi * 0.03 * t) + 0.5 * np.sin(2 * np.pi * 0.2 * t)).astype(np.float32)
    data = np.zeros((3, 3, 3, n_time), dtype=np.float32)
    data[:] = signal
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))
    (qc_dir / "slice_timing_qc.json").write_text(
        json.dumps({"ok": True, "subject_id": subject_id, "tr": tr, "slice_timing_status": "PASS"}),
        encoding="utf-8",
    )
    result = run_python_temporal_filter_subject(
        subject_id=subject_id, derivatives_dir=str(derivatives), low_hz=0.01, high_hz=0.08
    )
    assert result["ok"] is True
    assert (func_dir / "filt_resid_swrasub-001_bold.nii").exists()
    qc_path = qc_dir / "temporal_filtering_qc.json"
    assert qc_path.exists()
    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == subject_id
    assert payload["filtering_qc_status"] in {"PASS", "WARNING"}
    assert payload["tr"] == tr
    assert payload["retained_frequency_bin_count"] > 0


def test_python_temporal_filter_reads_tr_from_bids_sidecar(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    func_dir.mkdir(parents=True)
    input_nii = func_dir / "resid_rsub-001_task-rest_bold.nii.gz"
    tr = 1.5
    n_time = 36
    t = np.arange(n_time) * tr
    signal = np.sin(2 * np.pi * 0.04 * t).astype(np.float32)
    data = np.zeros((3, 3, 3, n_time), dtype=np.float32)
    data[:] = signal
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))
    (func_dir / "sub-001_task-rest_bold.json").write_text(
        json.dumps({"RepetitionTime": tr, "TaskName": "rest"}),
        encoding="utf-8",
    )

    result = run_python_temporal_filter_subject(
        subject_id=subject_id, derivatives_dir=str(derivatives)
    )

    assert result["ok"] is True, result["errors"]
    payload = json.loads(
        (derivatives / "rsfmri_qc" / subject_id / "temporal_filtering_qc.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["tr"] == tr
    assert payload["tr_source"].endswith("sub-001_task-rest_bold.json")


def test_python_temporal_filter_blocks_missing_tr(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    func_dir.mkdir(parents=True)
    input_nii = func_dir / "resid_rsub-001_bold.nii"
    nib.save(
        nib.Nifti1Image(np.zeros((3, 3, 3, 10), dtype=np.float32), affine=np.eye(4)), str(input_nii)
    )

    result = run_python_temporal_filter_subject(
        subject_id=subject_id, derivatives_dir=str(derivatives)
    )

    assert result["ok"] is False
    assert "tr is missing" in " ".join(result["errors"]).lower()
