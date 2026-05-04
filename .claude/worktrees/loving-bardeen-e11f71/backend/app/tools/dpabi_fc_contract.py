from __future__ import annotations
import json; from pathlib import Path; from typing import Any
def write_dpabi_functional_connectivity_contract(work_dir: str = "./work") -> dict[str, Any]:
    d = Path(work_dir) / "dpabi" / "contracts"; d.mkdir(parents=True, exist_ok=True)
    p = d / "functional_connectivity_backend_contract.json"
    payload = {"ok": True, "node_id": "dpabi_functional_connectivity_contract", "backend": "python", "backend_id": "dpabi_fc", "status": "CONTRACT_ONLY", "execution_allowed": False, "required_approval": True, "description": "DPABI FC contract. Does not execute DPABI.", "planned_inputs": ["derivatives/rsfmri_preproc/{id}/func/filt_resid_swr*.nii", "derivatives/rsfmri_fc/{id}/synthetic_roi_atlas.nii"], "blocked_functions": ["DPARSF_run","DPARSFA_run"], "allowed_future_mode": "single_function_wrapper_only", "safety": {"dpabi_executed": False, "dparsf_run_executed": False, "dparsfa_run_executed": False, "rawdata_modified": False}, "outputs": [str(p)], "warnings": ["Contract only."], "errors": []}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"); return payload
