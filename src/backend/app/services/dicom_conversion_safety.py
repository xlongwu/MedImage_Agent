"""DICOM conversion safety service — Phase 4H-1.

Builds pre/post rawdata checksum snapshots, compares them, and builds
dry-run rollback plans.  External tools are never called.  Rawdata is
never modified.  No files are deleted in dry-run mode.

Reference:
  docs/预处理与科学计算/DICOM转换/DICOM到NIfTI执行包装契约.md
  src/backend/app/schemas/dicom_conversion_safety.py
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.dicom_conversion_safety import (
    DicomConversionRollbackExecResult,
    DicomConversionRollbackPlan,
    DicomConversionRollbackRequest,
    DicomConversionRollbackResult,
    RawdataChecksumComparison,
    RawdataChecksumSnapshot,
    build_conversion_rollback_plan,
    build_rawdata_checksum_snapshot,
    compare_rawdata_checksum_snapshots,
    run_conversion_rollback_dry_run,
)
from src.backend.app.services.rawdata_fingerprint import (
    build_rawdata_fingerprint,
)


def build_pre_conversion_rawdata_snapshot(
    rawdata_roots: list[str],
) -> RawdataChecksumSnapshot:
    """Build a pre-conversion rawdata checksum snapshot.

    Uses the existing ``build_rawdata_fingerprint()`` service.
    Does NOT modify rawdata.  Does NOT call dcm2niix.
    """
    if not rawdata_roots:
        return RawdataChecksumSnapshot(
            ok=False,
            errors=["No rawdata roots provided."],
        )
    fp = build_rawdata_fingerprint(rawdata_roots)
    return build_rawdata_checksum_snapshot(fp)


def build_post_conversion_rawdata_snapshot(
    rawdata_roots: list[str],
) -> RawdataChecksumSnapshot:
    """Build a post-conversion rawdata checksum snapshot.

    Identical to pre-conversion — re-runs the fingerprint.
    Does NOT modify rawdata.  Does NOT call dcm2niix.
    """
    return build_pre_conversion_rawdata_snapshot(rawdata_roots)


def compare_conversion_rawdata_snapshots(
    before: RawdataChecksumSnapshot,
    after: RawdataChecksumSnapshot,
) -> RawdataChecksumComparison:
    """Compare pre and post conversion rawdata snapshots."""
    return compare_rawdata_checksum_snapshots(before, after)


def build_conversion_output_rollback_plan(
    project_dir: str,
    output_root: str,
    conversion_run_id: str = "",
    rawdata_roots: list[str] | None = None,
) -> DicomConversionRollbackPlan:
    """Build a dry-run rollback plan for conversion outputs.

    Scans *output_root* for files that can be safely removed.
    Never includes rawdata paths.  Never deletes files.
    """
    return build_conversion_rollback_plan(
        output_root=output_root,
        conversion_run_id=conversion_run_id,
        project_dir=project_dir,
        rawdata_roots=rawdata_roots,
    )


def run_conversion_output_rollback_dry_run(
    plan: DicomConversionRollbackPlan,
) -> DicomConversionRollbackResult:
    """Dry-run a rollback plan — NEVER deletes files."""
    return run_conversion_rollback_dry_run(plan)


# ═══════════════════════════════════════════════════════════════════════
# Phase 4J-0 — Real rollback execution
# ═══════════════════════════════════════════════════════════════════════


def run_conversion_rollback(
    request: DicomConversionRollbackRequest,
    *,
    project_dir: str = "",
    rawdata_roots: list[str] | None = None,
) -> DicomConversionRollbackExecResult:
    """Execute a real rollback on conversion outputs.

    - ``dry_run``: report what would happen, delete nothing.
    - ``quarantine``: move generable outputs to a quarantine dir.
    - ``delete``: delete generable outputs (requires confirm_rollback=True).

    Always protects: rawdata, approval/audit/checksum/provenance files,
    paths outside output_root, path traversal, symlink escapes.
    """
    import shutil
    from datetime import datetime

    from src.backend.app.schemas.dicom_conversion_safety import (
        _rollback_safety_flags,
        classify_rollback_candidate,
        validate_rollback_request,
    )

    warnings: list[str] = []
    errors: list[str] = []

    mode = request.rollback_mode
    ok_req, req_issues = validate_rollback_request(request)
    if not ok_req:
        return DicomConversionRollbackExecResult(
            ok=False,
            status="blocked",
            mode=mode,
            conversion_run_id=request.conversion_run_id,
            errors=req_issues,
            safety_flags=_rollback_safety_flags(),
        )

    if mode == "delete" and not request.confirm_rollback:
        return DicomConversionRollbackExecResult(
            ok=False,
            status="blocked",
            mode=mode,
            conversion_run_id=request.conversion_run_id,
            errors=["Delete mode requires confirm_rollback=True."],
            safety_flags=_rollback_safety_flags(),
        )

    output_root = request.expected_output_root or ""
    if not output_root:
        return DicomConversionRollbackExecResult(
            ok=False,
            status="blocked",
            mode=mode,
            conversion_run_id=request.conversion_run_id,
            errors=["expected_output_root is required for rollback."],
            safety_flags=_rollback_safety_flags(),
        )

    output_path = Path(output_root).resolve()
    if not output_path.exists():
        return DicomConversionRollbackExecResult(
            ok=False,
            status="blocked",
            mode=mode,
            conversion_run_id=request.conversion_run_id,
            errors=[f"Output root does not exist: {output_root}"],
            safety_flags=_rollback_safety_flags(),
        )

    # Classify all files under output_root
    removed: list[str] = []
    quarantined: list[str] = []
    protected: list[str] = []
    skipped: list[str] = []

    for p in sorted(output_path.rglob("*")):
        if not p.is_file():
            continue
        sp = str(p)
        classification = classify_rollback_candidate(
            sp,
            project_dir=project_dir,
            output_root=output_root,
            rawdata_roots=list(rawdata_roots or []),
        )

        if classification == "protected":
            protected.append(sp)
        elif classification == "removable":
            if mode == "dry_run":
                removed.append(sp)  # Report only
            elif mode == "quarantine":
                ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
                quarantine_dir = output_path / "rollback_quarantine" / ts
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                dest = quarantine_dir / p.relative_to(output_path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(sp, str(dest))
                quarantined.append(sp)
            elif mode == "delete":
                p.unlink()
                removed.append(sp)
        else:
            skipped.append(sp)

    # Write rollback manifest and provenance
    manifest_path = output_path / "rollback_manifest.json"
    provenance_path = output_path / "rollback_provenance.json"

    import json as _json

    manifest_path.write_text(
        _json.dumps(
            {
                "conversion_run_id": request.conversion_run_id,
                "mode": mode,
                "removed_count": len(removed),
                "quarantined_count": len(quarantined),
                "protected_count": len(protected),
                "removed": removed,
                "quarantined": quarantined,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    provenance_path.write_text(
        _json.dumps(
            {
                "mode": mode,
                "confirm_rollback": request.confirm_rollback,
                "requested_by": request.requested_by,
                "reason": request.reason,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    status = "completed" if not errors else "partial"

    return DicomConversionRollbackExecResult(
        ok=len(errors) == 0,
        status=status,
        mode=mode,
        conversion_run_id=request.conversion_run_id,
        output_root=output_root,
        removed_paths=removed,
        quarantined_paths=quarantined,
        protected_paths=protected,
        skipped_paths=skipped,
        rollback_manifest_path=str(manifest_path),
        rollback_provenance_path=str(provenance_path),
        warnings=warnings,
        errors=errors,
        safety_flags=_rollback_safety_flags(),
    )
