from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.app.runtime.node_registry import NodeExecutionContext

from src.backend.app.tools.gpu_functional_connectivity_runner import run_functional_connectivity_subject


def gpu_functional_connectivity_subject_node(
    context: "NodeExecutionContext",
    node: Any,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id:
        return {
            "ok": False, "node_id": node.id, "backend": "python-gpu",
            "outputs": [], "errors": ["Missing subject_id in context."],
        }

    # Resolve input from filtered residual
    proc_dir = Path(context.derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    input_nii = None
    if proc_dir.exists():
        candidates = sorted(proc_dir.glob("filt_resid_swr*.nii"))
        if not candidates:
            candidates = sorted(proc_dir.glob("filt_resid_*.nii"))
        if candidates:
            input_nii = str(candidates[0])

    if not input_nii:
        return {
            "ok": False, "node_id": node.id, "backend": "python-gpu",
            "subject_id": subject_id, "outputs": [],
            "errors": [f"No filtered functional input found for subject {subject_id}."],
        }

    gpu_config = context.project_config.get("gpu", {})
    prefer_gpu = bool(gpu_config.get("prefer_gpu", True))
    require_gpu = bool(gpu_config.get("require_gpu", False))
    benchmark = bool(gpu_config.get("benchmark_compare_cpu_gpu", True))

    roi_count = int(node.params.get("roi_count", 4))
    atlas_path = node.params.get("atlas_path")
    generate_seed_map = bool(node.params.get("generate_seed_map", False))

    result = run_functional_connectivity_subject(
        subject_id=subject_id,
        input_nii=input_nii,
        derivatives_dir=context.derivatives_dir,
        roi_count=roi_count,
        atlas_path=atlas_path,
        generate_seed_map=generate_seed_map,
        prefer_gpu=prefer_gpu,
        require_gpu=require_gpu,
        benchmark_compare_cpu_gpu=benchmark,
    )
    result["node_id"] = node.id
    return result
