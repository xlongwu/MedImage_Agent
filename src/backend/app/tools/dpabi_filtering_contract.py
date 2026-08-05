from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import write_json_artifact


def write_dpabi_temporal_filtering_contract(work_dir: str = "./work") -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    path = out_dir / "temporal_filtering_backend_contract.json"
    payload = {
        "ok": True, "node_id": "dpabi_temporal_filtering_contract", "backend": "python",
        "backend_id": "dpabi_temporal_filtering", "status": "CONTRACT_ONLY",
        "execution_allowed": False, "required_approval": True,
        "description": "DPABI temporal filtering backend contract. This step does not execute DPABI.",
        "planned_inputs": ["outputs/derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii", "outputs/derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json"],
        "planned_outputs": ["outputs/derivatives/rsfmri_preproc/{subject_id}/func/dpabi_filtered_resid_swr*.nii", "outputs/logs/{subject_id}_dpabi_temporal_filtering.log"],
        "parameters": {"low_hz": 0.01, "high_hz": 0.08, "tr_source": "slice_timing_qc_or_user_parameter"},
        "blocked_functions": ["DPARSF_run", "DPARSFA_run"],
        "allowed_future_mode": "single_function_wrapper_only",
        "safety": {"dpabi_executed": False, "dparsf_run_executed": False, "dparsfa_run_executed": False, "dpabi_gui_called": False, "rawdata_modified": False, "files_deleted": False},
        "outputs": [str(path)],
        "warnings": ["This is a contract only. DPABI temporal filtering execution is intentionally not implemented in Step 43."],
        "errors": [],
    }
    write_json_artifact(path, payload)
    return payload
