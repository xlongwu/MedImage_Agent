from __future__ import annotations
from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import write_json_artifact

def write_dpabi_alff_falff_contract(work_dir: str = "./work") -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    path = out_dir / "alff_falff_backend_contract.json"
    payload = {
        "ok": True, "node_id": "dpabi_alff_falff_contract", "backend": "python",
        "backend_id": "dpabi_alff_falff", "status": "CONTRACT_ONLY",
        "execution_allowed": False, "required_approval": True,
        "description": "DPABI ALFF/fALFF backend contract. This step does not execute DPABI.",
        "planned_inputs": ["outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii", "outputs/derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii"],
        "planned_outputs": ["outputs/derivatives/rsfmri_metrics/{subject_id}/dpabi_alff.nii", "outputs/derivatives/rsfmri_metrics/{subject_id}/dpabi_falff.nii", "outputs/logs/{subject_id}_dpabi_alff_falff.log"],
        "parameters": {"low_hz": 0.01, "high_hz": 0.08, "tr_source": "temporal_filtering_qc_or_user_parameter"},
        "blocked_functions": ["DPARSF_run", "DPARSFA_run"],
        "allowed_future_mode": "single_function_wrapper_only",
        "safety": {"dpabi_executed": False, "dparsf_run_executed": False, "dparsfa_run_executed": False, "dpabi_gui_called": False, "rawdata_modified": False, "files_deleted": False},
        "outputs": [str(path)],
        "warnings": ["Contract only. DPABI ALFF/fALFF execution not implemented in Step 44."],
        "errors": [],
    }
    write_json_artifact(path, payload)
    return payload
