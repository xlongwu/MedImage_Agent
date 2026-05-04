from __future__ import annotations
import json
from pathlib import Path
import nibabel as nib; import numpy as np
from src.backend.app.tools.reho import run_python_reho_subject

def test_python_reho_outputs_metric_map(tmp_path: Path):
    d = tmp_path / "derivatives"; sid = "sub-001"
    fd = d / "rsfmri_preproc" / sid / "func"; fd.mkdir(parents=True)
    ip = fd / "filt_resid_swrasub-001_bold.nii"
    nt = 8; base = np.linspace(0, 1, nt, dtype=np.float32)
    data = np.zeros((5,5,5,nt), dtype=np.float32)
    for x in range(1,4):
        for y in range(1,4):
            for z in range(1,4): data[x,y,z,:] = base
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(ip))
    result = run_python_reho_subject(subject_id=sid, derivatives_dir=str(d), neighborhood=27, use_gm_mask=False)
    assert result["ok"] is True
    assert (d / "rsfmri_metrics" / sid / "reho.nii").exists()
    qp = d / "rsfmri_qc" / sid / "reho_qc.json"; assert qp.exists()
    pl = json.loads(qp.read_text(encoding="utf-8"))
    assert pl["subject_id"] == sid; assert pl["reho_qc_status"] in {"PASS","WARNING"}
    assert pl["valid_voxel_count"] > 0; assert 0 <= pl["reho_mean"] <= 1
