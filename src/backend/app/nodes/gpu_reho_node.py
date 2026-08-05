from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.app.runtime.node_registry import NodeExecutionContext

from src.backend.app.tools.gpu_reho_runner import run_reho_subject


def gpu_reho_subject_node(
    context: NodeExecutionContext,
    node: Any,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python-gpu",
            "outputs": [],
            "errors": ["Missing subject_id in context."],
        }

    filter_dir = Path(context.derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    input_nii = None
    if filter_dir.exists():
        candidates = sorted(filter_dir.glob("filt_resid_swr*.nii"))
        if candidates:
            input_nii = str(candidates[0])

    if not input_nii:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python-gpu",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"No filtered functional input found for subject {subject_id}."],
        }

    gpu_config = context.project_config.get("gpu", {})
    prefer_gpu = bool(gpu_config.get("prefer_gpu", True))
    require_gpu = bool(gpu_config.get("require_gpu", False))
    benchmark = bool(gpu_config.get("benchmark_compare_cpu_gpu", True))

    neighborhood = int(node.params.get("neighborhood", 27))
    use_gm_mask = bool(node.params.get("use_gm_mask", False))
    gm_mask_path = node.params.get("gm_mask_path")

    result = run_reho_subject(
        subject_id=subject_id,
        input_nii=input_nii,
        derivatives_dir=context.derivatives_dir,
        neighborhood=neighborhood,
        use_gm_mask=use_gm_mask,
        gm_mask_path=gm_mask_path,
        prefer_gpu=prefer_gpu,
        require_gpu=require_gpu,
        benchmark_compare_cpu_gpu=benchmark,
    )
    result["node_id"] = node.id
    return result
