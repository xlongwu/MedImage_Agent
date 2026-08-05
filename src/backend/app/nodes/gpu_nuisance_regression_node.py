from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.app.runtime.node_registry import NodeExecutionContext

from src.backend.app.tools.gpu_nuisance_regression_runner import run_nuisance_regression_subject


def gpu_nuisance_regression_subject_node(
    context: NodeExecutionContext,
    node: Any,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id:
        return {
            "ok": False, "node_id": node.id, "backend": "python-gpu",
            "outputs": [], "errors": ["Missing subject_id in context."],
        }

    # Resolve input from SPM smooth output
    smooth_dir = Path(context.derivatives_dir) / "spm_smooth" / subject_id / "func"
    input_nii = None
    if smooth_dir.exists():
        candidates = sorted(smooth_dir.glob("*_smooth.nii")) + sorted(smooth_dir.glob("*_smooth.nii.gz"))
        if candidates:
            input_nii = str(candidates[0])

    # Also check for already preprocessed smooth output
    if not input_nii:
        smooth_dir2 = Path(context.derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
        if smooth_dir2.exists():
            candidates = sorted(smooth_dir2.glob("swr*.nii")) + sorted(smooth_dir2.glob("swr*.nii.gz"))
            if candidates:
                input_nii = str(candidates[0])

    if not input_nii:
        return {
            "ok": False, "node_id": node.id, "backend": "python-gpu",
            "subject_id": subject_id, "outputs": [],
            "errors": [f"No smooth BOLD input found for subject {subject_id}."],
        }

    # Resolve confounds (motion parameters)
    rp_dir = Path(context.derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    confounds_tsv = None
    if rp_dir.exists():
        rp_files = sorted(rp_dir.glob("rp_*.txt"))
        if rp_files:
            confounds_tsv = str(rp_files[0])

    if not confounds_tsv:
        return {
            "ok": False, "node_id": node.id, "backend": "python-gpu",
            "subject_id": subject_id, "outputs": [],
            "errors": [f"No motion parameter file found for subject {subject_id}."],
        }

    gpu_config = context.project_config.get("gpu", {})
    prefer_gpu = bool(gpu_config.get("prefer_gpu", True))
    require_gpu = bool(gpu_config.get("require_gpu", False))
    benchmark = bool(gpu_config.get("benchmark_compare_cpu_gpu", True))

    result = run_nuisance_regression_subject(
        subject_id=subject_id,
        input_nii=input_nii,
        confounds_tsv=confounds_tsv,
        derivatives_dir=context.derivatives_dir,
        prefer_gpu=prefer_gpu,
        require_gpu=require_gpu,
        benchmark_compare_cpu_gpu=benchmark,
    )
    result["node_id"] = node.id
    return result
