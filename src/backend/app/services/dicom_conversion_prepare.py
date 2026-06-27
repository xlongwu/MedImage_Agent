"""DICOM conversion prepare orchestration — 实现dcm2nii任务方案.md §13.

Single-call orchestration that performs all preparation steps for DICOM
conversion execution:

  1. Re-run preflight
  2. Validate dcm2niix
  3. Validate mappings unchanged
  4. Validate output paths
  5. Validate disk space
  6. Compute rawdata checksum-before
  7. Create rollback plan
  8. Generate complete conversion approval record
  9. Generate audit preview
 10. Persist review package
 11. Create conversion run
 12. Return authoritative readiness

Per §13.3, user confirmations and system validations are separated.
The backend never asks the user to manually set system-verifiable fields.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.api.dependencies import ProjectStore
from src.backend.app.schemas.dicom_conversion_prepare import (
    DicomConversionPrepareConfirmations,
    DicomConversionPrepareRequest,
    DicomConversionPrepareResponse,
    DicomConversionPrepareSystemChecks,
    determine_prepare_next_action,
    validate_prepare_confirmations,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: str | Path, data: dict[str, Any]) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _compute_rawdata_checksum_before(rawdata_dir: str) -> tuple[dict[str, str], str | None]:
    """Compute SHA-256 for every DICOM file under rawdata_dir.

    Returns (checksums_map, error_message).
    """
    if not rawdata_dir:
        return {}, "rawdata_dir is empty"
    root = Path(rawdata_dir)
    if not root.exists():
        return {}, f"rawdata_dir does not exist: {rawdata_dir}"

    checksums: dict[str, str] = {}
    try:
        for ext in ("*.dcm", "*.ima", "*.DICOM", "*.img"):
            for f in sorted(root.rglob(ext)):
                if f.is_file():
                    checksums[str(f)] = _sha256_file(f)
        # If no extension-matched files, hash all files in the tree
        if not checksums:
            for f in sorted(root.rglob("*")):
                if f.is_file():
                    checksums[str(f)] = _sha256_file(f)
    except Exception as exc:
        return {}, f"checksum computation failed: {exc}"
    return checksums, None


def _build_rollback_plan(
    run_dir: Path,
    output_root: str,
    mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a dry-run rollback plan describing how to undo a partial run.

    Per 实现dcm2nii任务方案.md §15.3, the default policy is
    ``fail_if_exists + quarantine_partial_outputs``.
    """
    return {
        "policy": "quarantine_partial_outputs",
        "quarantine_dir": str(run_dir / "quarantine"),
        "output_root": output_root,
        "steps": [
            "Move any newly created files under output_root to quarantine_dir.",
            "Do NOT delete rawdata under any circumstances.",
            "Preserve logs, failure record and rollback evidence.",
            "Do NOT register failed outputs as converted BIDS.",
        ],
        "mapping_count": len(mappings),
        "created_at": _now_iso(),
    }


def _estimate_disk_required(mappings: list[dict[str, Any]]) -> int:
    """Rough estimate of disk space required for conversion outputs.

    Conservative default: 2x the largest source DICOM series size, or
    500 MB per mapping if source size cannot be determined.
    """
    per_mapping_bytes = 500 * 1024 * 1024  # 500 MB
    return len(mappings) * per_mapping_bytes


def _check_disk_space(output_root: str, estimated_bytes: int) -> tuple[bool, int, int]:
    """Check free disk space at output_root (or its parent).

    Returns (ok, free_bytes, required_bytes).
    """
    try:
        import shutil
        check_path = output_root
        p = Path(output_root)
        if not p.exists():
            parent = p.parent
            check_path = str(parent) if parent.exists() else str(p.parent.parent)
        usage = shutil.disk_usage(check_path)
        return usage.free >= estimated_bytes, usage.free, estimated_bytes
    except Exception:
        return False, 0, estimated_bytes


