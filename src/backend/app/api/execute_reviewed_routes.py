"""Execute Reviewed Plan API (POST /api/plans/execute-reviewed).

Supports two modes:

  dry_run=true  — readiness check: validation, approval gate, adapter,
                   policy, optional pipeline YAML write, optional audit.
  dry_run=false — safe execution preflight (M5-T015) + gated execution
                   for safe allowlist nodes only (M5-T016).

ALL executor calls are gated behind env var, confirm_execution,
persist_audit, ProjectSettings, validation, approval, adapter,
execution policy, pipeline YAML write, audit, AND safe allowlist.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.backend.app.config.settings import ProjectSettings
from src.backend.app.planner.approval_gate import check_approval_gate
from src.backend.app.planner.audit_record import build_review_audit_record, write_audit_record
from src.backend.app.planner.plan_adapter import adapt_reviewed_plan
from src.backend.app.planner.plan_validator import validate_plan
from src.backend.app.planner.project_context import (
    ProjectContext,
    ProjectContextError,
    load_project_context,
    validate_plan_project_context,
)
from src.backend.app.planner.reviewed_plan_store import (
    ReviewedPlanStoreError,
    build_run_link,
    new_run_identity,
    resolve_reviewed_plan_for_execution,
)
from src.backend.app.planner import pipeline_writer  # imported as module for monkeypatch
from src.backend.app.runtime.pipeline_executor import run_pipeline  # for monkeypatch
from src.backend.app.schemas.desktop import ReviewedPlanRecord
from src.backend.app.services.mock_store import mock_store

router = APIRouter()

AUDIT_RECORD_DIR = Path("outputs/reports/audit_records")


class ExecuteReviewedRequest(BaseModel):
    plan: dict[str, Any]
    approval: dict[str, Any] | None = None
    project_id: str | None = None
    reviewed_plan_id: str | None = None
    project_config_path: str | None = None
    dry_run: bool = True
    persist_audit: bool = False
    write_pipeline_yaml: bool = False
    confirm_execution: bool = False
    actor: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _pipeline_yaml_default() -> dict[str, Any]:
    return {
        "would_write": False,
        "written": False,
        "path": None,
        "requires_audit": True,
    }


def _pipeline_yaml_summary(
    *,
    would_write: bool = False,
    written: bool = False,
    path: str | None = None,
    requires_audit: bool = True,
) -> dict[str, Any]:
    return {
        "would_write": would_write,
        "written": written,
        "path": path,
        "requires_audit": requires_audit,
    }


def _plan_summary(plan: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    nodes = plan.get("nodes", []) or []
    return {
        "pipeline_id": plan.get("pipeline_id", "unknown"),
        "nodes_total": len(nodes),
        "approval_required_nodes": validation.get("approval_required_nodes", []),
        "high_risk_nodes": validation.get("high_risk_nodes", []),
    }


def _execution_meta(
    submitted: bool = False,
    run_id: str | None = None,
    executor_called: bool = False,
) -> dict[str, Any]:
    return {
        "submitted": submitted,
        "run_id": run_id,
        "executor_called": executor_called,
    }


def _no_audit() -> dict[str, Any]:
    return {"persisted": False}


def _adapter_summary(adapter_result: Any) -> dict[str, Any]:
    if adapter_result is None:
        return {"ok": False, "errors": [], "warnings": [], "policy": {}, "pipeline": {"available": False}}
    pipeline = adapter_result.pipeline
    return {
        "ok": adapter_result.ok,
        "errors": adapter_result.errors,
        "warnings": adapter_result.warnings,
        "policy": adapter_result.policy,
        "pipeline": {
            "available": adapter_result.ok and pipeline is not None,
            "name": pipeline.get("pipeline_id", "unknown") if pipeline else "unknown",
            "nodes_total": len(pipeline.get("nodes", [])) if pipeline else 0,
            "modality": pipeline.get("modality", "rsfmri") if pipeline else "rsfmri",
        } if adapter_result.ok and pipeline else {"available": False},
    }


def _is_policy_blocked(policy: dict[str, list[str]]) -> bool:
    blocked = (policy.get("blocked_spm_nodes", []) +
               policy.get("blocked_dpabi_execution_nodes", []) +
               policy.get("blocked_gui_nodes", []) +
               policy.get("blocked_manual_required_nodes", []) +
               policy.get("blocked_unknown_nodes", []) +
               policy.get("blocked_uncataloged_nodes", []))
    return len(blocked) > 0


def _check_safe_allowlist(policy: dict[str, list[str]]) -> str | None:
    """Check that all allowed nodes are in the safe allowlist.

    Returns error status string if any node is not in the allowlist, else None.

    M5: pure-Python nodes only.
    M6-T004b: also allows spm_smoke_test (verified MATLAB/SPM environment smoke).
    """
    gpu_nodes = policy.get("allowed_gpu_nodes", [])
    contract_nodes = policy.get("allowed_contract_nodes", [])
    spm_smoke_nodes = policy.get("allowed_spm_smoke_nodes", [])
    spm_realign_sandbox_nodes = policy.get("allowed_spm_realign_sandbox_nodes", [])
    spm_slice_timing_sandbox_nodes = policy.get("allowed_spm_slice_timing_sandbox_nodes", [])
    spm_coregister_sandbox_nodes = policy.get("allowed_spm_coregister_sandbox_nodes", [])
    spm_segment_sandbox_nodes = policy.get("allowed_spm_segment_sandbox_nodes", [])
    spm_normalize_sandbox_nodes = policy.get("allowed_spm_normalize_sandbox_nodes", [])
    spm_smooth_sandbox_nodes = policy.get("allowed_spm_smooth_sandbox_nodes", [])
    dpabi_metadata_nodes = policy.get("allowed_dpabi_metadata_nodes", [])
    dpabi_sandbox_smoke_nodes = policy.get("allowed_dpabi_sandbox_smoke_nodes", [])
    dpabi_single_function_sandbox_nodes = policy.get("allowed_dpabi_single_function_sandbox_nodes", [])
    dpabi_subject_smooth_sandbox_nodes = policy.get("allowed_dpabi_subject_smooth_sandbox_nodes", [])
    dpabi_subject_wrapper_report_nodes = policy.get("allowed_dpabi_subject_wrapper_report_nodes", [])
    dpabi_validation_matrix_nodes = policy.get("allowed_dpabi_validation_matrix_nodes", [])

    contract_nodes = policy.get("allowed_contract_nodes", [])
    gpu_synthetic_smoke_nodes = policy.get("allowed_gpu_synthetic_smoke_nodes", [])
    gpu_alff_sandbox_nodes = policy.get("allowed_gpu_alff_sandbox_nodes", [])
    gpu_reho_sandbox_nodes = policy.get("allowed_gpu_reho_sandbox_nodes", [])
    gpu_temporal_filtering_sandbox_nodes = policy.get("allowed_gpu_temporal_filtering_sandbox_nodes", [])
    gpu_functional_connectivity_sandbox_nodes = policy.get("allowed_gpu_functional_connectivity_sandbox_nodes", [])
    gpu_nuisance_regression_sandbox_nodes = policy.get("allowed_gpu_nuisance_regression_sandbox_nodes", [])
    unsafe = gpu_nodes  # contract_nodes are Python-only metadata, now allowed; gpu_synthetic_smoke sandbox-gated
    if unsafe:
        return "SAFE_EXECUTION_POLICY_BLOCKED"

    # Must have at least one allowed node
    python_nodes = policy.get("allowed_python_nodes", [])
    total_allowed = python_nodes + spm_smoke_nodes + spm_realign_sandbox_nodes + spm_slice_timing_sandbox_nodes + spm_coregister_sandbox_nodes + spm_segment_sandbox_nodes + spm_normalize_sandbox_nodes + spm_smooth_sandbox_nodes + dpabi_metadata_nodes + dpabi_sandbox_smoke_nodes + dpabi_single_function_sandbox_nodes + dpabi_subject_smooth_sandbox_nodes + dpabi_subject_wrapper_report_nodes + dpabi_validation_matrix_nodes + contract_nodes + gpu_synthetic_smoke_nodes + gpu_alff_sandbox_nodes + gpu_reho_sandbox_nodes + gpu_temporal_filtering_sandbox_nodes + gpu_functional_connectivity_sandbox_nodes + gpu_nuisance_regression_sandbox_nodes
    if not total_allowed:
        return "SAFE_EXECUTION_POLICY_BLOCKED"
    return None


def _write_audit(
    event_type: str,
    plan: dict[str, Any],
    validation: dict[str, Any],
    approval: dict[str, Any] | None,
    gate: dict[str, Any] | None,
    dry_run_result: dict[str, Any] | None,
    actor: str | None,
    request: ExecuteReviewedRequest,
) -> dict[str, Any]:
    if not request.persist_audit:
        return _no_audit()
    try:
        record = build_review_audit_record(
            event_type=event_type,
            plan=plan,
            validation=validation,
            approval=approval,
            approval_gate=gate,
            dry_run_result=dry_run_result,
            actor=actor or request.actor,
            source="execute_reviewed_api",
        )
        path = write_audit_record(record, AUDIT_RECORD_DIR)
        return {
            "persisted": True,
            "audit_id": record.audit_id,
            "audit_path": str(path),
            "event_type": event_type,
        }
    except Exception:
        return {"persisted": False, "error": "Failed to write audit record"}


def _blocked_result(
    status: str,
    plan: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any] | None,
    adapter: Any,
    request: ExecuteReviewedRequest,
) -> dict[str, Any]:
    result = {
        "ok": False,
        "status": status,
        "dry_run": request.dry_run,
        "would_execute": False,
        "execution_allowed": False,
        "validation": validation,
        "approval_gate": gate,
        "adapter": _adapter_summary(adapter),
        "pipeline_yaml": _pipeline_yaml_default(),
        "project_config_path": request.project_config_path,
        "execution": _execution_meta(),
    }
    result["audit"] = _write_audit(
        "execution_blocked", plan, validation, request.approval,
        gate, result, request.actor, request,
    )
    return result


def _early_blocked(
    status: str,
    request: ExecuteReviewedRequest,
) -> dict[str, Any]:
    """Return a blocked result before any validation/approval/adapter runs."""
    return {
        "ok": False,
        "status": status,
        "dry_run": request.dry_run,
        "would_execute": False,
        "execution_allowed": False,
        "validation": None,
        "approval_gate": None,
        "adapter": None,
        "pipeline_yaml": _pipeline_yaml_default(),
        "plan_summary": None,
        "project_config_path": request.project_config_path,
        "execution": _execution_meta(),
        "audit": _no_audit(),
    }


def _try_write_pipeline_yaml(
    adapter: Any,
    request: ExecuteReviewedRequest,
    plan_hash: str | None = None,
) -> tuple[dict[str, Any], str | None, Path | None]:
    if not request.write_pipeline_yaml:
        return _pipeline_yaml_summary(would_write=True, written=False), None, None

    if not request.persist_audit:
        return _pipeline_yaml_summary(
            would_write=True, written=False, requires_audit=True,
        ), "PIPELINE_WRITE_REQUIRES_AUDIT", None

    try:
        pipeline_dict = adapter.pipeline if adapter else None
        if pipeline_dict is None:
            return _pipeline_yaml_summary(
                would_write=True, written=False,
            ), "PIPELINE_WRITE_FAILED", None
        path = pipeline_writer.write_reviewed_pipeline_yaml(
            pipeline_dict,
            plan_hash=plan_hash,
        )
        return _pipeline_yaml_summary(
            would_write=True, written=True, path=str(path),
        ), None, path
    except Exception:
        return _pipeline_yaml_summary(
            would_write=True, written=False,
        ), "PIPELINE_WRITE_FAILED", None


def _validate_project_config(project_config_path: str | None) -> tuple[Any, str | None]:
    if not project_config_path:
        return None, "PROJECT_CONFIG_REQUIRED"
    try:
        settings = ProjectSettings.from_yaml(project_config_path)
        return settings, None
    except FileNotFoundError:
        return None, "PROJECT_CONFIG_INVALID"
    except Exception:
        return None, "PROJECT_CONFIG_INVALID"


def _check_project_context(
    plan: dict[str, Any],
    project_config_path: str,
    project_id: str | None = None,
) -> tuple[ProjectContext | None, str | None, list[str]]:
    try:
        context = load_project_context(
            project_id=project_id,
            project_config_path=project_config_path,
        )
    except ProjectContextError as exc:
        return None, "PROJECT_CONTEXT_INVALID", [str(exc)]

    errors = validate_plan_project_context(plan, context)
    if errors:
        return context, "PROJECT_CONTEXT_MISMATCH", errors
    return context, None, []


def _project_context_blocked(
    status: str,
    request: ExecuteReviewedRequest,
    errors: list[str],
    context: ProjectContext | None = None,
) -> dict[str, Any]:
    result = _early_blocked(status, request)
    result["errors"] = errors
    result["project_context"] = context.to_dict() if context else None
    return result


def _is_preflight_enabled() -> bool:
    return os.environ.get("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "") == "1"


def _link_fields(
    *,
    reviewed_plan_id: str | None = None,
    run_link_id: str | None = None,
    run_id: str | None = None,
    pipeline_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    return {
        "reviewed_plan_id": reviewed_plan_id,
        "run_link_id": run_link_id,
        "run_id": run_id,
        "pipeline_path": pipeline_path,
        "summary_path": summary_path,
    }


def _with_link_fields(result: dict[str, Any], **fields: str | None) -> dict[str, Any]:
    result.update(_link_fields(**fields))
    return result


def _reviewed_plan_error_status(exc: ReviewedPlanStoreError) -> str:
    code = str(exc).partition(":")[0].strip()
    return code if code.startswith("REVIEWED_PLAN_") else "REVIEWED_PLAN_INVALID"


# ── Main endpoint ────────────────────────────────────────────────────────────

@router.post("/api/plans/execute-reviewed")
def api_execute_reviewed(request: ExecuteReviewedRequest) -> dict[str, Any]:
    """Validate (and optionally execute) a reviewed plan.

    dry_run=true  → readiness check only.
    dry_run=false → safe execution preflight + gated execution
                    (safe allowlist only).
    """
    plan = request.plan

    # ═══════════════════════════════════════════════════════════════════════════
    # dry_run=false → execution preflight (M5-T015) + gated execution (M5-T016)
    # ═══════════════════════════════════════════════════════════════════════════
    if request.dry_run is not True:
        # 1. Env var gate
        if not _is_preflight_enabled():
            return _early_blocked("REVIEWED_EXECUTION_DISABLED", request)

        # 2. Confirm execution
        if not request.confirm_execution:
            return _early_blocked("CONFIRMATION_REQUIRED", request)

        # 3. Audit required
        if not request.persist_audit:
            return _early_blocked("AUDIT_REQUIRED", request)

        # 4. Project config validation
        settings, pc_error = _validate_project_config(request.project_config_path)
        if pc_error:
            return _early_blocked(pc_error, request)

        context, context_status, context_errors = _check_project_context(
            plan,
            request.project_config_path,
            request.project_id,
        )
        if context_status:
            return _project_context_blocked(
                context_status,
                request,
                context_errors,
                context,
            )

        reviewed_plan: ReviewedPlanRecord | None = None
        if context and context.source == "created":
            try:
                reviewed_plan = resolve_reviewed_plan_for_execution(
                    context,
                    plan,
                    request.reviewed_plan_id,
                )
            except ReviewedPlanStoreError as exc:
                return _with_link_fields(
                    _project_context_blocked(
                        _reviewed_plan_error_status(exc),
                        request,
                        [str(exc)],
                        context,
                    ),
                    reviewed_plan_id=request.reviewed_plan_id,
                )

        # 5. Re-validate plan
        validation = validate_plan(plan).to_dict()
        if not validation.get("ok"):
            result = {
                "ok": False,
                "status": "VALIDATION_FAILED",
                "dry_run": False,
                "would_execute": False,
                "execution_allowed": False,
                "validation": validation,
                "approval_gate": None,
                "adapter": None,
                "pipeline_yaml": _pipeline_yaml_default(),
                "plan_summary": _plan_summary(plan, validation),
                "project_config_path": request.project_config_path,
                "execution": _execution_meta(),
            }
            result["audit"] = _write_audit(
                "execution_blocked", plan, validation, request.approval,
                None, result, request.actor, request,
            )
            return result

        # 6. Re-check approval gate
        gate = check_approval_gate(plan, validation, request.approval).to_dict()
        if not gate.get("execution_allowed"):
            result = {
                "ok": False,
                "status": "APPROVAL_GATE_BLOCKED",
                "dry_run": False,
                "would_execute": False,
                "execution_allowed": False,
                "validation": validation,
                "approval_gate": gate,
                "adapter": None,
                "pipeline_yaml": _pipeline_yaml_default(),
                "plan_summary": _plan_summary(plan, validation),
                "project_config_path": request.project_config_path,
                "execution": _execution_meta(),
            }
            result["audit"] = _write_audit(
                "execution_blocked", plan, validation, request.approval,
                gate, result, request.actor, request,
            )
            return result

        # 7. Plan adapter
        adapter = adapt_reviewed_plan(plan)
        if not adapter.ok:
            return _blocked_result("PLAN_ADAPTER_FAILED", plan, validation, gate, adapter, request)
        if _is_policy_blocked(adapter.policy):
            return _blocked_result("EXECUTION_POLICY_BLOCKED", plan, validation, gate, adapter, request)

        # 8. Safe allowlist check (M5-T016)
        allowlist_error = _check_safe_allowlist(adapter.policy)
        if allowlist_error:
            result = {
                "ok": False,
                "status": "SAFE_EXECUTION_POLICY_BLOCKED",
                "dry_run": False,
                "would_execute": False,
                "execution_allowed": False,
                "validation": validation,
                "approval_gate": gate,
                "adapter": _adapter_summary(adapter),
                "pipeline_yaml": _pipeline_yaml_default(),
                "plan_summary": _plan_summary(plan, validation),
                "project_config_path": request.project_config_path,
                "execution": _execution_meta(),
            }
            result["audit"] = _write_audit(
                "execution_blocked", plan, validation, request.approval,
                gate, result, request.actor, request,
            )
            return result

        run_link_id: str | None = None
        linked_run_id: str | None = None
        if reviewed_plan is not None:
            run_link_id, linked_run_id = new_run_identity()
            pipeline = adapter.pipeline
            execution_config = pipeline.setdefault("execution", {}) if pipeline else None
            if not isinstance(execution_config, dict):
                return _with_link_fields(
                    _blocked_result(
                        "PLAN_ADAPTER_FAILED",
                        plan,
                        validation,
                        gate,
                        adapter,
                        request,
                    ),
                    reviewed_plan_id=reviewed_plan.reviewed_plan_id,
                    run_link_id=run_link_id,
                    run_id=linked_run_id,
                )
            execution_config["run_id"] = linked_run_id

        # 9. Pipeline YAML required for execution
        if not request.write_pipeline_yaml:
            result = {
                "ok": False,
                "status": "PIPELINE_YAML_REQUIRED",
                "dry_run": False,
                "would_execute": False,
                "execution_allowed": False,
                "validation": validation,
                "approval_gate": gate,
                "adapter": _adapter_summary(adapter),
                "pipeline_yaml": _pipeline_yaml_summary(would_write=True, written=False),
                "plan_summary": _plan_summary(plan, validation),
                "project_config_path": request.project_config_path,
                "execution": _execution_meta(),
            }
            result["audit"] = _write_audit(
                "execution_blocked", plan, validation, request.approval,
                gate, result, request.actor, request,
            )
            return _with_link_fields(
                result,
                reviewed_plan_id=reviewed_plan.reviewed_plan_id if reviewed_plan else None,
                run_link_id=run_link_id,
                run_id=linked_run_id,
            )

        # 10. Write pipeline YAML
        py_info, writer_status, written_path = _try_write_pipeline_yaml(
            adapter,
            request,
            reviewed_plan.plan_hash if reviewed_plan else None,
        )
        if writer_status is not None:
            result = {
                "ok": False,
                "status": writer_status,
                "dry_run": False,
                "would_execute": False,
                "execution_allowed": False,
                "validation": validation,
                "approval_gate": gate,
                "adapter": _adapter_summary(adapter),
                "pipeline_yaml": py_info,
                "plan_summary": _plan_summary(plan, validation),
                "project_config_path": request.project_config_path,
                "execution": _execution_meta(),
            }
            result["audit"] = _write_audit(
                "execution_blocked", plan, validation, request.approval,
                gate, result, request.actor, request,
            )
            return _with_link_fields(
                result,
                reviewed_plan_id=reviewed_plan.reviewed_plan_id if reviewed_plan else None,
                run_link_id=run_link_id,
                run_id=linked_run_id,
            )

        if reviewed_plan is not None:
            assert run_link_id is not None
            assert linked_run_id is not None
            assert written_path is not None
            run_link = build_run_link(
                project_id=reviewed_plan.project_id,
                reviewed_plan_id=reviewed_plan.reviewed_plan_id,
                run_link_id=run_link_id,
                run_id=linked_run_id,
                project_config_path=reviewed_plan.project_config_path,
                pipeline_path=str(written_path),
            )
            try:
                mock_store.add_run_link(run_link)
            except Exception as exc:
                return _with_link_fields(
                    {
                        "ok": False,
                        "status": "RUN_LINK_WRITE_FAILED",
                        "dry_run": False,
                        "would_execute": False,
                        "execution_allowed": False,
                        "validation": validation,
                        "approval_gate": gate,
                        "adapter": _adapter_summary(adapter),
                        "pipeline_yaml": py_info,
                        "plan_summary": _plan_summary(plan, validation),
                        "project_config_path": request.project_config_path,
                        "execution": _execution_meta(),
                        "audit": _no_audit(),
                        "errors": [f"RUN_LINK_WRITE_FAILED: {exc}"],
                    },
                    reviewed_plan_id=reviewed_plan.reviewed_plan_id,
                    run_link_id=run_link_id,
                    run_id=linked_run_id,
                    pipeline_path=str(written_path),
                )

        # 11. Audit record → write BEFORE executor
        preflight_result = {
            "ok": True,
            "status": "EXECUTION_PREFLIGHT_READY",
            "dry_run": False,
            "would_execute": True,
            "execution_allowed": True,
            "validation": validation,
            "approval_gate": gate,
            "adapter": _adapter_summary(adapter),
            "pipeline_yaml": py_info,
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }
        audit_info = _write_audit(
            "execution_requested", plan, validation, request.approval,
            gate, preflight_result, request.actor, request,
        )
        if not audit_info.get("persisted"):
            result = dict(preflight_result)
            result["ok"] = False
            result["status"] = "AUDIT_WRITE_FAILED"
            result["would_execute"] = False
            result["execution_allowed"] = False
            result["audit"] = audit_info
            if run_link_id:
                try:
                    mock_store.update_run_link(
                        run_link_id,
                        status="BLOCKED",
                        payload={"audit": audit_info},
                    )
                except Exception as exc:
                    result["warnings"] = [f"RUN_LINK_UPDATE_FAILED: {exc}"]
            return _with_link_fields(
                result,
                reviewed_plan_id=reviewed_plan.reviewed_plan_id if reviewed_plan else None,
                run_link_id=run_link_id,
                run_id=linked_run_id,
                pipeline_path=str(written_path) if written_path else None,
            )

        if run_link_id and reviewed_plan:
            try:
                mock_store.update_run_link(
                    run_link_id,
                    status="RUNNING",
                    audit_id=str(audit_info.get("audit_id") or "") or None,
                    payload={"audit": audit_info},
                )
                mock_store.update_reviewed_plan(
                    reviewed_plan.reviewed_plan_id,
                    approval_status="APPROVED",
                    execution_status="RUNNING",
                    last_audit_id=str(audit_info.get("audit_id") or "") or None,
                    last_execution_id=run_link_id,
                )
            except Exception as exc:
                try:
                    mock_store.update_run_link(
                        run_link_id,
                        status="BLOCKED",
                        warnings=[f"RUN_LINK_UPDATE_FAILED: {exc}"],
                    )
                except Exception:
                    pass
                result = dict(preflight_result)
                result.update(
                    {
                        "ok": False,
                        "status": "RUN_LINK_UPDATE_FAILED",
                        "would_execute": False,
                        "execution_allowed": False,
                        "audit": audit_info,
                        "errors": [f"RUN_LINK_UPDATE_FAILED: {exc}"],
                    }
                )
                return _with_link_fields(
                    result,
                    reviewed_plan_id=reviewed_plan.reviewed_plan_id,
                    run_link_id=run_link_id,
                    run_id=linked_run_id,
                    pipeline_path=str(written_path) if written_path else None,
                )

        # 12. Call executor — FIRST TIME in M5 series
        try:
            executor_result = run_pipeline(
                project_config_path=request.project_config_path,
                pipeline_path=str(written_path),
            )
        except Exception as exc:
            if run_link_id and reviewed_plan:
                try:
                    mock_store.update_run_link(
                        run_link_id,
                        status="FAILED",
                        payload={"audit": audit_info, "error": str(exc)},
                    )
                    mock_store.update_reviewed_plan(
                        reviewed_plan.reviewed_plan_id,
                        execution_status="FAILED",
                        last_execution_id=run_link_id,
                    )
                except Exception:
                    pass
            result = {
                "ok": False,
                "status": "EXECUTION_FAILED",
                "dry_run": False,
                "would_execute": False,
                "execution_allowed": False,
                "validation": validation,
                "approval_gate": gate,
                "adapter": _adapter_summary(adapter),
                "pipeline_yaml": py_info,
                "plan_summary": _plan_summary(plan, validation),
                "project_config_path": request.project_config_path,
                "execution": _execution_meta(executor_called=True),
                "audit": audit_info,
                "errors": [str(exc)],
            }
            return _with_link_fields(
                result,
                reviewed_plan_id=reviewed_plan.reviewed_plan_id if reviewed_plan else None,
                run_link_id=run_link_id,
                run_id=linked_run_id,
                pipeline_path=str(written_path) if written_path else None,
            )

        # 13. Executor returned — success
        executor_run_id = executor_result.get("run_id") if isinstance(executor_result, dict) else None
        summary_path = (
            executor_result.get("summary_path")
            if isinstance(executor_result, dict)
            else None
        )
        response_warnings: list[str] = []
        if linked_run_id and executor_run_id and executor_run_id != linked_run_id:
            response_warnings.append(
                "EXECUTOR_RUN_ID_MISMATCH: executor returned a different run_id"
            )
        if run_link_id and reviewed_plan:
            execution_status = (
                str(executor_result.get("status") or "SUBMITTED")
                if isinstance(executor_result, dict)
                else "SUBMITTED"
            )
            try:
                mock_store.update_run_link(
                    run_link_id,
                    status=execution_status,
                    summary_path=str(summary_path) if summary_path else None,
                    payload={"audit": audit_info, "executor_result": executor_result},
                    warnings=response_warnings,
                )
                mock_store.update_reviewed_plan(
                    reviewed_plan.reviewed_plan_id,
                    execution_status=execution_status,
                    last_execution_id=run_link_id,
                )
            except Exception as exc:
                response_warnings.append(f"RUN_LINK_FINALIZE_FAILED: {exc}")
        result = {
            "ok": True,
            "status": "EXECUTION_SUBMITTED",
            "dry_run": False,
            "would_execute": True,
            "execution_allowed": True,
            "validation": validation,
            "approval_gate": gate,
            "adapter": _adapter_summary(adapter),
            "pipeline_yaml": py_info,
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(
                submitted=True,
                run_id=linked_run_id or executor_run_id,
                executor_called=True,
            ),
            "executor_result": executor_result,
            "audit": audit_info,
            "warnings": response_warnings,
        }
        return _with_link_fields(
            result,
            reviewed_plan_id=reviewed_plan.reviewed_plan_id if reviewed_plan else None,
            run_link_id=run_link_id,
            run_id=linked_run_id or executor_run_id,
            pipeline_path=str(written_path) if written_path else None,
            summary_path=str(summary_path) if summary_path else None,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # dry_run=true → readiness check (M5-T005..T014 — unchanged behaviour)
    # ═══════════════════════════════════════════════════════════════════════════

    # ── 1. Re-validate plan ──
    if request.project_config_path:
        settings, pc_error = _validate_project_config(request.project_config_path)
        if pc_error:
            return _early_blocked(pc_error, request)
        context, context_status, context_errors = _check_project_context(
            plan,
            request.project_config_path,
            request.project_id,
        )
        if context_status:
            return _project_context_blocked(
                context_status,
                request,
                context_errors,
                context,
            )

    validation = validate_plan(plan).to_dict()

    if not validation.get("ok"):
        result = {
            "ok": False,
            "status": "VALIDATION_FAILED",
            "dry_run": True,
            "would_execute": False,
            "execution_allowed": False,
            "validation": validation,
            "approval_gate": None,
            "adapter": None,
            "pipeline_yaml": _pipeline_yaml_default(),
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }
        result["audit"] = _write_audit(
            "execution_blocked", plan, validation, request.approval,
            None, result, request.actor, request,
        )
        return result

    # ── 2. Re-check approval gate ──
    gate = check_approval_gate(plan, validation, request.approval).to_dict()

    if not gate.get("execution_allowed"):
        result = {
            "ok": False,
            "status": "APPROVAL_GATE_BLOCKED",
            "dry_run": True,
            "would_execute": False,
            "execution_allowed": False,
            "validation": validation,
            "approval_gate": gate,
            "adapter": None,
            "pipeline_yaml": _pipeline_yaml_default(),
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }
        result["audit"] = _write_audit(
            "execution_blocked", plan, validation, request.approval,
            gate, result, request.actor, request,
        )
        return result

    # ── 3. Plan adapter check ──
    adapter = adapt_reviewed_plan(plan)

    if not adapter.ok:
        return _blocked_result("PLAN_ADAPTER_FAILED", plan, validation, gate, adapter, request)

    if _is_policy_blocked(adapter.policy):
        return _blocked_result("EXECUTION_POLICY_BLOCKED", plan, validation, gate, adapter, request)

    # ── 4. Pipeline writer check ──
    py_info, writer_status, written_path = _try_write_pipeline_yaml(adapter, request)
    if writer_status is not None:
        result = {
            "ok": False,
            "status": writer_status,
            "dry_run": True,
            "would_execute": False,
            "execution_allowed": False,
            "validation": validation,
            "approval_gate": gate,
            "adapter": _adapter_summary(adapter),
            "pipeline_yaml": py_info,
            "plan_summary": _plan_summary(plan, validation),
            "project_config_path": request.project_config_path,
            "execution": _execution_meta(),
        }
        result["audit"] = _write_audit(
            "execution_blocked", plan, validation, request.approval,
            gate, result, request.actor, request,
        )
        return result

    # ── 5. Dry-run OK ──
    result = {
        "ok": True,
        "status": "DRY_RUN_OK",
        "dry_run": True,
        "would_execute": True,
        "execution_allowed": True,
        "validation": validation,
        "approval_gate": gate,
        "adapter": _adapter_summary(adapter),
        "pipeline_yaml": py_info,
        "plan_summary": _plan_summary(plan, validation),
        "project_config_path": request.project_config_path,
        "execution": _execution_meta(),
    }
    result["audit"] = _write_audit(
        "dry_run_checked", plan, validation, request.approval,
        gate, result, request.actor, request,
    )
    return result
