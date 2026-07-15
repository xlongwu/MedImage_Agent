"""Conversion business logic — thin adapter over the existing conversion services.

Each function accepts a ``ProjectStore`` so callers (routes) do not touch the
global ``mock_store`` directly.  The underlying conversion helpers still
reference ``mock_store`` internally; that is a deeper refactor deferred to
a later task.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.api.dependencies import ProjectStore


def _project_dirs(store: ProjectStore, project_id: str) -> tuple[str, str]:
    project = store.get_project(project_id)
    if not project:
        raise ValueError(f"Project not found: {project_id}")
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    return str(metadata.get("project_dir") or ""), str(metadata.get("rawdata_dir") or "")


# ── Dry-run / preflight ───────────────────────────────────────────────────

def run_conversion_dry_run(
    store: ProjectStore,
    project_id: str,
    request: Any,
) -> dict[str, Any]:
    from src.backend.app.services.conversion_planner import plan_conversion
    return plan_conversion(project_id, request)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _blocked_latest_dry_run_response(
    project_id: str,
    message: str,
    *,
    checked_at: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "project_id": project_id,
        "status": "blocked",
        "dry_run": True,
        "checked_at": checked_at or _utc_now(),
        "target_layout": "bids",
        "output_root_name": "converted_bids",
        "output_root_preview": None,
        "source_summaries": [],
        "mapping_preview": [],
        "blocking_issues": [message],
        "warnings": [],
        "next_actions": ["Refresh the conversion dry-run preview for the active project."],
        "safety_flags": {
            "dry_run_only": True,
            "rawdata_read_only": True,
            "no_files_written": True,
            "no_external_tools_executed": True,
            "requires_user_review_before_conversion": True,
            "output_path_is_preview_only": True,
            "restored_from_persisted_review_package": False,
        },
    }


def _normalize_source_summary(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    source_type = str(raw.get("source_type") or "unknown")
    if source_type not in {"dicom", "loose_nifti", "bids", "unknown"}:
        source_type = "unknown"
    return {
        "source_id": str(raw.get("source_id") or raw.get("root") or "source"),
        "source_type": source_type,
        "root": str(raw.get("root") or ""),
        "exists": bool(raw.get("exists", False)),
        "file_count": int(raw.get("file_count") or 0),
        "subject_candidates": [
            str(item) for item in raw.get("subject_candidates", []) if item is not None
        ] if isinstance(raw.get("subject_candidates"), list) else [],
        "series_count": int(raw.get("series_count") or 0),
        "warnings": [str(item) for item in raw.get("warnings", [])]
        if isinstance(raw.get("warnings"), list)
        else [],
    }


def _normalize_mapping_preview(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    source_type = str(raw.get("source_type") or "dicom_series")
    if source_type not in {"dicom_series", "nifti_file"}:
        source_type = "dicom_series"
    confidence = str(raw.get("confidence") or "manual_required")
    if confidence not in {"high", "medium", "low", "manual_required"}:
        confidence = "manual_required"
    warnings_raw = raw.get("warnings", [])
    return {
        "source_path": raw.get("source_path"),
        "source_series_uid": raw.get("source_series_uid"),
        "source_type": source_type,
        "subject_id": raw.get("subject_id"),
        "session_id": raw.get("session_id"),
        "modality": raw.get("modality"),
        "suffix": raw.get("suffix"),
        "task": raw.get("task"),
        "suggested_relative_path": raw.get("suggested_relative_path"),
        "confidence": confidence,
        "warnings": [str(item) for item in warnings_raw] if isinstance(warnings_raw, list) else [],
    }


def run_get_latest_conversion_dry_run(
    store: ProjectStore,
    project_id: str,
) -> dict[str, Any]:
    """Restore the latest persisted dry-run mapping snapshot without executing conversion."""
    project_dir_raw, _rawdata_dir = _project_dirs(store, project_id)
    if not project_dir_raw:
        return _blocked_latest_dry_run_response(
            project_id,
            "Project directory is unavailable; refresh is required before mappings can be shown.",
        )

    project_dir = Path(project_dir_raw).resolve()
    conversion_root = project_dir / "conversion_runs"
    if not conversion_root.exists():
        return _blocked_latest_dry_run_response(
            project_id,
            "No persisted dry-run review package was found; refresh is required.",
        )

    candidates: list[Path] = []
    for run_dir in conversion_root.iterdir():
        if run_dir.is_dir() and (run_dir / "mapping_snapshot.json").exists():
            candidates.append(run_dir)
    candidates.sort(
        key=lambda path: (path / "mapping_snapshot.json").stat().st_mtime,
        reverse=True,
    )

    for run_dir in candidates:
        resolved_run_dir = run_dir.resolve()
        if not _is_relative_to(resolved_run_dir, project_dir):
            continue
        mapping_path = resolved_run_dir / "mapping_snapshot.json"
        preflight_path = resolved_run_dir / "preflight_snapshot.json"
        try:
            mapping_snapshot = _read_json_object(mapping_path)
            preflight_snapshot = _read_json_object(preflight_path) if preflight_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            continue

        mappings_raw = mapping_snapshot.get("mappings", [])
        if not isinstance(mappings_raw, list):
            mappings_raw = []
        mapping_preview = [
            item
            for item in (_normalize_mapping_preview(raw) for raw in mappings_raw)
            if item is not None
        ]
        if not mapping_preview:
            continue

        sources_raw = preflight_snapshot.get("source_summaries", [])
        source_summaries = [
            item
            for item in (_normalize_source_summary(raw) for raw in sources_raw)
            if item is not None
        ] if isinstance(sources_raw, list) else []
        warnings_raw = preflight_snapshot.get("warnings", [])
        blocking_raw = preflight_snapshot.get("blocking_issues", [])
        checked_at = str(
            preflight_snapshot.get("checked_at")
            or mapping_snapshot.get("created_at")
            or datetime.fromtimestamp(mapping_path.stat().st_mtime, timezone.utc).isoformat()
        )
        output_root_name = str(preflight_snapshot.get("output_root_name") or "converted_bids")
        status = str(preflight_snapshot.get("status") or "warning")
        if status not in {"ready", "warning", "blocked", "unknown"}:
            status = "warning"
        return {
            "ok": True,
            "project_id": project_id,
            "status": status,
            "dry_run": True,
            "checked_at": checked_at,
            "target_layout": "bids",
            "output_root_name": output_root_name,
            "output_root_preview": preflight_snapshot.get("output_root_preview"),
            "source_summaries": source_summaries,
            "mapping_preview": mapping_preview,
            "blocking_issues": [str(item) for item in blocking_raw]
            if isinstance(blocking_raw, list)
            else [],
            "warnings": [
                f"Restored dry-run mappings from persisted review package {resolved_run_dir.name}."
            ]
            + ([str(item) for item in warnings_raw] if isinstance(warnings_raw, list) else []),
            "next_actions": [
                "Review restored mappings before using them as approval material.",
                "Refresh dry-run preview if rawdata or project metadata changed.",
            ],
            "safety_flags": {
                "dry_run_only": True,
                "rawdata_read_only": True,
                "no_files_written": True,
                "no_external_tools_executed": True,
                "requires_user_review_before_conversion": True,
                "output_path_is_preview_only": True,
                "restored_from_persisted_review_package": True,
            },
        }

    return _blocked_latest_dry_run_response(
        project_id,
        "Persisted review packages exist but no usable dry-run mapping snapshot was found; refresh is required.",
    )


def run_conversion_preflight(
    store: ProjectStore,
    project_id: str,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    from src.backend.app.services.dicom_conversion_execution import (
        check_native_dicom_converter_availability,
        run_conversion_preflight,
    )
    _project_dirs(store, project_id)  # validate project exists
    preflight = run_conversion_preflight(project_id)
    availability = check_native_dicom_converter_availability()
    return {
        "ok": preflight.ok,
        "project_id": project_id,
        "status": preflight.status,
        "conversion_disabled_by_default": preflight.conversion_disabled_by_default,
        "conversion_backend": "medimage-native",
        "native_converter_available": availability["found"],
        "native_converter_status": availability["status"],
        "native_converter_version": availability["version"],
        "native_dependency_versions": availability["versions"],
        # Deprecated compatibility fields: the external converter is not used.
        "dcm2niix_available": False,
        "dcm2niix_status": "not_used",
        "dcm2niix_path": None,
        "dcm2niix_version": None,
        "env_enabled": preflight.env_enabled,
        "missing_env_flags": preflight.missing_env_flags,
        "approval_required": preflight.approval_required,
        "audit_required": preflight.audit_required,
        "output_root_preview": preflight.output_root_preview,
        "output_dir_safe": preflight.output_dir_safe,
        "mapping_count": preflight.mapping_count,
        "mappings": [
            {
                "subject_id": m.subject_id,
                "modality": m.modality,
                "suffix": m.suffix,
                "task": m.task,
                "source_path": m.source_path,
                "suggested_relative_path": m.suggested_relative_path,
                "confidence": m.confidence,
            }
            for m in preflight.mappings
        ],
        "command_templates": [
            {
                "tool": t.tool,
                "executable": t.executable,
                "input_dir": t.input_dir,
                "output_dir": t.output_dir,
                "filename_pattern": t.filename_pattern,
                "compress": t.compress,
                "bids_sidecar": t.bids_sidecar,
                "create_bids": t.create_bids,
                "command_preview": t.command_preview,
            }
            for t in preflight.command_templates
        ],
        "warnings": preflight.warnings,
        "errors": preflight.errors,
        "blocking_issues": preflight.blocking_issues,
        "safety_flags": preflight.safety_flags.model_dump(),
    }


# ── Approval / plan persistence ──────────────────────────────────────────

def run_conversion_persist_plan(
    store: ProjectStore,
    project_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    from src.backend.app.schemas.dicom_conversion_approval import (
        DicomConversionApprovalRecord,
        evaluate_conversion_approval_gate,
    )
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )
    project_dir, rawdata_dir = _project_dirs(store, project_id)

    approval = DicomConversionApprovalRecord(
        approval_id=body.get("approval_id", ""),
        project_id=project_id,
        status=body.get("status", "ready_for_review"),
        approved=body.get("approved", False),
        approved_by=body.get("approved_by", ""),
        approved_at=body.get("approved_at", ""),
        mapping_ids=body.get("mapping_ids", []),
        mappings_reviewed=body.get("mappings_reviewed", False),
        output_root=body.get("output_root", ""),
        output_root_confirmed=body.get("output_root_confirmed", False),
        output_root_under_project=body.get("output_root_under_project", False),
        output_root_not_rawdata=body.get("output_root_not_rawdata", False),
        overwrite_policy=body.get("overwrite_policy", "fail_if_exists"),
        rawdata_read_only_confirmed=body.get("rawdata_read_only_confirmed", False),
        command_templates_reviewed=body.get("command_templates_reviewed", False),
        no_shell_string_confirmed=body.get("no_shell_string_confirmed", False),
        dcm2niix_availability_confirmed=body.get("dcm2niix_availability_confirmed", False),
        env_flags_confirmed=body.get("env_flags_confirmed", False),
        rollback_policy_acknowledged=body.get("rollback_policy_acknowledged", False),
        clinical_use_prohibited_acknowledged=body.get("clinical_use_prohibited_acknowledged", False),
        external_tool_acknowledgement=body.get("external_tool_acknowledgement", False),
        risk_acknowledgement=body.get("risk_acknowledgement", False),
        confirm_execution=body.get("confirm_execution", False),
    )
    result = persist_conversion_plan(
        project_id=project_id,
        approval_record=approval,
        preflight_snapshot=body.get("preflight_snapshot"),
        mappings=body.get("mappings"),
        command_templates=body.get("command_templates"),
        safety_flags=body.get("safety_flags", {}),
        project_dir=project_dir,
        rawdata_dir=rawdata_dir,
        overwrite_policy=body.get("overwrite_policy", "fail_if_exists"),
        preflight_ok=body.get("preflight_ok", True),
    )
    return result.model_dump()


def run_get_conversion_review_package(
    store: ProjectStore,
    project_id: str,
    conversion_run_id: str,
) -> dict[str, Any]:
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    project_dir, rawdata_dir = _project_dirs(store, project_id)
    result = read_conversion_review_package(
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        project_dir=project_dir,
        rawdata_dir=rawdata_dir,
    )
    return result.model_dump()


def run_export_conversion_review_package(
    store: ProjectStore,
    project_id: str,
    conversion_run_id: str,
) -> dict[str, Any]:
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, rawdata_dir = _project_dirs(store, project_id)
    result = export_conversion_review_package(
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        project_dir=project_dir,
        rawdata_dir=rawdata_dir,
    )
    return result.model_dump()


def run_get_conversion_release_readiness(
    store: ProjectStore,
    project_id: str,
    conversion_run_id: str,
) -> dict[str, Any]:
    from src.backend.app.services.dicom_conversion_release_readiness import (
        evaluate_conversion_release_readiness,
    )
    project_dir, _ = _project_dirs(store, project_id)
    output_root = f"{project_dir}/converted_bids" if project_dir else ""
    report = evaluate_conversion_release_readiness(
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        output_root=output_root,
    )
    return report.model_dump()


# ── Public execute ────────────────────────────────────────────────────────

def run_conversion_execute(
    store: ProjectStore,
    project_id: str,
    request_raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Flag-gated public DICOM conversion — full gating logic preserved.

    This is a verbatim extraction of the execute body from dashboard_routes
    with ``mock_store`` replaced by the injected ``store``.
    """
    from datetime import datetime, timezone

    from src.backend.app.schemas.dicom_conversion_public_execution import (
        DicomConversionPublicExecutionRequest,
        DicomConversionPublicExecutionResponse,
        DicomConversionPublicExecutionSafetyFlags,
        validate_public_execution_env_flags,
        validate_public_execution_request_acknowledgements,
    )
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        is_release_approval_complete,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    from src.backend.app.services.dicom_conversion_release_readiness import (
        evaluate_conversion_release_readiness,
    )
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        validate_output_root_not_under_rawdata,
        validate_output_root_under_project,
    )

    project = store.get_project(project_id)
    if not project:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=(request_raw or {}).get("conversion_run_id", ""),
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
            ),
        ).model_dump()

    project_dir, rawdata_dir = _project_dirs(store, project_id)

    # ── 0. Parse request ────────────────────────────────────────────────
    try:
        body = request_raw or {}
        req = DicomConversionPublicExecutionRequest(**body)
    except Exception as exc:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            errors=[f"Invalid request body: {exc}"],
            blocking_issues=[f"Request validation failed: {exc}"],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(),
        ).model_dump()

    # ── 1. Env flag check ───────────────────────────────────────────────
    current_env = dict(os.environ)
    env_ok, missing_env = validate_public_execution_env_flags(current_env)
    if not env_ok:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="disabled",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=[
                f"Public conversion endpoint disabled: {len(missing_env)} "
                f"env flag(s) missing: {', '.join(missing_env)}."
            ],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                env_flags_missing=True,
                conversion_disabled_by_default=True,
            ),
        ).model_dump()

    # ── 2. Operator confirmations ───────────────────────────────────────
    ok_confirm, missing_confirm = validate_public_execution_request_acknowledgements(req)
    if not ok_confirm:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=[
                f"Operator confirmations missing: {', '.join(missing_confirm)}."
            ],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
            ),
        ).model_dump()

    # ── 3. Project lookup (already done above) ──────────────────────────

    if not project_dir:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=["Project directory not configured."],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
            ),
        ).model_dump()

    # ── 4. Release approval validation ──────────────────────────────────
    from src.backend.app.services.dicom_conversion_release_approval import (
        read_release_approval,
    )
    approval = read_release_approval(
        project_id=project_id,
        conversion_run_id=req.conversion_run_id,
        project_dir=project_dir,
    )
    approval_ok = approval.approved and not approval.blocked
    approval_status = approval.status
    if not approval_ok:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=approval.blocking_issues or [
                f"Release approval is not valid: status={approval_status}."
            ],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                release_approval_obtained=False,
            ),
        ).model_dump()

    # ── 5. Release readiness validation ─────────────────────────────────
    output_root = f"{project_dir}/converted_bids"
    readiness = evaluate_conversion_release_readiness(
        project_id=project_id,
        conversion_run_id=req.conversion_run_id,
        output_root=output_root,
    )
    readiness_allows_execution = readiness.status in {
        "ready_for_human_release_review", "warning"
    }
    if not readiness_allows_execution:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=readiness.blocking_issues or [
                f"Release readiness is '{readiness.status}', "
                f"must be 'ready_for_human_release_review'."
            ],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                release_readiness_ready=False,
                gates_32_of_32=(readiness.gates_met >= readiness.gates_total),
            ),
        ).model_dump()

    # ── 6. GO/NO-GO gate validation ─────────────────────────────────────
    gates_ok = readiness.gates_met >= readiness.gates_total
    if not gates_ok:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=[
                f"Not all safety gates met: {readiness.gates_met}/{readiness.gates_total}."
            ],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                gates_32_of_32=False,
            ),
        ).model_dump()

    # ── 7. Approval/audit package validation ────────────────────────────
    pkg = read_conversion_review_package(
        project_id, req.conversion_run_id,
        project_dir=project_dir, rawdata_dir=rawdata_dir,
    )
    if not pkg.ok:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=[f"Review package not readable: {pkg.errors}"],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                approval_audit_package_present=False,
            ),
        ).model_dump()

    # ── 8. Rawdata checksum-before validation ───────────────────────────
    checksum_before_path = next(
        (f.path for f in pkg.files if f.kind == "rawdata_checksum_before"), ""
    )
    if not checksum_before_path or not __import__("pathlib").Path(checksum_before_path).exists():
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=["Rawdata checksum-before snapshot does not exist."],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                rawdata_checksum_before_exists=False,
            ),
        ).model_dump()

    # ── 9. Rollback plan validation ─────────────────────────────────────
    rollback_plan_path = next(
        (f.path for f in pkg.files if f.kind == "rollback_plan_dry_run"), ""
    )
    if not rollback_plan_path or not __import__("pathlib").Path(rollback_plan_path).exists():
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=["Rollback plan does not exist."],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                rollback_plan_exists=False,
            ),
        ).model_dump()

    # ── 10. Disk-space check ────────────────────────────────────────────
    if not readiness.disk_space.ok:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=[
                f"Disk space insufficient: {readiness.disk_space.free_bytes} bytes free, "
                f"{readiness.disk_space.estimated_required_bytes} estimated required."
            ],
            errors=readiness.disk_space.errors,
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                disk_space_passed=False,
            ),
        ).model_dump()

    # ── 11. Output root safety ──────────────────────────────────────────
    out_safe = True
    out_blockers: list[str] = []
    if not validate_output_root_under_project(output_root, project_dir):
        out_safe = False
        out_blockers.append(
            f"Output root {output_root} is not under project directory {project_dir}."
        )
    if rawdata_dir and not validate_output_root_not_under_rawdata(output_root, rawdata_dir):
        out_safe = False
        out_blockers.append(
            f"Output root {output_root} must not be inside rawdata directory {rawdata_dir}."
        )
    if not out_safe:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=out_blockers,
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                output_root_safe=False,
            ),
        ).model_dump()

    # ── 12. SPM/DPABI/MATLAB guard ──────────────────────────────────────
    matlab_flag = os.environ.get("MEDIMAGE_MATLAB_EXECUTION_ENABLED", "")
    spm_flag = os.environ.get("MEDIMAGE_SPM_EXECUTION_ENABLED", "")
    if matlab_flag == "1" or spm_flag == "1":
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            blocking_issues=[
                "SPM/DPABI/MATLAB execution is not permitted during public conversion."
            ],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                conversion_disabled_by_default=True,
                spm_dpabi_matlab_disabled=False,
            ),
        ).model_dump()

    # ── 13. Execute ─────────────────────────────────────────────────────
    started_at = datetime.now(timezone.utc).isoformat()
    execution_id = (
        f"pubexec-{project_id}-{req.conversion_run_id}"
        f"-{int(datetime.now(timezone.utc).timestamp())}"
    )
    try:
        internal_result = run_internal_user_dicom_conversion_from_persisted_package(
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            env=current_env,
            project_dir=project_dir,
            rawdata_dir=rawdata_dir,
        )
    except Exception as exc:
        return DicomConversionPublicExecutionResponse(
            ok=False,
            status="failed",
            project_id=project_id,
            conversion_run_id=req.conversion_run_id,
            execution_id=execution_id,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            output_root=output_root,
            errors=[f"Internal execution failed: {exc}"],
            safety_flags=DicomConversionPublicExecutionSafetyFlags(
                env_flags_missing=False,
                public_execution_allowed=True,
                release_approval_obtained=True,
                release_readiness_ready=True,
                gates_32_of_32=True,
                approval_audit_package_present=True,
                rawdata_checksum_before_exists=True,
                rollback_plan_exists=True,
                disk_space_passed=True,
                output_root_safe=True,
                rawdata_read_only=True,
                spm_dpabi_matlab_disabled=True,
                full_preprocessing_disabled=True,
                human_release_approval_required=True,
                no_shell_execution=True,
                conversion_disabled_by_default=False,
            ),
        ).model_dump()

    finished_at = datetime.now(timezone.utc).isoformat()
    internal_status = getattr(internal_result, "status", "failed")
    status_map = {
        "succeeded": "succeeded",
        "partial": "partial",
        "warning": "partial",
        "disabled": "blocked",
        "blocked": "blocked",
    }
    public_status = status_map.get(internal_status, "failed")

    run_dir = f"{project_dir}/conversion_runs/{req.conversion_run_id}"
    cs_after = f"{run_dir}/rawdata_checksum_after.json"
    cs_comp = f"{run_dir}/rawdata_checksum_comparison.json"
    checksum_verified = __import__("pathlib").Path(cs_comp).exists() and __import__("pathlib").Path(cs_after).exists()

    response = DicomConversionPublicExecutionResponse(
        ok=getattr(internal_result, "ok", False),
        status=public_status,
        project_id=project_id,
        conversion_run_id=req.conversion_run_id,
        execution_id=execution_id,
        started_at=started_at,
        finished_at=finished_at,
        output_root=output_root,
        output_manifest_path=getattr(internal_result, "manifest_path", None) or "",
        execution_provenance_path=getattr(internal_result, "provenance_path", None) or "",
        audit_execution_start_path=f"{run_dir}/audit_execution_start.json",
        audit_execution_final_path=f"{run_dir}/audit_execution_final.json",
        checksum_before_path=checksum_before_path,
        checksum_after_path=cs_after,
        checksum_comparison_path=cs_comp,
        checksum_verified=checksum_verified,
        rollback_plan_path=rollback_plan_path,
        rollback_result_path=f"{run_dir}/rollback_result.json",
        warnings=getattr(internal_result, "warnings", []) or [],
        errors=getattr(internal_result, "errors", []) or [],
        blocking_issues=getattr(internal_result, "blocking_issues", []) or [],
        safety_flags=DicomConversionPublicExecutionSafetyFlags(
            conversion_disabled_by_default=False,
            env_flags_missing=False,
            public_execution_allowed=True,
            release_approval_obtained=True,
            release_readiness_ready=readiness_allows_execution,
            gates_32_of_32=True,
            approval_audit_package_present=True,
            rawdata_checksum_before_exists=True,
            rollback_plan_exists=True,
            disk_space_passed=True,
            output_root_safe=True,
            rawdata_read_only=True,
            spm_dpabi_matlab_disabled=True,
            full_preprocessing_disabled=True,
            human_release_approval_required=True,
            no_shell_execution=True,
        ),
    )
    return response.model_dump()
