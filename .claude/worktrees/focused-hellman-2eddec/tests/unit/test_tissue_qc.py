from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.tissue_qc import compute_tissue_qc_for_subject


def test_tissue_qc_computes_volume_metrics(tmp_path: Path):
    derivatives = tmp_path / "derivatives"

    gm = tmp_path / "c1coreg_sub-001_T1w.nii"
    wm = tmp_path / "c2coreg_sub-001_T1w.nii"
    csf = tmp_path / "c3coreg_sub-001_T1w.nii"
    deformation = tmp_path / "y_coreg_sub-001_T1w.nii"

    affine = np.eye(4)

    gm_data = np.zeros((4, 4, 4), dtype=np.float32)
    wm_data = np.zeros((4, 4, 4), dtype=np.float32)
    csf_data = np.zeros((4, 4, 4), dtype=np.float32)

    gm_data[:2, :, :] = 0.8
    wm_data[2:3, :, :] = 0.7
    csf_data[3:4, :, :] = 0.6

    nib.save(nib.Nifti1Image(gm_data, affine), str(gm))
    nib.save(nib.Nifti1Image(wm_data, affine), str(wm))
    nib.save(nib.Nifti1Image(csf_data, affine), str(csf))
    nib.save(nib.Nifti1Image(np.zeros((4, 4, 4, 1, 3), dtype=np.float32), affine), str(deformation))

    result = compute_tissue_qc_for_subject(
        subject_id="sub-001",
        gm_file=str(gm),
        wm_file=str(wm),
        csf_file=str(csf),
        deformation_field=str(deformation),
        derivatives_dir=str(derivatives),
        probability_threshold=0.2,
    )

    assert result["ok"] is True
    assert result["segmentation_qc_status"] == "PASS"
    assert result["gm_volume_mm3"] > 0
    assert result["wm_volume_mm3"] > 0
    assert result["csf_volume_mm3"] > 0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "tissue_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
