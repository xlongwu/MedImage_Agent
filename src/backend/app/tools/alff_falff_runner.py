from __future__ import annotations
from typing import Any
from src.backend.app.tools.alff_falff import run_python_alff_falff_subject
from src.backend.app.tools.gpu_alff_contract import write_alff_falff_gpu_candidate_contract
from src.backend.app.tools.dpabi_alff_contract import write_dpabi_alff_falff_contract

def run_alff_falff_subject(subject_id: str, derivatives_dir: str, backend: str = "python", low_hz: float | None = None, high_hz: float | None = None, tr: float | None = None, fallback_tr: float | None = None) -> dict[str, Any]:
    if backend == "gpu_contract": c = write_alff_falff_gpu_candidate_contract(); c["subject_id"] = subject_id; return c
    if backend == "dpabi_contract": c = write_dpabi_alff_falff_contract(); c["subject_id"] = subject_id; return c
    if backend != "python": return {"ok": False, "node_id": "alff_falff_subject", "backend": backend, "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"Unsupported backend: {backend}"]}
    r = run_python_alff_falff_subject(subject_id=subject_id, derivatives_dir=derivatives_dir, low_hz=low_hz, high_hz=high_hz, tr=tr, fallback_tr=fallback_tr)
    r["node_id"] = "alff_falff_subject"; return r
