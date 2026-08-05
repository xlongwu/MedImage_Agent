"""Spm Nodes registry plugin."""

from __future__ import annotations

from typing import Any

from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.schemas.pipeline_schema import PipelineNode
from src.backend.app.tools.rsfmri_chain_resolver import resolve_realign_input
from src.backend.app.tools.spm_coregister_runner import run_spm_coregister_subject
from src.backend.app.tools.spm_normalize_runner import run_spm_normalize_subject
from src.backend.app.tools.spm_realign_runner import run_spm_realign_subject
from src.backend.app.tools.spm_runner import run_spm_smoke_test
from src.backend.app.tools.spm_segment_runner import run_spm_segment_subject
from src.backend.app.tools.spm_slice_timing_runner import run_spm_slice_timing_subject
from src.backend.app.tools.spm_smooth_runner import run_spm_smooth_subject


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


def run_spm_smooth_subject_node(
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
    result = run_spm_smooth_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=subject_id,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        fwhm=node.params.get("fwhm", [6.0, 6.0, 6.0]),
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


REGISTRY: dict[str, NodeRunner] = {
    "spm_smoke_test": run_spm_smoke_test_node,
    "spm_realign_subject": run_spm_realign_subject_node,
    "spm_slice_timing_subject": run_spm_slice_timing_subject_node,
    "spm_coregister_subject": run_spm_coregister_subject_node,
    "spm_segment_subject": run_spm_segment_subject_node,
    "spm_normalize_subject": run_spm_normalize_subject_node,
    "spm_smooth_subject": run_spm_smooth_subject_node,
}
