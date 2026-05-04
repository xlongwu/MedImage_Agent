from __future__ import annotations
import json
from pathlib import Path
from typing import Any
def write_reho_gpu_candidate_contract(work_dir: str = "./work") -> dict[str, Any]:
    out_dir = Path(work_dir) / "gpu" / "contracts"; out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "reho_gpu_candidate_contract.json"
    payload = {"ok": True, "node_id": "reho_gpu_candidate_contract", "backend": "python", "backend_id": "gpu_candidate_reho", "status": "CONTRACT_ONLY", "execution_allowed": False, "gpu_executed": False, "required_approval": True, "description": "GPU candidate contract for ReHo. Does not execute GPU.", "candidate_backends": [{"name": "cupy_rank_kcc", "language": "python", "requirement": "cupy", "notes": "CuPy for neighborhood extraction and batched KCC."}, {"name": "torch_unfold_rank", "language": "python", "requirement": "torch CUDA", "notes": "Torch unfold-style neighborhood + GPU ranking."}, {"name": "matlab_gpuarray_reho", "language": "matlab", "requirement": "PCT", "notes": "MATLAB GPU for ReHo KCC."}], "planned_inputs": ["outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii"], "planned_outputs": ["outputs/derivatives/rsfmri_metrics/{subject_id}/reho_gpu.nii"], "parallelization_notes": ["Voxel neighborhoods are embarrassingly parallel.", "Rank per timepoint/neighborhood is bottleneck.", "Chunking over z-slices recommended."], "safety": {"gpu_executed": False, "rawdata_modified": False, "files_deleted": False}, "outputs": [str(path)], "warnings": ["Contract only. GPU execution not implemented in Step 45."], "errors": []}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
