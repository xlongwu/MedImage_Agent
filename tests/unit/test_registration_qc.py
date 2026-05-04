from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from src.backend.app.tools.registration_qc import compute_registration_qc_for_subject


def test_registration_qc_computes_header_metrics(tmp_path: Path):
    derivatives = tmp_path / "derivatives"

    ref = tmp_path / "mean_func.nii"
    src = tmp_path / "sub-001_T1w.nii"
    coreg = tmp_path / "coreg_sub-001_T1w.nii"

    data_ref = np.zeros((4, 4, 4), dtype=np.float32)
    data_src = np.zeros((8, 8, 8), dtype=np.float32)

    ref_affine = np.eye(4)
    src_affine = np.eye(4)
    coreg_affine = np.eye(4)
    coreg_affine[:3, 3] = [1, 2, 3]

    nib.save(nib.Nifti1Image(data_ref, ref_affine), str(ref))
    nib.save(nib.Nifti1Image(data_src, src_affine), str(src))
    nib.save(nib.Nifti1Image(data_src, coreg_affine), str(coreg))

    result = compute_registration_qc_for_subject(
        subject_id="sub-001",
        reference_nii=str(ref),
        source_nii=str(src),
        coregistered_nii=str(coreg),
        derivatives_dir=str(derivatives),
        center_distance_warning_mm=100.0,
    )

    assert result["ok"] is True
    assert result["registration_qc_status"] == "PASS"
    assert result["affine_translation_distance_mm"] > 0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "registration_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
