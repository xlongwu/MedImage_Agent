from __future__ import annotations
import csv, json
from pathlib import Path
import nibabel as nib; import numpy as np
from src.backend.app.tools.nuisance_regression import run_python_nuisance_regression_subject

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
