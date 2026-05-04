from __future__ import annotations
import json; from pathlib import Path
import nibabel as nib; import numpy as np
from backend.app.tools.functional_connectivity import run_python_functional_connectivity_subject

def test_python_fc_outputs_matrices(tmp_path: Path):
    d = tmp_path / "derivatives"; sid = "sub-001"
    fd = d / "rsfmri_preproc" / sid / "func"; fd.mkdir(parents=True)
    ip = fd / "filt_resid_swrasub-001_bold.nii"
    nt = 12; t = np.linspace(0, 2*np.pi, nt, dtype=np.float32)
    data = np.zeros((4,4,4,nt), dtype=np.float32)
    data[0:1,:,:,:] = np.sin(t); data[1:2,:,:,:] = np.sin(t); data[2:3,:,:,:] = np.cos(t); data[3:4,:,:,:] = -np.sin(t)
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(ip))
    r = run_python_functional_connectivity_subject(subject_id=sid, derivatives_dir=str(d), roi_count=4, generate_seed_map=True)
    assert r["ok"] is True
    fcd = d / "rsfmri_fc" / sid
    assert (fcd / "roi_timeseries.tsv").exists(); assert (fcd / "correlation_matrix.tsv").exists()
    assert (fcd / "fisher_z_matrix.tsv").exists(); assert (fcd / "seed_correlation_map.nii").exists()
    qp = d / "rsfmri_qc" / sid / "functional_connectivity_qc.json"; assert qp.exists()
    pl = json.loads(qp.read_text(encoding="utf-8"))
    assert pl["subject_id"] == sid; assert pl["fc_qc_status"] in {"PASS","WARNING"}
    assert pl["roi_count"] == 4; assert pl["correlation_matrix_shape"] == [4,4]
