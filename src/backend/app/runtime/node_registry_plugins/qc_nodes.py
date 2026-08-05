"""Qc Nodes registry plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.schemas.pipeline_schema import PipelineNode
from src.backend.app.tools.alff_falff import write_alff_falff_dataset_report
from src.backend.app.tools.functional_connectivity import (
    write_functional_connectivity_dataset_report,
)
from src.backend.app.tools.motion_qc import (
    compute_motion_qc_for_subject,
    write_motion_qc_dataset_report,
)
from src.backend.app.tools.normalization_qc import write_normalization_qc_dataset_report
from src.backend.app.tools.nuisance_regression import write_nuisance_regression_dataset_report
from src.backend.app.tools.qc_metrics import compute_subject_qc
from src.backend.app.tools.registration_qc import write_registration_qc_dataset_report
from src.backend.app.tools.reho import write_reho_dataset_report
from src.backend.app.tools.rsfmri_chain_report import write_st_realign_motion_chain_report
from src.backend.app.tools.slice_timing_qc import write_slice_timing_dataset_report
from src.backend.app.tools.smoothing_qc import write_smoothing_qc_dataset_report
from src.backend.app.tools.temporal_filtering import write_temporal_filtering_dataset_report
from src.backend.app.tools.tissue_qc import write_tissue_qc_dataset_report


def run_subject_qc_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if subject_id is None:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "errors": ["subject_qc requires subject_id"],
        }

    # Find the smoothed output for this subject
    smoothed_path = (
        Path(context.derivatives_dir)
        / "spm_smooth"
        / subject_id
        / "func"
        / f"{subject_id}_task-rest_bold_smoothed.nii"
    )

    if not smoothed_path.exists():
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "subject_id": subject_id,
            "errors": [f"Smoothed output not found for QC: {smoothed_path}"],
        }

    qc_output_dir = node.params.get("qc_output_dir", f"{context.derivatives_dir}/qc")
    return compute_subject_qc(
        subject_id=subject_id,
        input_nii=str(smoothed_path),
        output_dir=qc_output_dir,
    )


def run_motion_qc_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "outputs": [],
            "errors": ["Missing subject_id in context."],
        }

    motion_file = (
        Path(context.derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"rp_{subject_id}_bold.txt"
    )

    result = compute_motion_qc_for_subject(
        subject_id=subject_id,
        motion_parameter_file=str(motion_file),
        derivatives_dir=context.derivatives_dir,
        fd_threshold=float(node.params.get("fd_threshold", 0.5)),
        head_radius_mm=float(node.params.get("head_radius_mm", 50.0)),
    )

    result["node_id"] = node.id
    return result


def run_motion_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_motion_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_slice_timing_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_slice_timing_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_st_realign_motion_chain_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_st_realign_motion_chain_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_registration_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_registration_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_tissue_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_tissue_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_normalization_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_normalization_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_smoothing_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_smoothing_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_nuisance_regression_qc_dataset_report_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    result = write_nuisance_regression_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_temporal_filtering_qc_dataset_report_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    result = write_temporal_filtering_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_alff_falff_qc_dataset_report_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    r = write_alff_falff_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    r["node_id"] = node.id
    return r


def run_reho_qc_dataset_report_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    r = write_reho_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    r["node_id"] = node.id
    return r


def run_functional_connectivity_qc_dataset_report_node(context, node):
    """Write dataset-level FC QC report."""
    result = write_functional_connectivity_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


REGISTRY: dict[str, NodeRunner] = {
    "subject_qc": run_subject_qc_node,
    "motion_qc_subject": run_motion_qc_subject_node,
    "motion_qc_dataset_report": run_motion_qc_dataset_report_node,
    "slice_timing_qc_dataset_report": run_slice_timing_qc_dataset_report_node,
    "st_realign_motion_chain_report": run_st_realign_motion_chain_report_node,
    "registration_qc_dataset_report": run_registration_qc_dataset_report_node,
    "tissue_qc_dataset_report": run_tissue_qc_dataset_report_node,
    "normalization_qc_dataset_report": run_normalization_qc_dataset_report_node,
    "smoothing_qc_dataset_report": run_smoothing_qc_dataset_report_node,
    "nuisance_regression_qc_dataset_report": run_nuisance_regression_qc_dataset_report_node,
    "temporal_filtering_qc_dataset_report": run_temporal_filtering_qc_dataset_report_node,
    "alff_falff_qc_dataset_report": run_alff_falff_qc_dataset_report_node,
    "reho_qc_dataset_report": run_reho_qc_dataset_report_node,
    "functional_connectivity_qc_dataset_report": run_functional_connectivity_qc_dataset_report_node,
}
