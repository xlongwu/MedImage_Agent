from __future__ import annotations
from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import write_json_artifact

def write_dpabi_reho_contract(work_dir: str = "./work") -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    path = out_dir / "reho_backend_contract.json"
    payload = {"ok": True, "node_id": "dpabi_reho_contract", "backend": "python", "backend_id": "dpabi_reho", "status": "CONTRACT_ONLY", "execution_allowed": False, "required_approval": True, "description": "DPABI ReHo contract. Does not execute DPABI.", "planned_inputs": ["outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii"], "planned_outputs": ["outputs/derivatives/rsfmri_metrics/{subject_id}/dpabi_reho.nii", "outputs/logs/{subject_id}_dpabi_reho.log"], "parameters": {"neighborhood": 27}, "blocked_functions": ["DPARSF_run","DPARSFA_run"], "allowed_future_mode": "single_function_wrapper_only", "safety": {"dpabi_executed": False, "dparsf_run_executed": False, "dparsfa_run_executed": False, "dpabi_gui_called": False, "rawdata_modified": False, "files_deleted": False}, "outputs": [str(path)], "warnings": ["Contract only. DPABI ReHo execution not implemented in Step 45."], "errors": []}
    write_json_artifact(path, payload)
    return payload
