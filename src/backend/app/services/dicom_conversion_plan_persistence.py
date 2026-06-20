"""DICOM conversion plan persistence — Phase 4E-0.

Persists approval records, preflight snapshots, mappings, command templates,
and reserves a safe project-scoped conversion run directory.  No dcm2niix
is called.  No NIfTI files are created.  No rawdata is modified.

Reference:
  docs/DICOM_CONVERSION_APPROVAL_GATE_DESIGN.md  (Section 21)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.schemas.dicom_conversion_approval import (
    DicomConversionApprovalRecord,
    DicomConversionGateDecision,
    DicomConversionOverwritePolicy,
    DicomConversionPersistedPlan,
    DicomConversionPlanPersistenceResponse,
    DicomConversionPersistenceStatus,
    DicomConversionRunReservation,
    build_conversion_run_id,
    build_conversion_run_paths,
    evaluate_conversion_approval_gate,
    is_reserved_run_directory_safe,
    summarize_persisted_conversion_plan,
    validate_conversion_run_paths,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: str, data: dict[str, Any]) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def persist_conversion_plan(
    project_id: str,
    approval_record: DicomConversionApprovalRecord,
    *,
    preflight_snapshot: dict[str, Any] | None = None,
    mappings: list[dict[str, Any]] | None = None,
    command_templates: list[dict[str, Any]] | None = None,
    safety_flags: dict[str, bool] | None = None,
    project_dir: str = "",
    rawdata_dir: str = "",
    overwrite_policy: DicomConversionOverwritePolicy = "fail_if_exists",
    preflight_ok: bool = True,
) -> DicomConversionPlanPersistenceResponse:
    """Persist a DICOM conversion approval plan and reserve a run directory.

    Evaluates the approval gate FIRST.  If blocked or incomplete, returns
    a blocked response without writing any files or reserving any directory.

    If approved, writes metadata snapshots into a reserved run directory
    under ``<project_dir>/conversion_runs/<conversion_run_id>/``.

    Does NOT call dcm2niix.  Does NOT create NIfTI files.  Does NOT
    modify rawdata.  Subprocess execution is never used.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── 1. Gate evaluation ──
    gate = evaluate_conversion_approval_gate(approval_record, preflight_ok=preflight_ok)
    if gate.status != "approved":
        return DicomConversionPlanPersistenceResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            gate_decision=gate,
            errors=[f"Approval gate blocked: {gate.status}"],
            safety_flags=safety_flags or {},
        )

    if not project_dir:
        return DicomConversionPlanPersistenceResponse(
            ok=False,
            status="invalid",
            project_id=project_id,
            gate_decision=gate,
            errors=["project_dir is required for persistence."],
            safety_flags=safety_flags or {},
        )

    # ── 2. Build run ID and paths ──
    mapping_hash = str(hash(tuple(sorted(m.get("subject_id", "") for m in (mappings or [])))))

    # Check for existing run directory
    conversion_run_id = build_conversion_run_id(project_id, mapping_hash)
    paths = build_conversion_run_paths(project_dir, conversion_run_id)
    run_dir = Path(paths["run_dir"])

    if run_dir.exists():
        if overwrite_policy == "fail_if_exists":
            return DicomConversionPlanPersistenceResponse(
                ok=False,
                status="already_exists",
                project_id=project_id,
                conversion_run_id=conversion_run_id,
                gate_decision=gate,
                errors=[f"Run directory already exists: {run_dir}"],
                safety_flags=safety_flags or {},
            )
        elif overwrite_policy == "write_new_run_directory":
            # Generate a new unique run ID
            import uuid
            conversion_run_id = f"conv-{uuid.uuid4().hex[:12]}"
            paths = build_conversion_run_paths(project_dir, conversion_run_id)
            run_dir = Path(paths["run_dir"])

    # ── 3. Path safety validation ──
    all_paths = {k: v for k, v in paths.items() if v}
    safe, path_issues = validate_conversion_run_paths(all_paths, project_dir, rawdata_dir)
    if not safe:
        return DicomConversionPlanPersistenceResponse(
            ok=False,
            status="invalid",
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            gate_decision=gate,
            errors=path_issues,
            safety_flags=safety_flags or {},
        )

    # ── 4. Write metadata snapshots ──
    written: list[str] = []
    try:
        written.append(_write_json(paths["approval_record_path"], approval_record.model_dump()))
        written.append(_write_json(paths["audit_preview_path"], {
            "audit_id": f"audit-{conversion_run_id}",
            "approval_id": approval_record.approval_id,
            "project_id": project_id,
            "reviewed_plan_id": approval_record.reviewed_plan_id,
            "output_root": paths["output_root"],
            "dcm2niix_version": approval_record.dcm2niix_version,
            "persisted_at": _now_iso(),
            "note": "Audit record placeholder — no conversion executed.",
        }))
        written.append(_write_json(paths["preflight_snapshot_path"], preflight_snapshot or {}))
        written.append(_write_json(paths["mapping_snapshot_path"], {"mappings": mappings or []}))
        written.append(_write_json(paths["command_templates_path"], {"templates": command_templates or []}))
        written.append(_write_json(paths["planned_manifest_path"], {
            "project_id": project_id,
            "run_id": conversion_run_id,
            "node_id": "dicom_to_nifti",
            "note": "Planned output manifest — no conversion executed.",
        }))
        written.append(_write_json(paths["planned_provenance_path"], {
            "project_id": project_id,
            "run_id": conversion_run_id,
            "backend": "external",
            "note": "Planned provenance — no conversion executed.",
        }))

        # ── Phase 4H-2: Rawdata checksum snapshot ──
        rawdata_checksum_path = str(run_dir / "rawdata_checksum_before.json")
        from src.backend.app.services.rawdata_fingerprint import build_rawdata_fingerprint
        from src.backend.app.schemas.dicom_conversion_safety import build_rawdata_checksum_snapshot
        try:
            if rawdata_dir:
                fp = build_rawdata_fingerprint([rawdata_dir])
                checksum = build_rawdata_checksum_snapshot(fp)
                checksum.generated_at = _now_iso()
                _write_json(rawdata_checksum_path, checksum.model_dump())
                written.append(rawdata_checksum_path)
            else:
                _write_json(rawdata_checksum_path, {
                    "note": "No rawdata_dir configured — checksum snapshot not generated.",
                })
                written.append(rawdata_checksum_path)
        except Exception as exc:
            warnings.append(f"Rawdata checksum snapshot failed: {exc}")

        # ── Phase 4H-2: Rollback dry-run plan ──
        rollback_plan_path = str(run_dir / "rollback_plan_dry_run.json")
        from src.backend.app.schemas.dicom_conversion_safety import (
            build_conversion_rollback_plan,
            run_conversion_rollback_dry_run,
        )
        try:
            rawdata_roots = [rawdata_dir] if rawdata_dir else []
            plan = build_conversion_rollback_plan(
                output_root=str(run_dir),
                conversion_run_id=conversion_run_id,
                project_dir=project_dir,
                rawdata_roots=rawdata_roots,
            )
            dry_run = run_conversion_rollback_dry_run(plan)
            _write_json(rollback_plan_path, dry_run.model_dump())
            written.append(rollback_plan_path)
        except Exception as exc:
            warnings.append(f"Rollback plan generation failed: {exc}")

        # Logs dir
        Path(paths["stdout_log_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(paths["stdout_log_path"]).write_text(
            f"# Conversion run {conversion_run_id} — stdout log placeholder\n"
            f"# No conversion has been executed.\n"
            f"# Reserved at: {_now_iso()}\n"
        )
        written.append(paths["stdout_log_path"])
        Path(paths["stderr_log_path"]).write_text(
            f"# Conversion run {conversion_run_id} — stderr log placeholder\n"
        )
        written.append(paths["stderr_log_path"])

        # README
        Path(paths["readme_path"]).write_text(
            f"# DICOM Conversion Run: {conversion_run_id}\n\n"
            f"- Project: {project_id}\n"
            f"- Reserved at: {_now_iso()}\n"
            f"- Status: NO CONVERSION EXECUTED\n\n"
            f"This directory contains metadata snapshots for a planned DICOM-to-NIfTI conversion.\n"
            f"No dcm2niix has been called. No NIfTI files have been created.\n"
            f"Real user-data conversion remains disabled in this release.\n"
        )
        written.append(paths["readme_path"])

    except Exception as exc:
        return DicomConversionPlanPersistenceResponse(
            ok=False,
            status="failed",
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            gate_decision=gate,
            written_files=written,
            errors=[f"Persistence write failed: {exc}"],
            safety_flags=safety_flags or {},
        )

    # ── 5. Build reservation ──
    reservation = DicomConversionRunReservation(
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        run_dir=paths["run_dir"],
        output_root=paths["output_root"],
        approval_record_path=paths["approval_record_path"],
        audit_preview_path=paths["audit_preview_path"],
        preflight_snapshot_path=paths["preflight_snapshot_path"],
        mapping_snapshot_path=paths["mapping_snapshot_path"],
        command_templates_path=paths["command_templates_path"],
        planned_manifest_path=paths["planned_manifest_path"],
        planned_provenance_path=paths["planned_provenance_path"],
        stdout_log_path=paths["stdout_log_path"],
        stderr_log_path=paths["stderr_log_path"],
        created_at=_now_iso(),
        overwrite_policy=overwrite_policy,
    )

    return DicomConversionPlanPersistenceResponse(
        ok=True,
        status="reserved",
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        reservation=reservation,
        gate_decision=gate,
        written_files=written,
        safety_flags=safety_flags or {},
    )
