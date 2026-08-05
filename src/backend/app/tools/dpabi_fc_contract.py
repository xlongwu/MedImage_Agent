from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import write_json_artifact


def write_dpabi_functional_connectivity_contract(work_dir: str = "./work") -> dict[str, Any]:
    d = Path(work_dir) / "dpabi" / "contracts"
    p = d / "functional_connectivity_backend_contract.json"
    payload = {"ok": True, "node_id": "dpabi_functional_connectivity_contract", "backend": "python", "backend_id": "dpabi_fc", "status": "CONTRACT_ONLY", "execution_allowed": False, "required_approval": True, "description": "DPABI FC contract. Does not execute DPABI.", "planned_inputs": ["outputs/derivatives/rsfmri_preproc/{id}/func/filt_resid_swr*.nii", "outputs/derivatives/rsfmri_fc/{id}/synthetic_roi_atlas.nii"], "blocked_functions": ["DPARSF_run","DPARSFA_run"], "allowed_future_mode": "single_function_wrapper_only", "safety": {"dpabi_executed": False, "dparsf_run_executed": False, "dparsfa_run_executed": False, "rawdata_modified": False}, "outputs": [str(p)], "warnings": ["Contract only."], "errors": []}
    write_json_artifact(p, payload)
    return payload