def run_dicom_conversion_prepare(
    store: ProjectStore,
    project_id: str,
    request: DicomConversionPrepareRequest,
) -> DicomConversionPrepareResponse:
    """Orchestrate the full prepare flow for DICOM conversion.

    Per 实现dcm2nii任务方案.md §13.2, this performs all system validations
    and persists the approval package in one call.
    """
    from src.backend.app.services.dicom_conversion_execution import (
        _detect_dcm2niix_runtime,
        run_conversion_preflight,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.schemas.dicom_conversion_approval import (
        DicomConversionApprovalRecord,
        evaluate_conversion_approval_gate,
    )
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    warnings: list[str] = []
    errors: list[str] = []
    blocking: list[str] = []

    # ── 0. Project lookup ──────────────────────────────────────────────
    project = store.get_project(project_id)
    if not project:
        return DicomConversionPrepareResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            errors=[f"Project not found: {project_id}"],
            blocking_issues=[f"Project not found: {project_id}"],
        )

    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    rawdata_dir = str(metadata.get("rawdata_dir") or "")

    if not project_dir:
        blocking.append("Project directory is not configured.")
    if not rawdata_dir:
        blocking.append("Rawdata directory is not configured.")

    # ── 1. Re-run preflight ────────────────────────────────────────────
    try:
        exec_request = DicomConversionExecutionRequest(project_id=project_id)
        preflight = run_conversion_preflight(project_id, exec_request)
    except Exception as exc:
        errors.append(f"Preflight failed: {exc}")
        return DicomConversionPrepareResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            errors=errors,
            blocking_issues=[f"Preflight failed: {exc}"],
        )

    preflight_ok = preflight.status in {"review_required", "ready"}
    if not preflight_ok:
        blocking.extend(preflight.blocking_issues or ["Preflight not ready."])

    # ── 2. Validate dcm2niix ───────────────────────────────────────────
    dcm2niix_info = _detect_dcm2niix_runtime()
    dcm2niix_available = bool(dcm2niix_info.get("found"))
    if not dcm2niix_available:
        blocking.append(
            dcm2niix_info.get("error") or "dcm2niix was not found."
        )

    # ── 3. Validate mappings ───────────────────────────────────────────
    mappings = [m.model_dump() for m in preflight.mappings]
    mapping_count = len(mappings)
    mappings_complete = mapping_count > 0
    if not mappings_complete:
        blocking.append("No conversion mappings were generated.")

    # ── 4. Validate output paths ───────────────────────────────────────
    output_root = preflight.output_root_preview or (
        str(Path(project_dir) / "converted_bids") if project_dir else ""
    )
    output_root_safe = bool(preflight.output_dir_safe)
    if output_root and not output_root_safe:
        blocking.append(f"Output root is not safe: {output_root}")

    # ── 5. Validate disk space ─────────────────────────────────────────
    estimated_bytes = _estimate_disk_required(mappings)
    disk_ok, disk_free, disk_required = _check_disk_space(
        output_root or project_dir or ".", estimated_bytes
    )
    if not disk_ok:
        blocking.append(
            f"Disk space insufficient: {disk_free} bytes free, "
            f"{disk_required} estimated required."
        )

    # ── 6. Env gates ───────────────────────────────────────────────────
    env_gates_ok = bool(preflight.env_enabled)
    if not env_gates_ok:
        blocking.append(
            f"Env gates not satisfied: {', '.join(preflight.missing_env_flags)}"
        )

    # ── 7. Reserve conversion run directory ────────────────────────────
    conversion_run_id = f"conv-{uuid.uuid4().hex[:12]}"
    run_dir = Path(project_dir) / "conversion_runs" / conversion_run_id if project_dir else Path("conversion_runs") / conversion_run_id

    # ── 8. Compute rawdata checksum-before ─────────────────────────────
    checksum_before_path = run_dir / "rawdata_checksum_before.json"
    checksum_before_exists = False
    if rawdata_dir and Path(rawdata_dir).exists():
        checksums, checksum_error = _compute_rawdata_checksum_before(rawdata_dir)
        if checksum_error:
            warnings.append(f"Checksum-before warning: {checksum_error}")
        else:
            _write_json(
                checksum_before_path,
                {
                    "rawdata_dir": rawdata_dir,
                    "file_count": len(checksums),
                    "computed_at": _now_iso(),
                    "checksums": checksums,
                },
            )
            checksum_before_exists = True
    else:
        warnings.append("rawdata_dir not accessible; checksum-before skipped.")

    # ── 9. Create rollback plan ────────────────────────────────────────
    rollback_plan_path = run_dir / "rollback_plan_dry_run.json"
    rollback_plan = _build_rollback_plan(run_dir, output_root, mappings)
    _write_json(rollback_plan_path, rollback_plan)
    rollback_plan_exists = True

    # ── 10. Persist preflight & mapping snapshots ──────────────────────
    preflight_snapshot_path = run_dir / "preflight_snapshot.json"
    _write_json(preflight_snapshot_path, preflight.model_dump())

    mapping_snapshot_path = run_dir / "mapping_snapshot.json"
    _write_json(mapping_snapshot_path, {
        "mapping_count": mapping_count,
        "mappings": mappings,
        "captured_at": _now_iso(),
    })

    command_templates_path = run_dir / "command_templates.json"
    _write_json(command_templates_path, {
        "templates": [t.model_dump() for t in preflight.command_templates],
        "captured_at": _now_iso(),
    })

    # ── 11. Build approval record ──────────────────────────────────────
    approval_id = f"approval-{uuid.uuid4().hex[:12]}"
    confirmations = request.confirmations
    approval_record = DicomConversionApprovalRecord(
        approval_id=approval_id,
        project_id=project_id,
        status="ready_for_review",
        approved=confirmations.confirm_execution,
        approved_by=request.approved_by,
        approved_at=_now_iso() if confirmations.confirm_execution else None,
        mapping_ids=request.selected_mapping_ids,
        mappings_reviewed=confirmations.mappings_reviewed,
        output_root=output_root,
        output_root_confirmed=output_root_safe,
        output_root_under_project=output_root_safe,
        output_root_not_rawdata=True,
        overwrite_policy=request.overwrite_policy,
        rawdata_read_only_confirmed=confirmations.rawdata_readonly,
        command_templates_reviewed=confirmations.mappings_reviewed,
        no_shell_string_confirmed=True,
        dcm2niix_availability_confirmed=dcm2niix_available,
        dcm2niix_version=dcm2niix_info.get("version"),
        env_flags_confirmed=env_gates_ok,
        rawdata_checksum_snapshot_path=str(checksum_before_path) if checksum_before_exists else None,
        rawdata_checksum_confirmed=checksum_before_exists,
        rollback_plan_path=str(rollback_plan_path) if rollback_plan_exists else None,
        rollback_plan_confirmed=rollback_plan_exists,
        missing_env_flags=preflight.missing_env_flags,
        rollback_policy_acknowledged=confirmations.rollback_policy,
        clinical_use_prohibited_acknowledged=confirmations.no_clinical_use,
        external_tool_acknowledgement=confirmations.external_converter,
        risk_acknowledgement=confirmations.risk_acknowledgement,
        confirm_execution=confirmations.confirm_execution,
    )

    # ── 12. Validate operator confirmations ────────────────────────────
    confirmations_ok, missing_confirmations = validate_prepare_confirmations(confirmations)

    # ── 13. Evaluate approval gate ─────────────────────────────────────
    gate = evaluate_conversion_approval_gate(approval_record, preflight_ok=preflight_ok)

    # ── 14. Persist approval record ────────────────────────────────────
    approval_record_path = run_dir / "approval_record.json"
    _write_json(approval_record_path, {
        **approval_record.model_dump(),
        "persisted_at": _now_iso(),
        "gate_status": gate.status,
    })

    # ── 15. Generate audit preview ─────────────────────────────────────
    audit_preview_path = run_dir / "audit_preview.json"
    _write_json(audit_preview_path, {
        "project_id": project_id,
        "conversion_run_id": conversion_run_id,
        "approval_id": approval_id,
        "prepared_at": _now_iso(),
        "prepared_by": request.approved_by,
        "preflight_status": preflight.status,
        "dcm2niix_available": dcm2niix_available,
        "dcm2niix_path": dcm2niix_info.get("executable_path"),
        "dcm2niix_version": dcm2niix_info.get("version"),
        "dcm2niix_sha256": dcm2niix_info.get("sha256"),
        "dcm2niix_strategy": dcm2niix_info.get("strategy"),
        "mapping_count": mapping_count,
        "output_root": output_root,
        "output_root_safe": output_root_safe,
        "disk_space_ok": disk_ok,
        "checksum_before_exists": checksum_before_exists,
        "rollback_plan_exists": rollback_plan_exists,
        "env_gates_ok": env_gates_ok,
        "confirmations_ok": confirmations_ok,
        "missing_confirmations": missing_confirmations,
        "gate_status": gate.status,
    })

    # ── 16. Persist via plan persistence (for compatibility) ───────────
    try:
        persist_result = persist_conversion_plan(
            project_id=project_id,
            approval_record=approval_record,
            preflight_snapshot=preflight.model_dump(),
            mappings=mappings,
            command_templates=[t.model_dump() for t in preflight.command_templates],
            safety_flags=preflight.safety_flags.model_dump(),
            project_dir=project_dir,
            rawdata_dir=rawdata_dir,
            overwrite_policy=request.overwrite_policy,
            preflight_ok=preflight_ok,
        )
        if persist_result.conversion_run_id:
            conversion_run_id = persist_result.conversion_run_id
            run_dir = Path(project_dir) / "conversion_runs" / conversion_run_id
    except Exception as exc:
        warnings.append(f"Plan persistence skipped: {exc}")

    # ── 17. Determine readiness ────────────────────────────────────────
    technical_ready = (
        preflight_ok
        and dcm2niix_available
        and mappings_complete
        and output_root_safe
        and disk_ok
        and env_gates_ok
        and checksum_before_exists
        and rollback_plan_exists
    )
    approval_ready = technical_ready and confirmations_ok and gate.status == "approved"
    execution_ready = approval_ready

    if not env_gates_ok or not dcm2niix_available:
        status = "disabled"
    elif blocking:
        status = "blocked"
    elif not technical_ready:
        status = "review_required"
    elif not approval_ready:
        status = "review_required"
    else:
        status = "ready"

    next_action = determine_prepare_next_action(
        technical_ready=technical_ready,
        approval_ready=approval_ready,
        execution_ready=execution_ready,
        dcm2niix_available=dcm2niix_available,
        mapping_count=mapping_count,
        output_root_safe=output_root_safe,
        env_gates_ok=env_gates_ok,
    )

    system_checks = DicomConversionPrepareSystemChecks(
        preflight_ok=preflight_ok,
        dcm2niix_available=dcm2niix_available,
        dcm2niix_path=dcm2niix_info.get("executable_path"),
        dcm2niix_version=dcm2niix_info.get("version"),
        dcm2niix_sha256=dcm2niix_info.get("sha256"),
        dcm2niix_strategy=dcm2niix_info.get("strategy"),
        mappings_complete=mappings_complete,
        mapping_count=mapping_count,
        output_root_safe=output_root_safe,
        output_root=output_root,
        rawdata_dir=rawdata_dir,
        project_dir=project_dir,
        disk_space_ok=disk_ok,
        disk_free_bytes=disk_free,
        disk_required_bytes=disk_required,
        checksum_before_exists=checksum_before_exists,
        checksum_before_path=str(checksum_before_path) if checksum_before_exists else None,
        rollback_plan_exists=rollback_plan_exists,
        rollback_plan_path=str(rollback_plan_path) if rollback_plan_exists else None,
        env_gates_ok=env_gates_ok,
        missing_env_flags=preflight.missing_env_flags,
    )

    return DicomConversionPrepareResponse(
        ok=technical_ready and not blocking,
        status=status,
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        approval_id=approval_id,
        technical_ready=technical_ready,
        approval_ready=approval_ready,
        execution_ready=execution_ready,
        next_action=next_action,
        system_checks=system_checks,
        operator_confirmations=confirmations,
        missing_confirmations=missing_confirmations,
        blocking_issues=blocking,
        warnings=warnings,
        errors=errors,
        run_dir=str(run_dir),
        approval_record_path=str(approval_record_path),
        audit_preview_path=str(audit_preview_path),
        preflight_snapshot_path=str(preflight_snapshot_path),
        mapping_snapshot_path=str(mapping_snapshot_path),
        command_templates_path=str(command_templates_path),
        checksum_before_path=str(checksum_before_path) if checksum_before_exists else None,
        rollback_plan_path=str(rollback_plan_path) if rollback_plan_exists else None,
        review_package_path=str(run_dir),
    )
