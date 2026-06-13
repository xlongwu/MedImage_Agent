"""Core Nodes registry plugin."""
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

def run_environment_check_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    output_json = f"{context.work_dir}/environment_check.json"
    return run_matlab_check(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        dpabi_dir=context.dpabi_dir,
        output_json=output_json,
        log_dir=context.log_dir,
        matlab_script_dir="./matlab",
    )


def run_create_synthetic_bids_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    output_dir = node.params.get("output_dir", "./examples/synthetic_bids/rawdata")
    subjects = node.params.get("subjects")
    result = create_synthetic_bids_dataset(
        output_dir=output_dir,
        subjects=subjects,
    )
    result["node_id"] = node.id
    result["backend"] = "python"
    return result


def run_data_inspection_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    rawdata_dir = node.params.get("rawdata_dir")
    output_dir = node.params.get("output_dir", f"{context.work_dir}/dataset_index")
    read_nifti_metadata = bool(node.params.get("read_nifti_metadata", True))

    if not rawdata_dir:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "outputs": [],
            "errors": ["Missing required param: rawdata_dir"],
        }

    result = inspect_dataset(
        rawdata_dir=rawdata_dir,
        output_dir=output_dir,
        read_nifti_metadata=read_nifti_metadata,
    )
    result["node_id"] = node.id
    result["backend"] = "python"
    return result


def run_dataset_evaluation_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    dataset_index_path = node.params.get("dataset_index")
    report_dir = node.params.get("report_dir", "./reports")

    result = evaluate_dataset(
        run_id=context.run_id,
        work_dir=context.work_dir,
        derivatives_dir=context.derivatives_dir,
        report_dir=report_dir,
        dataset_index_path=dataset_index_path,
    )
    result["node_id"] = node.id
    result["backend"] = "python"

    # Generate reports if evaluation succeeded
    if result.get("ok") and result.get("outputs"):
        try:
            summary_path = None
            qc_table_path = None
            exclusion_path = None
            for output in result["outputs"]:
                if "dataset_summary.json" in output:
                    summary_path = output
                elif "subject_qc_table.csv" in output:
                    qc_table_path = output
                elif "exclusion_recommendations.csv" in output:
                    exclusion_path = output

            if summary_path and qc_table_path and exclusion_path:
                report_result = write_dataset_evaluation_report(
                    dataset_summary_path=summary_path,
                    subject_qc_table_path=qc_table_path,
                    exclusion_recommendations_path=exclusion_path,
                    output_dir=f"{report_dir}/dataset_evaluation",
                )
                if report_result.get("ok"):
                    result["outputs"].extend(report_result.get("outputs", []))
        except Exception as e:
            result["warnings"] = result.get("warnings", []) + [f"Report generation warning: {e}"]

    return result


REGISTRY: dict[str, NodeRunner] = {
    "environment_check": run_environment_check_node,
    "create_synthetic_bids": run_create_synthetic_bids_node,
    "data_inspection": run_data_inspection_node,
    "dataset_evaluation": run_dataset_evaluation_node,
    "contract_smoke": run_contract_smoke_node,
}
