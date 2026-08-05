from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.app.runtime.node_registry import NodeExecutionContext

from src.backend.app.tools.gpu_alff_runner import run_alff_subject


def gpu_alff_subject_node(
    context: NodeExecutionContext,
    node: Any,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    subject_id = subject_id or (subject_record.get("subject_id", "unknown") if subject_record else "unknown")
    if not subject_id or subject_id == "unknown":
        return {
            "ok": False, "node_id": node.id, "backend": "python-gpu",
            "outputs": [], "errors": ["Missing subject_id in context."],
        }

    derivatives_dir = context.derivatives_dir
    spm_smooth_dir = Path(derivatives_dir) / "spm_smooth" / subject_id / "func"
    input_nii = None
    if spm_smooth_dir.exists():
        for f in spm_smooth_dir.iterdir():
            if f.name.endswith("_smooth.nii") or f.name.endswith("_smooth.nii.gz"):
                input_nii = str(f)
                break
    if not input_nii:
        return {
            "ok": False, "node_id": node.id, "backend": "python-gpu",
            "subject_id": subject_id, "outputs": [],
            "errors": [f"Smoothed BOLD not found for {subject_id}"],
        }

    gpu_config = context.project_config.get("gpu", {})
    prefer_gpu = bool(gpu_config.get("prefer_gpu", True))
    require_gpu = bool(gpu_config.get("require_gpu", False))
    benchmark_compare = bool(gpu_config.get("benchmark_compare_cpu_gpu", True))

    tr = node.params.get("tr", 2.0)
    freq_band = node.params.get("freq_band", [0.01, 0.08])

    result = run_alff_subject(
        subject_id=subject_id, input_nii=input_nii,
        derivatives_dir=derivatives_dir, tr=tr, freq_band=freq_band,
        prefer_gpu=prefer_gpu, require_gpu=require_gpu,
        benchmark_compare_cpu_gpu=benchmark_compare,
    )
    result["node_id"] = node.id
    return result
