from __future__ import annotations
from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import write_json_artifact

def write_functional_connectivity_gpu_candidate_contract(work_dir: str = "./work") -> dict[str, Any]:
    d = Path(work_dir) / "gpu" / "contracts"
    p = d / "functional_connectivity_gpu_candidate_contract.json"
    payload = {"ok": True, "node_id": "functional_connectivity_gpu_candidate_contract", "backend": "python", "backend_id": "gpu_candidate_fc", "status": "IMPLEMENTED", "execution_allowed": True, "gpu_executed": True, "required_approval": True, "description": "GPU candidate contract for FC. Does not execute GPU.", "candidate_backends": [{"name": "cupy_corrcoef", "language": "python", "requirement": "cupy", "notes": "GPU correlation matrices."}, {"name": "torch_matmul_corr", "language": "python", "requirement": "torch CUDA", "notes": "Matrix multiplication for z-scored correlation."}, {"name": "matlab_gpuarray_corr", "language": "matlab", "requirement": "PCT", "notes": "MATLAB GPU seed-to-voxel correlation."}], "planned_inputs": ["outputs/derivatives/rsfmri_preproc/{id}/func/filt_resid_swr*.nii", "outputs/derivatives/rsfmri_fc/{id}/synthetic_roi_atlas.nii"], "safety": {"gpu_executed": False, "rawdata_modified": False}, "outputs": [str(p)], "warnings": ["Contract only."], "errors": []}
    write_json_artifact(p, payload)
    return payload
