from __future__ import annotations
from typing import Any
from src.backend.app.tools.reho import run_python_reho_subject
from src.backend.app.tools.gpu_reho_contract import write_reho_gpu_candidate_contract
from src.backend.app.tools.dpabi_reho_contract import write_dpabi_reho_contract

def run_reho_subject(subject_id: str, derivatives_dir: str, backend: str = "python", neighborhood: int = 27, use_gm_mask: bool = False) -> dict[str, Any]:
    if backend == "gpu_contract": c = write_reho_gpu_candidate_contract(); c["subject_id"] = subject_id; return c
    if backend == "dpabi_contract": c = write_dpabi_reho_contract(); c["subject_id"] = subject_id; return c
    if backend != "python": return {"ok": False, "node_id": "reho_subject", "backend": backend, "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"Unsupported backend: {backend}"]}
    r = run_python_reho_subject(subject_id=subject_id, derivatives_dir=derivatives_dir, neighborhood=neighborhood, use_gm_mask=use_gm_mask)
    r["node_id"] = "reho_subject"; return r
