"""Dpabi Nodes registry plugin."""

from __future__ import annotations

from typing import Any

from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.schemas.pipeline_schema import PipelineNode
from src.backend.app.tools.dpabi_adapter import build_dpabi_input_manifest
from src.backend.app.tools.dpabi_alff_contract import write_dpabi_alff_falff_contract
from src.backend.app.tools.dpabi_config import write_dpabi_wrapper_scaffold
from src.backend.app.tools.dpabi_contract_registry import write_dpabi_wrapper_contracts
from src.backend.app.tools.dpabi_fc_contract import write_dpabi_functional_connectivity_contract
from src.backend.app.tools.dpabi_filtering_contract import write_dpabi_temporal_filtering_contract
from src.backend.app.tools.dpabi_nuisance_contract import write_dpabi_nuisance_regression_contract
from src.backend.app.tools.dpabi_preflight import run_dpabi_preflight
from src.backend.app.tools.dpabi_reho_contract import write_dpabi_reho_contract
from src.backend.app.tools.dpabi_run_plan import create_dpabi_run_plan
from src.backend.app.tools.dpabi_runner import run_dpabi_capability_inspection
from src.backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke
from src.backend.app.tools.dpabi_signature_runner import run_dpabi_signature_probe
from src.backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox
from src.backend.app.tools.dpabi_subject_wrapper import run_dpabi_subject_smooth
from src.backend.app.tools.dpabi_subject_wrapper_report import write_dpabi_subject_wrapper_report
from src.backend.app.tools.dpabi_template_instantiator import (
    execute_dpabi_template_instance,
    instantiate_dpabi_template,
)
from src.backend.app.tools.dpabi_template_library import write_dpabi_template_library
from src.backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix


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


def run_dpabi_sandbox_smoke_run_node(context, node):
    result = run_dpabi_sandbox_smoke(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=True,
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


def run_dpabi_wrapper_validation_matrix_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        signatures_path=node.params.get(
            "signatures_path", f"{context.work_dir}/dpabi/dpabi_function_signatures.json"
        ),
        contracts_path=node.params.get(
            "contracts_path", f"{context.work_dir}/dpabi/dpabi_wrapper_contracts.json"
        ),
        sandbox_result_path=node.params.get(
            "sandbox_result_path",
            f"{context.work_dir}/dpabi/single_function_sandbox/dpabi_single_function_result.json",
        ),
        subject_wrapper_summary_path=node.params.get(
            "subject_wrapper_summary_path", "./reports/dpabi/dpabi_subject_wrapper_summary.json"
        ),
    )
    result["node_id"] = node.id
    return result


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
        project_config_path=context.project_config.get(
            "project_config_path", "examples/project_config_dataset.yaml"
        ),
        approved=node.params.get("approved", False),
        approved_by=node.params.get("approved_by", "local-user"),
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_nuisance_regression_contract_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    result = write_dpabi_nuisance_regression_contract(work_dir=context.work_dir)
    result["node_id"] = node.id
    return result


def run_dpabi_temporal_filtering_contract_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    result = write_dpabi_temporal_filtering_contract(work_dir=context.work_dir)
    result["node_id"] = node.id
    return result


def run_dpabi_alff_falff_contract_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    r = write_dpabi_alff_falff_contract(work_dir=context.work_dir)
    r["node_id"] = node.id
    return r


def run_dpabi_reho_contract_node(
    context: NodeExecutionContext, node: PipelineNode
) -> dict[str, Any]:
    r = write_dpabi_reho_contract(work_dir=context.work_dir)
    r["node_id"] = node.id
    return r


def run_dpabi_functional_connectivity_contract_node(context, node):
    """Generate DPABI contract for FC computation."""
    result = write_dpabi_functional_connectivity_contract(work_dir=context.work_dir)
    result["node_id"] = node.id
    return result


REGISTRY: dict[str, NodeRunner] = {
    "dpabi_capability_inspection": run_dpabi_capability_inspection_node,
    "dpabi_wrapper_scaffold": run_dpabi_wrapper_scaffold_node,
    "dpabi_input_manifest": run_dpabi_input_manifest_node,
    "dpabi_preflight": run_dpabi_preflight_node,
    "dpabi_run_plan": run_dpabi_run_plan_node,
    "dpabi_sandbox_smoke_run": run_dpabi_sandbox_smoke_run_node,
    "dpabi_signature_probe": run_dpabi_signature_probe_node,
    "dpabi_wrapper_contracts": run_dpabi_wrapper_contracts_node,
    "dpabi_single_function_sandbox": run_dpabi_single_function_sandbox_node,
    "dpabi_subject_smooth": run_dpabi_subject_smooth_node,
    "dpabi_subject_wrapper_report": run_dpabi_subject_wrapper_report_node,
    "dpabi_wrapper_validation_matrix": run_dpabi_wrapper_validation_matrix_node,
    "dpabi_template_library": run_dpabi_template_library_node,
    "dpabi_template_instantiate": run_dpabi_template_instantiate_node,
    "dpabi_template_execute": run_dpabi_template_execute_node,
    "dpabi_nuisance_regression_contract": run_dpabi_nuisance_regression_contract_node,
    "dpabi_temporal_filtering_contract": run_dpabi_temporal_filtering_contract_node,
    "dpabi_alff_falff_contract": run_dpabi_alff_falff_contract_node,
    "dpabi_reho_contract": run_dpabi_reho_contract_node,
    "dpabi_functional_connectivity_contract": run_dpabi_functional_connectivity_contract_node,
}
