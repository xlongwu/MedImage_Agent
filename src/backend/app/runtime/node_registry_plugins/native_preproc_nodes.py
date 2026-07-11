"""Native preprocessing node registry plugin."""
from __future__ import annotations

from typing import Any

from src.backend.app.native_preproc.orchestrator.stage_graph import iter_native_full_stage_specs
from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.schemas.native_preproc_api import (
    NativeFullPreprocConfirmations,
    NativeFullPreprocRequest,
)
from src.backend.app.schemas.pipeline_schema import PipelineNode
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.native_preproc_full import (
    run_native_full_dry_run,
    run_native_full_execute,
)


def _request_from_node(context: NodeExecutionContext, node: PipelineNode) -> NativeFullPreprocRequest:
    params = dict(node.params or {})
    confirmations = params.get("confirmations") if isinstance(params.get("confirmations"), dict) else {}
    return NativeFullPreprocRequest(
        run_id=str(params.get("run_id") or context.run_id),
        subject_id=str(params.get("subject_id") or ""),
        session_id=str(params.get("session_id") or ""),
        output_dir=str(params.get("output_dir") or ""),
        input_bold=str(params.get("input_bold") or ""),
        sidecar_json=str(params.get("sidecar_json") or ""),
        t1w=str(params.get("t1w") or ""),
        template=str(params.get("template") or ""),
        atlas=str(params.get("atlas") or ""),
        atlas_labels=str(params.get("atlas_labels") or ""),
        conversion_run_id=str(params.get("conversion_run_id") or ""),
        dparsf_config=dict(params.get("dparsf_config") or {}),
        stage_overrides=dict(params.get("stage_overrides") or {}),
        remove_first=int(params.get("remove_first") or 0),
        enable_slice_timing=bool(params.get("enable_slice_timing", True)),
        tr=float(params["tr"]) if params.get("tr") is not None else None,
        confirmations=NativeFullPreprocConfirmations(
            confirm_reviewed_native_execution=bool(
                confirmations.get("confirm_reviewed_native_execution")
                or params.get("confirm_reviewed_native_execution", False)
            ),
            confirm_rawdata_readonly=bool(
                confirmations.get("confirm_rawdata_readonly")
                or params.get("confirm_rawdata_readonly", False)
            ),
            confirm_no_external_tools=bool(
                confirmations.get("confirm_no_external_tools")
                or params.get("confirm_no_external_tools", False)
            ),
            confirm_research_use_only=bool(
                confirmations.get("confirm_research_use_only")
                or params.get("confirm_research_use_only", False)
            ),
            confirm_no_clinical_use=bool(
                confirmations.get("confirm_no_clinical_use")
                or params.get("confirm_no_clinical_use", False)
            ),
        ),
    )


def run_native_full_dry_run_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    request = _request_from_node(context, node)
    project_id = str(node.params.get("project_id") or context.project_config.get("project_id") or "")
    project = mock_store.get_project(project_id) if project_id else None
    project_metadata = project.metadata if project is not None else {}
    project_dir = str(
        node.params.get("project_dir")
        or project_metadata.get("project_dir")
        or context.project_config.get("project_dir")
        or ""
    )
    result = run_native_full_dry_run(
        project_id,
        request,
        project_dir=project_dir,
        project_metadata=project_metadata,
    )
    payload = result.model_dump(mode="json")
    payload["node_id"] = node.id
    return payload


def run_native_full_execute_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    request = _request_from_node(context, node)
    project_id = str(node.params.get("project_id") or context.project_config.get("project_id") or "")
    project = mock_store.get_project(project_id) if project_id else None
    project_metadata = project.metadata if project is not None else {}
    project_dir = str(
        node.params.get("project_dir")
        or project_metadata.get("project_dir")
        or context.project_config.get("project_dir")
        or ""
    )
    result = run_native_full_execute(
        project_id,
        request,
        project_dir=project_dir,
        project_metadata=project_metadata,
    )
    payload = result.model_dump(mode="json")
    payload["node_id"] = node.id
    return payload


def _run_native_stage_boundary_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "blocked",
        "backend": "native_python",
        "node_id": node.id,
        "warnings": [],
        "errors": [
            "Native stage node is registered as a stable reviewed-plan boundary; "
            "execute via native_preproc_full_execute so manifest, provenance, "
            "artifact validation, and status truthfulness remain coordinated."
        ],
        "safety_flags": {
            "no_external_tools_executed": True,
            "no_matlab_spm_dpabi": True,
            "third_party_runtime_not_used": True,
        },
    }


REGISTRY: dict[str, NodeRunner] = {
    "native_preproc_full_dry_run": run_native_full_dry_run_node,
    "native_preproc_full_execute": run_native_full_execute_node,
}

for _spec in iter_native_full_stage_specs():
    REGISTRY.setdefault(_spec.node_id, _run_native_stage_boundary_node)


__all__ = ["REGISTRY"]
