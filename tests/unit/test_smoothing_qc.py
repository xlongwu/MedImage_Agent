from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from src.backend.app.tools.smoothing_qc import compute_smoothing_qc_for_subject


def test_smoothing_qc_computes_variance_ratio(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    input_func = tmp_path / "wrasub-001_bold.nii"
    smoothed = tmp_path / "swrasub-001_bold.nii"
    affine = np.diag([3.0, 3.0, 3.0, 1.0])
    rng = np.random.default_rng(42)
    input_data = rng.normal(0, 2, size=(6, 6, 6, 5)).astype(np.float32)
    smoothed_data = input_data * 0.5
    nib.save(nib.Nifti1Image(input_data, affine), str(input_func))
    nib.save(nib.Nifti1Image(smoothed_data, affine), str(smoothed))

    result = compute_smoothing_qc_for_subject(
        subject_id="sub-001",
        input_nii=str(input_func),
        smoothed_nii=str(smoothed),
        derivatives_dir=str(derivatives),
        fwhm=[6.0, 6.0, 6.0],
    )

    assert result["ok"] is True
    assert result["smoothing_qc_status"] == "PASS"
    assert result["frames_total"] == 5
    assert result["finite_fraction"] == 1.0
    assert result["variance_reduction_ratio"] < 1.0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "smoothing_qc.json"
    assert qc_path.exists()
    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
