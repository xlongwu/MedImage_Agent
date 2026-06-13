"""Gpu Nodes registry plugin."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.schemas.pipeline_schema import PipelineNode
from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.tools.data_inspector import inspect_dataset
from src.backend.app.tools.dataset_evaluator import evaluate_dataset
from src.backend.app.tools.matlab_runner import run_matlab_check
from src.backend.app.tools.qc_metrics import compute_subject_qc
from src.backend.app.tools.report_writer import write_dataset_evaluation_report
from src.backend.app.tools.spm_runner import run_spm_smoke_test
from src.backend.app.tools.spm_subject_runner import run_spm_smooth_subject
from src.backend.app.tools.synthetic_bids import create_synthetic_bids_dataset
from src.backend.app.nodes.gpu_alff_node import gpu_alff_subject_node
from src.backend.app.nodes.gpu_reho_node import gpu_reho_subject_node
from src.backend.app.nodes.gpu_nuisance_regression_node import gpu_nuisance_regression_subject_node
from src.backend.app.nodes.gpu_temporal_filtering_node import gpu_temporal_filtering_subject_node
from src.backend.app.nodes.gpu_functional_connectivity_node import gpu_functional_connectivity_subject_node
from src.backend.app.tools.dpabi_runner import run_dpabi_capability_inspection
from src.backend.app.tools.dpabi_config import write_dpabi_wrapper_scaffold
from src.backend.app.tools.dpabi_adapter import build_dpabi_input_manifest
from src.backend.app.tools.dpabi_preflight import run_dpabi_preflight
from src.backend.app.tools.dpabi_run_plan import create_dpabi_run_plan
from src.backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke
from src.backend.app.tools.dpabi_signature_runner import run_dpabi_signature_probe
from src.backend.app.tools.dpabi_contract_registry import write_dpabi_wrapper_contracts
from src.backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox
from src.backend.app.tools.dpabi_subject_wrapper import run_dpabi_subject_smooth
from src.backend.app.tools.dpabi_subject_wrapper_report import write_dpabi_subject_wrapper_report
from src.backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix
from src.backend.app.tools.dpabi_template_library import write_dpabi_template_library
from src.backend.app.tools.dpabi_template_instantiator import (
    instantiate_dpabi_template,
    execute_dpabi_template_instance,
)
from src.backend.app.tools.rsfmri_plan_tool import write_rsfmri_preprocessing_plan
from src.backend.app.tools.spm_realign_runner import run_spm_realign_subject
from src.backend.app.tools.motion_qc import (
    compute_motion_qc_for_subject,
    write_motion_qc_dataset_report,
)
from src.backend.app.tools.spm_slice_timing_runner import run_spm_slice_timing_subject
from src.backend.app.tools.slice_timing_qc import write_slice_timing_dataset_report
from src.backend.app.tools.rsfmri_chain_resolver import resolve_realign_input
from src.backend.app.tools.rsfmri_chain_report import write_st_realign_motion_chain_report
from src.backend.app.tools.spm_coregister_runner import run_spm_coregister_subject
from src.backend.app.tools.registration_qc import write_registration_qc_dataset_report
from src.backend.app.tools.spm_segment_runner import run_spm_segment_subject
from src.backend.app.tools.tissue_qc import write_tissue_qc_dataset_report
from src.backend.app.tools.spm_normalize_runner import run_spm_normalize_subject
from src.backend.app.tools.normalization_qc import write_normalization_qc_dataset_report
from src.backend.app.tools.spm_smooth_runner import run_spm_smooth_subject
from src.backend.app.tools.smoothing_qc import write_smoothing_qc_dataset_report
from src.backend.app.tools.nuisance_regression_runner import run_nuisance_regression_subject
from src.backend.app.tools.nuisance_regression import write_nuisance_regression_dataset_report
from src.backend.app.tools.dpabi_nuisance_contract import write_dpabi_nuisance_regression_contract
from src.backend.app.tools.temporal_filtering_runner import run_temporal_filtering_subject
from src.backend.app.tools.temporal_filtering import write_temporal_filtering_dataset_report
from src.backend.app.tools.dpabi_filtering_contract import write_dpabi_temporal_filtering_contract
from src.backend.app.tools.alff_falff_runner import run_alff_falff_subject
from src.backend.app.tools.alff_falff import write_alff_falff_dataset_report
from src.backend.app.tools.gpu_alff_contract import write_alff_falff_gpu_candidate_contract
from src.backend.app.tools.dpabi_alff_contract import write_dpabi_alff_falff_contract
from src.backend.app.tools.reho_runner import run_reho_subject
from src.backend.app.tools.reho import write_reho_dataset_report
from src.backend.app.tools.gpu_reho_contract import write_reho_gpu_candidate_contract
from src.backend.app.tools.dpabi_reho_contract import write_dpabi_reho_contract
from src.backend.app.tools.functional_connectivity_runner import run_functional_connectivity_subject
from src.backend.app.tools.functional_connectivity import write_functional_connectivity_dataset_report
from src.backend.app.tools.gpu_fc_contract import write_functional_connectivity_gpu_candidate_contract
from src.backend.app.tools.dpabi_fc_contract import write_dpabi_functional_connectivity_contract
from src.backend.app.tools.group_dataset_summary import build_group_dataset_summary
from src.backend.app.tools.report_exporter import export_rsfmri_report_package
from src.backend.app.tools.report_package_validator import validate_rsfmri_report_package
from src.backend.app.tools.release_readiness import build_release_readiness
from src.backend.app.tools.docs_inventory import build_docs_inventory
from src.backend.app.tools.node_contract_smoke import run_contract_smoke_node

def run_alff_falff_gpu_candidate_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_alff_falff_gpu_candidate_contract(work_dir=context.work_dir); r["node_id"] = node.id; return r


def run_reho_gpu_candidate_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_reho_gpu_candidate_contract(work_dir=context.work_dir); r["node_id"] = node.id; return r


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
    from src.backend.app.tools.gpu_temporal_filtering_runner import run_gpu_temporal_filtering_subject
    p = node.params
    result = run_gpu_temporal_filtering_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        derivatives_dir=context.derivatives_dir, run_id=context.run_id,
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
    from src.backend.app.tools.gpu_functional_connectivity_runner import run_gpu_functional_connectivity_subject
    p = node.params
    result = run_gpu_functional_connectivity_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        derivatives_dir=context.derivatives_dir, run_id=context.run_id,
        atlas_source=p.get("atlas_source", "approved_builtin_atlas"),
        roi_count=p.get("roi_count"), timepoints=p.get("timepoints"),
        correlation_method=p.get("correlation_method", "pearson"),
        fisher_z=bool(p.get("fisher_z", True)),
        device=p.get("device", "auto"),
        timeout_seconds=int(p.get("timeout_seconds", 60)),
        approved=True,
    )
    result["node_id"] = node.id
    return result


def run_gpu_nuisance_regression_subject_node(context, node):
    from src.backend.app.tools.gpu_nuisance_regression_runner import run_gpu_nuisance_regression_subject
    p = node.params
    result = run_gpu_nuisance_regression_subject(
        subject_id=p.get("subject_id", "sub-001"),
        input_functional=p.get("input_functional", f"{context.derivatives_dir}/func.nii"),
        confounds_path=p.get("confounds_path", f"{context.derivatives_dir}/confounds.tsv"),
        derivatives_dir=context.derivatives_dir, run_id=context.run_id,
        confound_columns=p.get("confound_columns"),
        regression_mode=p.get("regression_mode", "ols"),
        include_intercept=bool(p.get("include_intercept", True)),
        allow_global_signal=bool(p.get("allow_global_signal", False)),
        allow_scrubbing=bool(p.get("allow_scrubbing", False)),
        n_confounds=p.get("n_confounds"), timepoints=p.get("timepoints"),
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
