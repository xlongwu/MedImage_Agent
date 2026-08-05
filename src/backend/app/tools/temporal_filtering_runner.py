from __future__ import annotations

from typing import Any

from src.backend.app.tools.dpabi_filtering_contract import write_dpabi_temporal_filtering_contract
from src.backend.app.tools.gpu_temporal_filtering_runner import (
    run_temporal_filtering_subject as run_gpu_temporal_filtering,
)
from src.backend.app.tools.temporal_filtering import run_python_temporal_filter_subject


def run_temporal_filtering_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    low_hz: float = 0.01,
    high_hz: float = 0.08,
    tr: float | None = None,
    fallback_tr: float | None = None,
    input_nii: str | None = None,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
) -> dict[str, Any]:
    if backend == "gpu":
        if not input_nii:
            return {
                "ok": False,
                "node_id": "temporal_filtering_subject",
                "backend": backend,
                "subject_id": subject_id,
                "outputs": [],
                "warnings": [],
                "errors": ["GPU backend requires input_nii."],
            }
        r = run_gpu_temporal_filtering(
            subject_id=subject_id,
            input_nii=input_nii,
            derivatives_dir=derivatives_dir,
            tr=tr or fallback_tr,
            low_hz=low_hz,
            high_hz=high_hz,
            prefer_gpu=prefer_gpu,
            require_gpu=require_gpu,
        )
        r["node_id"] = "temporal_filtering_subject"
        return r
    if backend == "dpabi_contract":
        contract = write_dpabi_temporal_filtering_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract
    if backend != "python":
        return {
            "ok": False,
            "node_id": "temporal_filtering_subject",
            "backend": backend,
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsupported temporal filtering backend: {backend}"],
        }
    result = run_python_temporal_filter_subject(
        subject_id=subject_id,
        derivatives_dir=derivatives_dir,
        low_hz=low_hz,
        high_hz=high_hz,
        tr=tr,
        fallback_tr=fallback_tr,
    )
    result["node_id"] = "temporal_filtering_subject"
    return result
