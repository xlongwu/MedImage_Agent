from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.backend.app.schemas.pipeline_schema import PipelineNode
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


@dataclass
class NodeExecutionContext:
    run_id: str
    project_config: dict[str, Any]
    work_dir: str
    log_dir: str
    matlab_command: str
    spm_dir: str
    dpabi_dir: str
    derivatives_dir: str = "./derivatives"


NodeRunner = Callable[[NodeExecutionContext, PipelineNode], dict[str, Any]]


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


def run_spm_smoke_test_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    return run_spm_smoke_test(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        work_dir=context.work_dir,
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


def run_spm_smooth_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if subject_record is None or subject_id is None:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "errors": ["spm_smooth_subject requires subject_record and subject_id"],
        }

    fwhm = node.params.get("fwhm", [4, 4, 4])
    return run_spm_smooth_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_record=subject_record,
        subject_id=subject_id,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        derivatives_dir=context.derivatives_dir,
        matlab_script_dir="./matlab",
        fwhm=fwhm,
    )


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


def run_dpabi_capability_inspection_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_dpabi_capability_inspection(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


def run_dpabi_wrapper_scaffold_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    capabilities_path = node.params.get(
        "capabilities_path",
        f"{context.work_dir}/dpabi/dpabi_capabilities.json",
    )

    result = write_dpabi_wrapper_scaffold(
        capabilities_path=capabilities_path,
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_dpabi_input_manifest_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    dataset_index_path = node.params.get(
        "dataset_index",
        f"{context.work_dir}/dataset_index/dataset_index.json",
    )

    result = build_dpabi_input_manifest(
        dataset_index_path=dataset_index_path,
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_preflight_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    capabilities_path = node.params.get(
        "capabilities_path",
        f"{context.work_dir}/dpabi/dpabi_capabilities.json",
    )
    manifest_path = node.params.get(
        "manifest_path",
        f"{context.work_dir}/dpabi/dpabi_input_manifest.json",
    )
    wrapper_config_path = node.params.get(
        "wrapper_config_template_path",
        f"{context.work_dir}/dpabi/dpabi_wrapper_config_template.yaml",
    )

    result = run_dpabi_preflight(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        capabilities_path=capabilities_path,
        manifest_path=manifest_path,
        wrapper_config_template_path=wrapper_config_path,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_run_plan_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    capabilities_path = node.params.get(
        "capabilities_path",
        f"{context.work_dir}/dpabi/dpabi_capabilities.json",
    )
    manifest_path = node.params.get(
        "manifest_path",
        f"{context.work_dir}/dpabi/dpabi_input_manifest.json",
    )
    preflight_path = node.params.get(
        "preflight_path",
        f"{context.work_dir}/dpabi/dpabi_preflight_report.json",
    )
    params_path = node.params.get(
        "params_path",
        f"{context.work_dir}/dpabi/dpabi_params_review.yaml",
    )

    result = create_dpabi_run_plan(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        capabilities_path=capabilities_path,
        manifest_path=manifest_path,
        preflight_path=preflight_path,
        params_path=params_path,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_sandbox_smoke_run_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    approved = bool(node.params.get("approved", False))
    approved_by = node.params.get("approved_by", "local-user")

    result = run_dpabi_sandbox_smoke(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=approved,
        approved_by=approved_by,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


def run_dpabi_signature_probe_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_dpabi_signature_probe(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


def run_dpabi_wrapper_contracts_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    signatures_path = node.params.get(
        "signatures_path",
        f"{context.work_dir}/dpabi/dpabi_function_signatures.json",
    )

    result = write_dpabi_wrapper_contracts(
        signatures_path=signatures_path,
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_dpabi_single_function_sandbox_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    function_name = node.params.get("function_name", "y_Smooth")
    approved = bool(node.params.get("approved", False))
    approved_by = node.params.get("approved_by", "local-user")

    result = run_dpabi_single_function_sandbox(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        function_name=function_name,
        approved=approved,
        approved_by=approved_by,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


NODE_REGISTRY: dict[str, NodeRunner] = {
    "environment_check": run_environment_check_node,
    "spm_smoke_test": run_spm_smoke_test_node,
    "create_synthetic_bids": run_create_synthetic_bids_node,
    "data_inspection": run_data_inspection_node,
    "spm_smooth_subject": run_spm_smooth_subject_node,
    "subject_qc": run_subject_qc_node,
    "dataset_evaluation": run_dataset_evaluation_node,
    "gpu_alff_subject": gpu_alff_subject_node,
    "gpu_reho_subject": gpu_reho_subject_node,
    "gpu_nuisance_regression_subject": gpu_nuisance_regression_subject_node,
    "gpu_temporal_filtering_subject": gpu_temporal_filtering_subject_node,
    "gpu_functional_connectivity_subject": gpu_functional_connectivity_subject_node,
    "dpabi_capability_inspection": run_dpabi_capability_inspection_node,
    "dpabi_wrapper_scaffold": run_dpabi_wrapper_scaffold_node,
    "dpabi_input_manifest": run_dpabi_input_manifest_node,
    "dpabi_preflight": run_dpabi_preflight_node,
    "dpabi_run_plan": run_dpabi_run_plan_node,
    "dpabi_sandbox_smoke_run": run_dpabi_sandbox_smoke_run_node,
    "dpabi_signature_probe": run_dpabi_signature_probe_node,
    "dpabi_wrapper_contracts": run_dpabi_wrapper_contracts_node,
    "dpabi_single_function_sandbox": run_dpabi_single_function_sandbox_node,
}


def run_dpabi_subject_smooth_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    subject_id = node.params.get("subject_id", "")
    input_bold = node.params.get("input_bold", "")
    function_name = node.params.get("function_name", "y_Smooth")
    fwhm = node.params.get("fwhm", [4, 4, 4])
    approved = bool(node.params.get("approved", False))

    result = run_dpabi_subject_smooth(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        subject_id=subject_id,
        input_bold=input_bold,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        function_name=function_name,
        fwhm=fwhm,
        approved=approved,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


def run_dpabi_subject_wrapper_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


NODE_REGISTRY["dpabi_subject_smooth"] = run_dpabi_subject_smooth_node
NODE_REGISTRY["dpabi_subject_wrapper_report"] = run_dpabi_subject_wrapper_report_node


def run_dpabi_wrapper_validation_matrix_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        signatures_path=node.params.get("signatures_path", f"{context.work_dir}/dpabi/dpabi_function_signatures.json"),
        contracts_path=node.params.get("contracts_path", f"{context.work_dir}/dpabi/dpabi_wrapper_contracts.json"),
        sandbox_result_path=node.params.get("sandbox_result_path", f"{context.work_dir}/dpabi/single_function_sandbox/dpabi_single_function_result.json"),
        subject_wrapper_summary_path=node.params.get("subject_wrapper_summary_path", "./reports/dpabi/dpabi_subject_wrapper_summary.json"),
    )
    result["node_id"] = node.id
    return result


NODE_REGISTRY["dpabi_wrapper_validation_matrix"] = run_dpabi_wrapper_validation_matrix_node


def run_dpabi_template_library_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_template_library(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        matrix_path=node.params.get(
            "matrix_path",
            f"{context.work_dir}/dpabi/dpabi_wrapper_compatibility_matrix.json",
        ),
    )
    result["node_id"] = node.id
    return result


NODE_REGISTRY["dpabi_template_library"] = run_dpabi_template_library_node


def run_dpabi_template_instantiate_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = instantiate_dpabi_template(
        template_id=node.params.get("template_id", "dpabi_y_smooth_subject_wrapper_template"),
        instance_id=node.params.get("instance_id"),
        run_id=node.params.get("run_id"),
        function_name=node.params.get("function_name"),
        fwhm=node.params.get("fwhm"),
        subjects=node.params.get("subjects"),
        scheduler=node.params.get("scheduler"),
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_template_execute_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = execute_dpabi_template_instance(
        instance_id=node.params.get("instance_id", ""),
        project_config_path=context.project_config.get("project_config_path", "examples/project_config_dataset.yaml"),
        approved=node.params.get("approved", False),
        approved_by=node.params.get("approved_by", "local-user"),
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


NODE_REGISTRY["dpabi_template_instantiate"] = run_dpabi_template_instantiate_node
NODE_REGISTRY["dpabi_template_execute"] = run_dpabi_template_execute_node


def run_rsfmri_preprocessing_plan_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_rsfmri_preprocessing_plan(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


NODE_REGISTRY["rsfmri_preprocessing_plan"] = run_rsfmri_preprocessing_plan_node


def _find_subject_bold(subject_record: dict[str, Any]) -> str | None:
    for session in subject_record.get("sessions", []):
        for func in session.get("func", []):
            if func.get("bold"):
                return func.get("bold")
    return None


def run_spm_realign_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id or not subject_record:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id or subject_record in context."],
        }

    use_slice_timing_output = bool(node.params.get("use_slice_timing_output", False))

    resolved = resolve_realign_input(
        subject_id=subject_id,
        subject_record=subject_record,
        derivatives_dir=context.derivatives_dir,
        use_slice_timing_output=use_slice_timing_output,
    )

    if not resolved.get("ok"):
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": resolved.get("warnings", []),
            "errors": resolved.get("errors", []),
        }

    bold = resolved["input_bold"]

    result = run_spm_realign_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=subject_id,
        input_bold=bold,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        matlab_script_dir="./matlab",
        allow_derivative_input=use_slice_timing_output,
    )

    result["node_id"] = node.id
    result["input_resolution"] = resolved
    return result


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


NODE_REGISTRY["spm_realign_subject"] = run_spm_realign_subject_node
NODE_REGISTRY["motion_qc_subject"] = run_motion_qc_subject_node
NODE_REGISTRY["motion_qc_dataset_report"] = run_motion_qc_dataset_report_node


def run_spm_slice_timing_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id or not subject_record:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id or subject_record in context."],
        }

    bold = _find_subject_bold(subject_record)
    if not bold:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "errors": ["No BOLD input found for subject."],
        }

    result = run_spm_slice_timing_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=subject_id,
        input_bold=bold,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        tr=node.params.get("tr"),
        slice_order=node.params.get("slice_order"),
        reference_slice=node.params.get("reference_slice"),
        matlab_script_dir="./matlab",
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


NODE_REGISTRY["spm_slice_timing_subject"] = run_spm_slice_timing_subject_node
NODE_REGISTRY["slice_timing_qc_dataset_report"] = run_slice_timing_qc_dataset_report_node


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


NODE_REGISTRY["st_realign_motion_chain_report"] = run_st_realign_motion_chain_report_node


def run_spm_coregister_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id or not subject_record:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id or subject_record in context."],
        }

    result = run_spm_coregister_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=subject_id,
        subject_record=subject_record,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        matlab_script_dir="./matlab",
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


NODE_REGISTRY["spm_coregister_subject"] = run_spm_coregister_subject_node
NODE_REGISTRY["registration_qc_dataset_report"] = run_registration_qc_dataset_report_node


def run_spm_segment_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id in context."],
        }

    result = run_spm_segment_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=subject_id,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        matlab_script_dir="./matlab",
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


NODE_REGISTRY["spm_segment_subject"] = run_spm_segment_subject_node
NODE_REGISTRY["tissue_qc_dataset_report"] = run_tissue_qc_dataset_report_node


def run_spm_normalize_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id in context."],
        }

    result = run_spm_normalize_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=subject_id,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        voxel_size=node.params.get("voxel_size", [3.0, 3.0, 3.0]),
        bounding_box=node.params.get("bounding_box"),
        normalize_mean=bool(node.params.get("normalize_mean", True)),
        matlab_script_dir="./matlab",
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


NODE_REGISTRY["spm_normalize_subject"] = run_spm_normalize_subject_node
NODE_REGISTRY["normalization_qc_dataset_report"] = run_normalization_qc_dataset_report_node


def run_spm_smooth_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
    subject_record: dict[str, Any] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id:
        return {
            "ok": False, "node_id": node.id, "backend": "matlab-spm",
            "outputs": [], "errors": ["Missing subject_id in context."],
        }
    result = run_spm_smooth_subject(
        matlab_command=context.matlab_command, spm_dir=context.spm_dir,
        subject_id=subject_id, derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir, log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        fwhm=node.params.get("fwhm", [6.0, 6.0, 6.0]),
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


def run_smoothing_qc_dataset_report_node(
    context: NodeExecutionContext, node: PipelineNode,
) -> dict[str, Any]:
    result = write_smoothing_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


NODE_REGISTRY["spm_smooth_subject"] = run_spm_smooth_subject_node
NODE_REGISTRY["smoothing_qc_dataset_report"] = run_smoothing_qc_dataset_report_node


def run_nuisance_regression_subject_node(
    context: NodeExecutionContext, node: PipelineNode,
    subject_record: dict[str, Any] | None = None, subject_id: str | None = None,
) -> dict[str, Any]:
    if not subject_id: return {"ok": False, "node_id": node.id, "backend": "python", "outputs": [], "errors": ["Missing subject_id"]}
    result = run_nuisance_regression_subject(
        subject_id=subject_id, derivatives_dir=context.derivatives_dir,
        backend=node.params.get("backend", "python"),
        model=node.params.get("model", "friston24"),
        include_intercept=bool(node.params.get("include_intercept", True)),
        include_linear_trend=bool(node.params.get("include_linear_trend", True)),
        include_global_signal=bool(node.params.get("include_global_signal", False)),
    )
    result["node_id"] = node.id
    return result


def run_nuisance_regression_qc_dataset_report_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    result = write_nuisance_regression_dataset_report(derivatives_dir=context.derivatives_dir, report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"))
    result["node_id"] = node.id; return result


def run_dpabi_nuisance_regression_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    result = write_dpabi_nuisance_regression_contract(work_dir=context.work_dir)
    result["node_id"] = node.id; return result


NODE_REGISTRY["nuisance_regression_subject"] = run_nuisance_regression_subject_node
NODE_REGISTRY["nuisance_regression_qc_dataset_report"] = run_nuisance_regression_qc_dataset_report_node
NODE_REGISTRY["dpabi_nuisance_regression_contract"] = run_dpabi_nuisance_regression_contract_node


def run_temporal_filtering_subject_node(context: NodeExecutionContext, node: PipelineNode, subject_record: dict[str, Any] | None = None, subject_id: str | None = None) -> dict[str, Any]:
    if not subject_id: return {"ok": False, "node_id": node.id, "backend": "python", "outputs": [], "errors": ["Missing subject_id"]}
    result = run_temporal_filtering_subject(subject_id=subject_id, derivatives_dir=context.derivatives_dir, backend=node.params.get("backend", "python"), low_hz=float(node.params.get("low_hz", 0.01)), high_hz=float(node.params.get("high_hz", 0.08)), tr=node.params.get("tr"), fallback_tr=node.params.get("fallback_tr"))
    result["node_id"] = node.id; return result

def run_temporal_filtering_qc_dataset_report_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    result = write_temporal_filtering_dataset_report(derivatives_dir=context.derivatives_dir, report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"))
    result["node_id"] = node.id; return result

def run_dpabi_temporal_filtering_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    result = write_dpabi_temporal_filtering_contract(work_dir=context.work_dir)
    result["node_id"] = node.id; return result

NODE_REGISTRY["temporal_filtering_subject"] = run_temporal_filtering_subject_node
NODE_REGISTRY["temporal_filtering_qc_dataset_report"] = run_temporal_filtering_qc_dataset_report_node
NODE_REGISTRY["dpabi_temporal_filtering_contract"] = run_dpabi_temporal_filtering_contract_node


def run_alff_falff_subject_node(context: NodeExecutionContext, node: PipelineNode, subject_record: dict[str, Any] | None = None, subject_id: str | None = None) -> dict[str, Any]:
    if not subject_id: return {"ok": False, "node_id": node.id, "backend": "python", "outputs": [], "errors": ["Missing subject_id"]}
    r = run_alff_falff_subject(subject_id=subject_id, derivatives_dir=context.derivatives_dir, backend=node.params.get("backend", "python"), low_hz=node.params.get("low_hz"), high_hz=node.params.get("high_hz"), tr=node.params.get("tr"), fallback_tr=node.params.get("fallback_tr"))
    r["node_id"] = node.id; return r

def run_alff_falff_qc_dataset_report_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_alff_falff_dataset_report(derivatives_dir=context.derivatives_dir, report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"))
    r["node_id"] = node.id; return r

def run_alff_falff_gpu_candidate_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_alff_falff_gpu_candidate_contract(work_dir=context.work_dir); r["node_id"] = node.id; return r

def run_dpabi_alff_falff_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_dpabi_alff_falff_contract(work_dir=context.work_dir); r["node_id"] = node.id; return r

NODE_REGISTRY["alff_falff_subject"] = run_alff_falff_subject_node
NODE_REGISTRY["alff_falff_qc_dataset_report"] = run_alff_falff_qc_dataset_report_node
NODE_REGISTRY["alff_falff_gpu_candidate_contract"] = run_alff_falff_gpu_candidate_contract_node
NODE_REGISTRY["dpabi_alff_falff_contract"] = run_dpabi_alff_falff_contract_node


def run_reho_subject_node(context: NodeExecutionContext, node: PipelineNode, subject_record=None, subject_id=None) -> dict[str, Any]:
    if not subject_id: return {"ok": False, "node_id": node.id, "backend": "python", "outputs": [], "errors": ["Missing subject_id"]}
    r = run_reho_subject(subject_id=subject_id, derivatives_dir=context.derivatives_dir, backend=node.params.get("backend", "python"), neighborhood=int(node.params.get("neighborhood", 27)), use_gm_mask=bool(node.params.get("use_gm_mask", False)))
    r["node_id"] = node.id; return r

def run_reho_qc_dataset_report_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_reho_dataset_report(derivatives_dir=context.derivatives_dir, report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"))
    r["node_id"] = node.id; return r

def run_reho_gpu_candidate_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_reho_gpu_candidate_contract(work_dir=context.work_dir); r["node_id"] = node.id; return r

def run_dpabi_reho_contract_node(context: NodeExecutionContext, node: PipelineNode) -> dict[str, Any]:
    r = write_dpabi_reho_contract(work_dir=context.work_dir); r["node_id"] = node.id; return r

NODE_REGISTRY["reho_subject"] = run_reho_subject_node
NODE_REGISTRY["reho_qc_dataset_report"] = run_reho_qc_dataset_report_node
NODE_REGISTRY["reho_gpu_candidate_contract"] = run_reho_gpu_candidate_contract_node
NODE_REGISTRY["dpabi_reho_contract"] = run_dpabi_reho_contract_node


def run_functional_connectivity_subject_node(context, node, subject_record=None, subject_id=None):
    """Compute ROI-based functional connectivity for a subject."""
    if not subject_id:
        return {
            "ok": False, "node_id": node.id, "backend": "python",
            "outputs": [], "errors": ["Missing subject_id"],
        }
    result = run_functional_connectivity_subject(
        subject_id=subject_id,
        derivatives_dir=context.derivatives_dir,
        backend=node.params.get("backend", "python"),
        roi_count=int(node.params.get("roi_count", 4)),
        atlas_path=node.params.get("atlas_path"),
        generate_seed_map=bool(node.params.get("generate_seed_map", False)),
    )
    result["node_id"] = node.id
    return result


def run_functional_connectivity_qc_dataset_report_node(context, node):
    """Write dataset-level FC QC report."""
    result = write_functional_connectivity_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_functional_connectivity_gpu_candidate_contract_node(context, node):
    """Generate GPU candidate contract for FC computation."""
    result = write_functional_connectivity_gpu_candidate_contract(work_dir=context.work_dir)
    result["node_id"] = node.id
    return result


def run_dpabi_functional_connectivity_contract_node(context, node):
    """Generate DPABI contract for FC computation."""
    result = write_dpabi_functional_connectivity_contract(work_dir=context.work_dir)
    result["node_id"] = node.id
    return result


NODE_REGISTRY["functional_connectivity_subject"] = run_functional_connectivity_subject_node
NODE_REGISTRY["functional_connectivity_qc_dataset_report"] = run_functional_connectivity_qc_dataset_report_node
NODE_REGISTRY["functional_connectivity_gpu_candidate_contract"] = run_functional_connectivity_gpu_candidate_contract_node
NODE_REGISTRY["dpabi_functional_connectivity_contract"] = run_dpabi_functional_connectivity_contract_node


# ── Report / Export nodes ──────────────────────────────────────────────────

def run_group_dataset_summary_node(context, node):
    """Build group-level dataset summary report."""
    result = build_group_dataset_summary(
        derivatives_dir=context.derivatives_dir,
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_rsfmri_report_exporter_node(context, node):
    """Export rs-fMRI report package with checksums and safety manifest."""
    result = export_rsfmri_report_package(
        derivatives_dir=context.derivatives_dir,
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        work_dir=context.work_dir,
        exports_dir=node.params.get("exports_dir", "./exports"),
        export_id=node.params.get("export_id"),
        include_subject_qc=bool(node.params.get("include_subject_qc", True)),
        include_metrics=bool(node.params.get("include_metrics", True)),
        include_fc=bool(node.params.get("include_fc", True)),
        include_contracts=bool(node.params.get("include_contracts", True)),
        include_pipeline_runs=bool(node.params.get("include_pipeline_runs", True)),
    )
    result["node_id"] = node.id
    return result


def run_rsfmri_report_package_validator_node(context, node):
    """Validate exported report package integrity."""
    result = validate_rsfmri_report_package(
        exports_dir=node.params.get("exports_dir", "./exports"),
        export_id=node.params.get("export_id"),
        package_dir=node.params.get("package_dir"),
        zip_path=node.params.get("zip_path"),
        strict=bool(node.params.get("strict", False)),
    )
    result["node_id"] = node.id
    return result


def run_project_release_readiness_node(context, node):
    """Check project release readiness against quality gates."""
    result = build_release_readiness()
    result["node_id"] = node.id
    return result


def run_docs_inventory_node(context, node):
    """Build documentation inventory for the project."""
    result = build_docs_inventory()
    result["node_id"] = node.id
    return result


NODE_REGISTRY["group_dataset_summary"] = run_group_dataset_summary_node
NODE_REGISTRY["rsfmri_report_exporter"] = run_rsfmri_report_exporter_node
NODE_REGISTRY["rsfmri_report_package_validator"] = run_rsfmri_report_package_validator_node
NODE_REGISTRY["project_release_readiness"] = run_project_release_readiness_node
NODE_REGISTRY["docs_inventory"] = run_docs_inventory_node

# ── M7-DPABI-T002a: register safe DPABI metadata/contract runners ──
NODE_REGISTRY["dpabi_capability_inspection"] = run_dpabi_capability_inspection_node
NODE_REGISTRY["dpabi_input_manifest"] = run_dpabi_input_manifest_node
NODE_REGISTRY["dpabi_preflight"] = run_dpabi_preflight_node
NODE_REGISTRY["dpabi_run_plan"] = run_dpabi_run_plan_node
NODE_REGISTRY["dpabi_signature_probe"] = run_dpabi_signature_probe_node
NODE_REGISTRY["dpabi_wrapper_contracts"] = run_dpabi_wrapper_contracts_node
NODE_REGISTRY["dpabi_wrapper_scaffold"] = run_dpabi_wrapper_scaffold_node

# ── M7-DPABI-T004b: register dpabi_sandbox_smoke_run (NOTE: remains blocked by allowlist) ──
def run_dpabi_sandbox_smoke_run_node(context, node):
    from src.backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke
    result = run_dpabi_sandbox_smoke(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=True,
    )
    result["node_id"] = node.id
    return result
NODE_REGISTRY["dpabi_sandbox_smoke_run"] = run_dpabi_sandbox_smoke_run_node
# NOTE: dpabi_single_function_sandbox is NOT registered — must remain blocked.
# NOTE: dpabi_sandbox_smoke_run has a registered runner but IS blocked by reviewed execution allowlist.


def get_node_runner(node_id: str) -> NodeRunner:
    try:
        return NODE_REGISTRY[node_id]
    except KeyError as exc:
        raise KeyError(f"No node runner registered for node id: {node_id}") from exc
