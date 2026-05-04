from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.normalization_qc import compute_normalization_qc_for_subject


def test_normalization_qc_computes_output_metrics(tmp_path: Path):
    derivatives = tmp_path / "derivatives"

    input_func = tmp_path / "rasub-001_bold.nii"
    deformation = tmp_path / "y_coreg_sub-001_T1w.nii"
    normalized = tmp_path / "wrasub-001_bold.nii"

    affine_input = np.eye(4)
    affine_norm = np.diag([3.0, 3.0, 3.0, 1.0])

    input_data = np.ones((4, 4, 4, 5), dtype=np.float32)
    normalized_data = np.ones((6, 6, 6, 5), dtype=np.float32)

    nib.save(nib.Nifti1Image(input_data, affine_input), str(input_func))
    nib.save(nib.Nifti1Image(np.zeros((4, 4, 4, 1, 3), dtype=np.float32), affine_input), str(deformation))
    nib.save(nib.Nifti1Image(normalized_data, affine_norm), str(normalized))

    result = compute_normalization_qc_for_subject(
        subject_id="sub-001",
        input_nii=str(input_func),
        deformation_field=str(deformation),
        normalized_nii=str(normalized),
        derivatives_dir=str(derivatives),
        target_voxel_size=[3.0, 3.0, 3.0],
    )

    assert result["ok"] is True
    assert result["normalization_qc_status"] == "PASS"
    assert result["frames_total"] == 5
    assert result["finite_fraction"] == 1.0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "normalization_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
