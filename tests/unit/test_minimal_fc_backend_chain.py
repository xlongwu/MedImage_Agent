from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from src.backend.app.tools.functional_connectivity import run_python_functional_connectivity_subject
from src.backend.app.tools.motion_qc import compute_motion_qc_for_subject
from src.backend.app.tools.nuisance_regression_runner import run_nuisance_regression_subject
from src.backend.app.tools.temporal_filtering import run_python_temporal_filter_subject


def test_minimal_fc_backend_chain_realigned_to_atlas_grounded_fc(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    func_dir.mkdir(parents=True)

    tr = 2.0
    n_time = 48
    t = np.arange(n_time) * tr
    data = np.zeros((4, 4, 3, n_time), dtype=np.float32)
    data[:2, :, :, :] = np.sin(2 * np.pi * 0.03 * t)
    data[2:, :, :, :] = np.cos(2 * np.pi * 0.03 * t)
    realigned_bold = func_dir / "rsub-001_task-rest_bold.nii.gz"
    nib.save(nib.Nifti1Image(data, np.eye(4)), str(realigned_bold))
    (func_dir / "sub-001_task-rest_bold.json").write_text(
        json.dumps({"RepetitionTime": tr, "TaskName": "rest"}),
        encoding="utf-8",
    )

    motion_file = func_dir / "rp_sub-001_task-rest_bold.txt"
    motion_rows = [
        f"{0.01 * idx:.6f} 0 0 0 0 0"
        for idx in range(n_time)
    ]
    motion_file.write_text("\n".join(motion_rows) + "\n", encoding="utf-8")

    motion_qc = compute_motion_qc_for_subject(
        subject_id=subject_id,
        motion_parameter_file=str(motion_file),
        derivatives_dir=str(derivatives),
    )
    assert motion_qc["ok"] is True
    assert Path(motion_qc["fd_timeseries_tsv"]).exists()

    nuisance = run_nuisance_regression_subject(
        subject_id=subject_id,
        derivatives_dir=str(derivatives),
        model="motion6",
        include_linear_trend=True,
    )
    assert nuisance["ok"] is True, nuisance["errors"]
    denoised = Path(nuisance["regression"]["output_nii"])
    assert denoised.exists()

    filtering = run_python_temporal_filter_subject(
        subject_id=subject_id,
        derivatives_dir=str(derivatives),
        low_hz=0.01,
        high_hz=0.08,
    )
    assert filtering["ok"] is True, filtering["errors"]
    filtered = Path(filtering["output_nii"])
    assert filtered.exists()

    atlas = np.zeros((4, 4, 3), dtype=np.int16)
    atlas[:2, :, :] = 1
    atlas[2:, :, :] = 2
    atlas_path = derivatives / "atlases" / "sub-001_space-native_atlas.nii.gz"
    atlas_path.parent.mkdir(parents=True)
    nib.save(nib.Nifti1Image(atlas, np.eye(4)), str(atlas_path))
    labels_path = derivatives / "atlases" / "sub-001_space-native_labels.tsv"
    labels_path.write_text("label\tname\n1\tSinROI\n2\tCosROI\n", encoding="utf-8")

    fc = run_python_functional_connectivity_subject(
        subject_id=subject_id,
        derivatives_dir=str(derivatives),
        atlas_path=str(atlas_path),
        labels_path=str(labels_path),
    )
    assert fc["ok"] is True, fc["errors"]
    assert fc["stage_status"] == "succeeded"
    assert fc["atlas_grounded"] is True

    corr = np.load(fc["correlation_matrix_npy"])
    fisher_z = np.load(fc["fisher_z_matrix_npy"])
    assert corr.shape == (2, 2)
    assert np.allclose(corr, corr.T, atol=1e-6)
    assert np.allclose(np.diag(corr), 1.0, atol=1e-6)
    assert np.allclose(np.diag(fisher_z), 0.0, atol=1e-6)
    assert Path(fc["roi_timeseries_tsv"]).exists()
    assert Path(fc["provenance_json"]).exists()
