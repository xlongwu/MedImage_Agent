from __future__ import annotations
import json
from pathlib import Path
import nibabel as nib; import numpy as np
from src.backend.app.tools.alff_falff import run_python_alff_falff_subject

def test_python_alff_falff_outputs_metric_maps(tmp_path: Path):
    derivatives = tmp_path / "derivatives"; sid = "sub-001"
    fd = derivatives / "rsfmri_preproc" / sid / "func"; qd = derivatives / "rsfmri_qc" / sid
    fd.mkdir(parents=True); qd.mkdir(parents=True)
    rp = fd / "resid_swrasub-001_bold.nii"; fp = fd / "filt_resid_swrasub-001_bold.nii"
    tr = 2.0; nt = 32; t = np.arange(nt) * tr
    rs = (np.sin(2*np.pi*0.03*t) + 0.5*np.sin(2*np.pi*0.2*t)).astype(np.float32)
    fs = np.sin(2*np.pi*0.03*t).astype(np.float32)
    rd = np.zeros((3,3,3,nt), dtype=np.float32); rd[:] = rs
    fd_data = np.zeros((3,3,3,nt), dtype=np.float32); fd_data[:] = fs
    nib.save(nib.Nifti1Image(rd, affine=np.eye(4)), str(rp))
    nib.save(nib.Nifti1Image(fd_data, affine=np.eye(4)), str(fp))
    (qd / "temporal_filtering_qc.json").write_text(json.dumps({"ok": True, "subject_id": sid, "tr": tr, "low_hz": 0.01, "high_hz": 0.08, "filtering_qc_status": "PASS"}), encoding="utf-8")
    result = run_python_alff_falff_subject(subject_id=sid, derivatives_dir=str(derivatives))
    assert result["ok"] is True
    assert (derivatives / "rsfmri_metrics" / sid / "alff.nii").exists()
    assert (derivatives / "rsfmri_metrics" / sid / "falff.nii").exists()
    qp = qd / "alff_falff_qc.json"; assert qp.exists()
    pl = json.loads(qp.read_text(encoding="utf-8"))
    assert pl["subject_id"] == sid; assert pl["alff_qc_status"] in {"PASS", "WARNING"}
    assert pl["retained_frequency_bin_count"] > 0; assert pl["falff_mean"] >= 0
