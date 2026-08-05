"""Core Nodes registry plugin."""
from __future__ import annotations

from typing import Any

from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.schemas.pipeline_schema import PipelineNode
from src.backend.app.tools.data_inspector import inspect_dataset
from src.backend.app.tools.dataset_evaluator import evaluate_dataset
from src.backend.app.tools.matlab_runner import run_matlab_check
from src.backend.app.tools.node_contract_smoke import run_contract_smoke_node
from src.backend.app.tools.report_writer import write_dataset_evaluation_report
from src.backend.app.tools.synthetic_bids import create_synthetic_bids_dataset


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
