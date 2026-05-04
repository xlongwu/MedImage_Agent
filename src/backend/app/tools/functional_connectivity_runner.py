from __future__ import annotations
from typing import Any
from src.backend.app.tools.functional_connectivity import run_python_functional_connectivity_subject
from src.backend.app.tools.gpu_fc_contract import write_functional_connectivity_gpu_candidate_contract
from src.backend.app.tools.dpabi_fc_contract import write_dpabi_functional_connectivity_contract

def run_functional_connectivity_subject(subject_id: str, derivatives_dir: str, backend: str = "python", roi_count: int = 4, atlas_path: str | None = None, generate_seed_map: bool = False) -> dict[str, Any]:
    if backend == "gpu_contract": c = write_functional_connectivity_gpu_candidate_contract(); c["subject_id"] = subject_id; return c
    if backend == "dpabi_contract": c = write_dpabi_functional_connectivity_contract(); c["subject_id"] = subject_id; return c
    if backend != "python": return {"ok": False, "node_id": "functional_connectivity_subject", "backend": backend, "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"Unsupported: {backend}"]}
    r = run_python_functional_connectivity_subject(subject_id=subject_id, derivatives_dir=derivatives_dir, roi_count=roi_count, atlas_path=atlas_path, generate_seed_map=generate_seed_map)
    r["node_id"] = "functional_connectivity_subject"; return r
