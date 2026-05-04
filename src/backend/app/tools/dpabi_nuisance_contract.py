from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def write_dpabi_nuisance_regression_contract(work_dir: str = "./work") -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "nuisance_regression_backend_contract.json"
    payload = {
        "ok": True, "node_id": "dpabi_nuisance_regression_contract", "backend": "python",
        "backend_id": "dpabi_nuisance_regression", "status": "CONTRACT_ONLY",
        "execution_allowed": False, "required_approval": True,
        "description": "DPABI nuisance regression backend contract. This step does not execute DPABI.",
        "planned_inputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/swr*.nii",
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/rp_*.txt",
            "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/c1*.nii",
            "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/c2*.nii",
            "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/c3*.nii"
        ],
        "planned_outputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/dpabi_regressed_swr*.nii",
            "outputs/logs/{subject_id}_dpabi_nuisance_regression.log"
        ],
        "blocked_functions": ["DPARSF_run", "DPARSFA_run"],
        "allowed_future_mode": "single_function_wrapper_only",
        "safety": {"dpabi_executed": False, "dparsf_run_executed": False, "dparsfa_run_executed": False, "dpabi_gui_called": False, "rawdata_modified": False, "files_deleted": False},
        "outputs": [str(path)],
        "warnings": ["This is a contract only. DPABI nuisance regression execution is intentionally not implemented in Step 42."],
        "errors": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
