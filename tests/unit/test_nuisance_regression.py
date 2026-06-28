from __future__ import annotations
import csv, json
from pathlib import Path
import nibabel as nib; import numpy as np
from src.backend.app.tools.nuisance_regression import run_python_nuisance_regression_subject
from src.backend.app.tools.nuisance_regression_runner import run_nuisance_regression_subject

def test_python_nuisance_regression_outputs_residual_nifti(tmp_path: Path):
    derivatives = tmp_path / "derivatives"; subject_id = "sub-001"
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"; func_dir.mkdir(parents=True)
    input_nii = func_dir / "swrasub-001_bold.nii"; confounds = tmp_path / "confounds.tsv"
    rng = np.random.default_rng(42)
    data = rng.normal(size=(4,4,4,6)).astype(np.float32)
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))
    with confounds.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t"); w.writerow(["intercept","linear_trend"])
        for i in range(6): w.writerow([1.0, -1.0 + 2.0 * i / 5.0])
    result = run_python_nuisance_regression_subject(subject_id=subject_id, input_nii=str(input_nii), confounds_tsv=str(confounds), derivatives_dir=str(derivatives))
    assert result["ok"] is True
    assert (func_dir / "resid_swrasub-001_bold.nii").exists()
    qc_path = derivatives / "rsfmri_qc" / subject_id / "nuisance_regression_qc.json"
    assert qc_path.exists()
    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == subject_id
    assert payload["regression_qc_status"] in {"PASS", "WARNING"}


def test_nuisance_runner_accepts_realigned_bold_and_motion_params(tmp_path: Path):
    derivatives = tmp_path / "derivatives"; subject_id = "sub-001"
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"; func_dir.mkdir(parents=True)
    input_nii = func_dir / "rsub-001_bold.nii"
    rng = np.random.default_rng(8)
    data = rng.normal(size=(3,3,3,8)).astype(np.float32)
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))
    motion = func_dir / "rp_sub-001_bold.txt"
    motion.write_text("\n".join(["0 0 0 0 0 0"] * 8), encoding="utf-8")

    result = run_nuisance_regression_subject(subject_id=subject_id, derivatives_dir=str(derivatives))

    assert result["ok"] is True, result["errors"]
    assert result["input_nii"].endswith("rsub-001_bold.nii")
    assert (func_dir / "resid_rsub-001_bold.nii").exists()
    assert "linear_trend" in result["confounds"]["qc"]["column_names"]


def test_nuisance_runner_blocks_without_motion_params(tmp_path: Path):
    derivatives = tmp_path / "derivatives"; subject_id = "sub-001"
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"; func_dir.mkdir(parents=True)
    nib.save(
        nib.Nifti1Image(np.zeros((3,3,3,5), dtype=np.float32), affine=np.eye(4)),
        str(func_dir / "rsub-001_bold.nii"),
    )

    result = run_nuisance_regression_subject(subject_id=subject_id, derivatives_dir=str(derivatives))

    assert result["ok"] is False
    assert "motion parameter" in " ".join(result["errors"]).lower()
