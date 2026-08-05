"""Ticket-bound application service for native in-project DICOM conversion."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.backend.app.services.reviewed_native_conversion_handoff import (
    ensure_reviewed_native_conversion_handoff,
)


class ReviewedConversionService:
    NODE_ID = "native_dicom_conversion_execute"
    BACKEND_ID = "medimage-native"

    def __init__(self, handoff: Callable[..., dict[str, Any]] | None = None) -> None:
        self._handoff = handoff or ensure_reviewed_native_conversion_handoff

    def check_readiness(
        self,
        *,
        project_id: str,
        conversion_run_id: str,
        project_dir: str,
        rawdata_dir: str,
        output_dir: str,
    ) -> dict[str, Any]:
        """Read and verify the persisted conversion package without dispatching."""
        from src.backend.app.schemas.dicom_conversion_execution import (
            validate_output_root_not_under_rawdata,
            validate_output_root_under_project,
        )
        from src.backend.app.services.dicom_conversion_release_approval import (
            read_release_approval,
        )
        from src.backend.app.services.dicom_conversion_release_readiness import (
            evaluate_conversion_release_readiness,
        )
        from src.backend.app.services.dicom_conversion_review_package import (
            read_conversion_review_package,
        )

        if not all((project_id, conversion_run_id, project_dir, rawdata_dir, output_dir)):
            return self._blocked("CONVERSION_REVIEW_PACKAGE_BINDING_REQUIRED")
        if not validate_output_root_under_project(output_dir, project_dir) or not validate_output_root_not_under_rawdata(
            output_dir, rawdata_dir
        ):
            return self._blocked("CONVERSION_OUTPUT_SCOPE_INVALID")
        approval = read_release_approval(
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            project_dir=project_dir,
        )
        if not approval.approved or approval.blocked:
            return self._blocked("CONVERSION_RELEASE_APPROVAL_REQUIRED")
        readiness = evaluate_conversion_release_readiness(
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            output_root=output_dir,
        )
        if readiness.status not in {"ready_for_human_release_review", "warning"} or readiness.gates_met < readiness.gates_total:
            return self._blocked("CONVERSION_RELEASE_READINESS_REQUIRED")
        package = read_conversion_review_package(
            project_id,
            conversion_run_id,
            project_dir=project_dir,
            rawdata_dir=rawdata_dir,
        )
        required = {"approval_record", "rawdata_checksum_before", "rollback_plan_dry_run"}
        present = {item.kind for item in package.files if item.exists}
        if not package.ok or not required.issubset(present):
            return self._blocked("CONVERSION_REVIEW_PACKAGE_INCOMPLETE")
        return {
            "ok": True,
            "status": "ready",
            "node_id": self.NODE_ID,
            "backend": self.BACKEND_ID,
            "preprocessing_ready": False,
            "conversion_run_id": conversion_run_id,
            "package_uri": f"project://conversion_runs/{Path(conversion_run_id).name}",
            "safety_flags": {
                "rawdata_not_modified": True,
                "no_external_tools_executed": True,
                "ticket_bound": False,
            },
        }

    def execute_node(self, *, context, node, store) -> dict[str, Any]:
        execution = context.tool_execution_context
        if execution is None:
            return self._blocked("VERIFIED_EXECUTION_CONTEXT_REQUIRED")
        if self.NODE_ID not in execution.approved_node_ids:
            return self._blocked("CONVERSION_NODE_NOT_APPROVED")
        if self.BACKEND_ID not in execution.approved_backend_ids:
            return self._blocked("CONVERSION_BACKEND_NOT_APPROVED")
        project_id = str(node.params.get("project_id") or context.project_config.get("project_id") or "")
        conversion_run_id = str(node.params.get("conversion_run_id") or "")
        project = store.get_project(project_id) if project_id else None
        metadata = project.metadata if project is not None and isinstance(project.metadata, dict) else {}
        project_dir = str(node.params.get("project_dir") or metadata.get("project_dir") or "")
        rawdata_dir = str(node.params.get("rawdata_dir") or metadata.get("rawdata_dir") or "")
        if not project_id or project_id != execution.project_id or project is None:
            return self._blocked("CONVERSION_PROJECT_BINDING_INVALID")
        if not conversion_run_id or not project_dir or not rawdata_dir:
            return self._blocked("CONVERSION_REVIEW_PACKAGE_BINDING_REQUIRED")
        result = self._handoff(
            store,
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            project_dir=project_dir,
            rawdata_dir=rawdata_dir,
            execution_context=execution,
        )
        successful = bool(result.get("ok")) and str(result.get("status")) in {
            "registered", "already_registered", "recovered_registration"
        }
        return {
            **result,
            "ok": successful,
            "status": "succeeded" if successful else str(result.get("status") or "failed"),
            "node_id": self.NODE_ID,
            "backend": self.BACKEND_ID,
            "preprocessing_ready": successful,
            "safety_flags": {
                "rawdata_not_modified": True,
                "no_external_tools_executed": True,
                "no_matlab_spm_dpabi": True,
                "ticket_bound": True,
            },
        }

    def _blocked(self, code: str) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "blocked",
            "node_id": self.NODE_ID,
            "backend": self.BACKEND_ID,
            "preprocessing_ready": False,
            "blocking_issues": [code],
            "safety_flags": {
                "rawdata_not_modified": True,
                "no_external_tools_executed": True,
                "no_matlab_spm_dpabi": True,
                "ticket_bound": False,
            },
        }
