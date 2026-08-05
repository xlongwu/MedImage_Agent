"""Gpu Nodes registry plugin."""

from __future__ import annotations

from typing import Any

from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.schemas.pipeline_schema import PipelineNode
from src.backend.app.tools.gpu_alff_contract import write_alff_falff_gpu_candidate_contract
from src.backend.app.tools.gpu_fc_contract import (
    write_functional_connectivity_gpu_candidate_contract,
)
from src.backend.app.tools.gpu_reho_contract import write_reho_gpu_candidate_contract


def run_alff_falff_gpu_candidate_contract_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    r = write_alff_falff_gpu_candidate_contract(work_dir=context.work_dir)
    r["node_id"] = node.id
    return r


def run_reho_gpu_candidate_contract_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    r = write_reho_gpu_candidate_contract(work_dir=context.work_dir)
    r["node_id"] = node.id
    return r


def run_functional_connectivity_gpu_candidate_contract_node(context, node):
    """Generate GPU candidate contract for FC computation."""
    result = write_functional_connectivity_gpu_candidate_contract(work_dir=context.work_dir)
    result["node_id"] = node.id
    return result


def run_gpu_synthetic_smoke_node(context, node):
    from src.backend.app.tools.gpu_smoke_runner import run_gpu_synthetic_smoke

    result = run_gpu_synthetic_smoke(
        device=node.params.get("device", "auto"),
        shape=node.params.get("shape", (64, 64)),
        dtype_bytes=node.params.get("dtype_bytes", 4),
        batch_size=node.params.get("batch_size", 1),
        timeout_seconds=node.params.get("timeout_seconds", 10),
        require_gpu=node.params.get("require_gpu", False),
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        work_dir=context.work_dir,
        run_id=context.run_id,
        approved=True,
    )
    result["node_id"] = node.id
    return result


def run_gpu_alff_subject_node(context, node):
    from src.backend.app.tools.gpu_alff_runner import run_gpu_alff_subject

    p = node.params
    result = run_gpu_alff_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        derivatives_dir=context.derivatives_dir,
        run_id=context.run_id,
        tr=float(p.get("tr", 2.0)),
        frequency_band=tuple(p.get("frequency_band", (0.01, 0.08))),
        compute_falff=bool(p.get("compute_falff", True)),
        device=p.get("device", "auto"),
        timeout_seconds=int(p.get("timeout_seconds", 60)),
        approved=True,
    )
    result["node_id"] = node.id
    return result


def run_gpu_reho_subject_node(context, node):
    from src.backend.app.tools.gpu_reho_runner import run_gpu_reho_subject

    p = node.params
    result = run_gpu_reho_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        derivatives_dir=context.derivatives_dir,
        run_id=context.run_id,
        neighborhood=int(p.get("neighborhood", 27)),
        mask_path=p.get("mask_path"),
        device=p.get("device", "auto"),
        timeout_seconds=int(p.get("timeout_seconds", 60)),
        approved=True,
    )
    result["node_id"] = node.id
    return result


def run_gpu_temporal_filtering_subject_node(context, node):
    from src.backend.app.tools.gpu_temporal_filtering_runner import (
        run_gpu_temporal_filtering_subject,
    )

    p = node.params
    result = run_gpu_temporal_filtering_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        derivatives_dir=context.derivatives_dir,
        run_id=context.run_id,
        tr=float(p.get("tr", 2.0)),
        frequency_band=tuple(p.get("frequency_band", (0.01, 0.08))),
        filter_mode=p.get("filter_mode", "bandpass"),
        filter_method=p.get("filter_method", "butterworth"),
        filter_order=int(p.get("filter_order", 2)),
        device=p.get("device", "auto"),
        timeout_seconds=int(p.get("timeout_seconds", 60)),
        approved=True,
    )
    result["node_id"] = node.id
    return result


def run_gpu_functional_connectivity_subject_node(context, node):
    from src.backend.app.tools.gpu_functional_connectivity_runner import (
        run_gpu_functional_connectivity_subject,
    )

    p = node.params
    result = run_gpu_functional_connectivity_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        derivatives_dir=context.derivatives_dir,
        run_id=context.run_id,
        atlas_source=p.get("atlas_source", "approved_builtin_atlas"),
        roi_count=p.get("roi_count"),
        timepoints=p.get("timepoints"),
        correlation_method=p.get("correlation_method", "pearson"),
        fisher_z=bool(p.get("fisher_z", True)),
        device=p.get("device", "auto"),
        timeout_seconds=int(p.get("timeout_seconds", 60)),
        approved=True,
    )
    result["node_id"] = node.id
    return result


def run_gpu_nuisance_regression_subject_node(context, node):
    from src.backend.app.tools.gpu_nuisance_regression_runner import (
        run_gpu_nuisance_regression_subject,
    )

    p = node.params
    result = run_gpu_nuisance_regression_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        confounds_path=p.get("confounds_path", f"{context.derivatives_dir}/confounds.tsv"),
        derivatives_dir=context.derivatives_dir,
        run_id=context.run_id,
        confound_columns=p.get("confound_columns"),
        regression_mode=p.get("regression_mode", "ols"),
        include_intercept=bool(p.get("include_intercept", True)),
        allow_global_signal=bool(p.get("allow_global_signal", False)),
        allow_scrubbing=bool(p.get("allow_scrubbing", False)),
        n_confounds=p.get("n_confounds"),
        timepoints=p.get("timepoints"),
        device=p.get("device", "auto"),
        timeout_seconds=int(p.get("timeout_seconds", 60)),
        approved=True,
    )
    result["node_id"] = node.id
    return result


REGISTRY: dict[str, NodeRunner] = {
    "alff_falff_gpu_candidate_contract": run_alff_falff_gpu_candidate_contract_node,
    "reho_gpu_candidate_contract": run_reho_gpu_candidate_contract_node,
    "functional_connectivity_gpu_candidate_contract": run_functional_connectivity_gpu_candidate_contract_node,
    "gpu_synthetic_smoke": run_gpu_synthetic_smoke_node,
    "gpu_alff_subject": run_gpu_alff_subject_node,
    "gpu_reho_subject": run_gpu_reho_subject_node,
    "gpu_temporal_filtering_subject": run_gpu_temporal_filtering_subject_node,
    "gpu_functional_connectivity_subject": run_gpu_functional_connectivity_subject_node,
    "gpu_nuisance_regression_subject": run_gpu_nuisance_regression_subject_node,
}
