from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def write_dpabi_alff_falff_contract(work_dir: str = "./work") -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"; out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "alff_falff_backend_contract.json"
    payload = {
        "ok": True, "node_id": "dpabi_alff_falff_contract", "backend": "python",
        "backend_id": "dpabi_alff_falff", "status": "CONTRACT_ONLY",
        "execution_allowed": False, "required_approval": True,
        "description": "DPABI ALFF/fALFF backend contract. This step does not execute DPABI.",
        "planned_inputs": ["derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii", "derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii"],
        "planned_outputs": ["derivatives/rsfmri_metrics/{subject_id}/dpabi_alff.nii", "derivatives/rsfmri_metrics/{subject_id}/dpabi_falff.nii", "logs/{subject_id}_dpabi_alff_falff.log"],
        "parameters": {"low_hz": 0.01, "high_hz": 0.08, "tr_source": "temporal_filtering_qc_or_user_parameter"},
        "blocked_functions": ["DPARSF_run", "DPARSFA_run"],
        "allowed_future_mode": "single_function_wrapper_only",
        "safety": {"dpabi_executed": False, "dparsf_run_executed": False, "dparsfa_run_executed": False, "dpabi_gui_called": False, "rawdata_modified": False, "files_deleted": False},
        "outputs": [str(path)],
        "warnings": ["Contract only. DPABI ALFF/fALFF execution not implemented in Step 44."],
        "errors": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
