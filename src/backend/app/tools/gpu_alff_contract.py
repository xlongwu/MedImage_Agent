from __future__ import annotations
from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import write_json_artifact

def write_alff_falff_gpu_candidate_contract(work_dir: str = "./work") -> dict[str, Any]:
    out_dir = Path(work_dir) / "gpu" / "contracts"
    path = out_dir / "alff_falff_gpu_candidate_contract.json"
    payload = {
        "ok": True, "node_id": "alff_falff_gpu_candidate_contract", "backend": "python",
        "backend_id": "gpu_candidate_alff_falff", "status": "CONTRACT_ONLY",
        "execution_allowed": False, "gpu_executed": False, "required_approval": True,
        "description": "GPU candidate contract for future ALFF/fALFF acceleration. This step does not execute GPU code.",
        "candidate_backends": [
            {"name": "cupy_fft", "language": "python", "requirement": "cupy", "notes": "Potential drop-in replacement for NumPy FFT when CUDA is available."},
            {"name": "torch_fft", "language": "python", "requirement": "torch with CUDA", "notes": "Potential backend for batched voxel-wise FFT."},
            {"name": "matlab_gpuarray_fft", "language": "matlab", "requirement": "Parallel Computing Toolbox", "notes": "Potential MATLAB GPU backend for FFT-based metrics."}
        ],
        "planned_inputs": ["outputs/derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii", "outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii"],
        "planned_outputs": ["outputs/derivatives/rsfmri_metrics/{subject_id}/alff_gpu.nii", "outputs/derivatives/rsfmri_metrics/{subject_id}/falff_gpu.nii"],
        "safety": {"gpu_executed": False, "rawdata_modified": False, "files_deleted": False},
        "outputs": [str(path)],
        "warnings": ["Contract only. GPU execution not implemented in Step 44."],
        "errors": [],
    }
    write_json_artifact(path, payload)
    return payload
