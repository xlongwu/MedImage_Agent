"""DICOM Conversion Safety Schema — Phase 4H-1.

Defines rawdata checksum snapshot, comparison, rollback plan, and
rollback result models, plus pure helper functions for verifying
rawdata integrity before/after DICOM conversion.

Schema-only module.  No subprocess.  No file writes.  No dcm2niix.
No rawdata modification.  No SPM/DPABI/MATLAB.

Reference:
  docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md
  docs/DICOM_USER_DATA_CONVERSION_GO_NO_GO_REVIEW.md
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RawdataChecksumSnapshot(BaseModel):
    """A point-in-time snapshot of rawdata filesystem metadata."""

    ok: bool = True
    roots: list[str] = Field(default_factory=list)
    fingerprint: str | None = None
    file_count: int = 0
    total_size_bytes: int = 0
    newest_mtime: str | None = None
    relative_path_hash: str | None = None
    generated_at: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RawdataChecksumComparison(BaseModel):
    """Comparison of two rawdata checksum snapshots."""

    ok: bool = True
    unchanged: bool = True
    before_fingerprint: str | None = None
    after_fingerprint: str | None = None
    before_file_count: int = 0
    after_file_count: int = 0
    before_total_size_bytes: int = 0
    after_total_size_bytes: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionRollbackPlan(BaseModel):
    """A dry-run plan for rolling back conversion outputs."""

    conversion_run_id: str = ""
    output_root: str = ""
    removable_paths: list[str] = Field(default_factory=list)
    quarantine_paths: list[str] = Field(default_factory=list)
    protected_paths: list[str] = Field(default_factory=list)
    rawdata_roots: list[str] = Field(default_factory=list)
    rollback_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionRollbackResult(BaseModel):
    """Result of executing (or dry-running) a rollback plan."""

    ok: bool = True
    status: str = "dry_run"
    removed_paths: list[str] = Field(default_factory=list)
    quarantined_paths: list[str] = Field(default_factory=list)
    protected_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# Pure helpers
# ═══════════════════════════════════════════════════════════════════════


def build_rawdata_checksum_snapshot(
    rawdata_fingerprint: Any,
) -> RawdataChecksumSnapshot:
    """Build a checksum snapshot from a RawdataFingerprint result."""
    fp = getattr(rawdata_fingerprint, "fingerprint", None) or rawdata_fingerprint.get("fingerprint") if isinstance(rawdata_fingerprint, dict) else None
    fc = getattr(rawdata_fingerprint, "file_count", 0) or (rawdata_fingerprint.get("file_count", 0) if isinstance(rawdata_fingerprint, dict) else 0)
    ts = getattr(rawdata_fingerprint, "total_size_bytes", 0) or (rawdata_fingerprint.get("total_size_bytes", 0) if isinstance(rawdata_fingerprint, dict) else 0)
    mt = getattr(rawdata_fingerprint, "newest_mtime_iso", None) or (rawdata_fingerprint.get("newest_mtime_iso") if isinstance(rawdata_fingerprint, dict) else None)
    rh = getattr(rawdata_fingerprint, "relative_path_hash", None) or (rawdata_fingerprint.get("relative_path_hash") if isinstance(rawdata_fingerprint, dict) else None)
    roots = getattr(rawdata_fingerprint, "roots", []) or (rawdata_fingerprint.get("roots", []) if isinstance(rawdata_fingerprint, dict) else [])

    return RawdataChecksumSnapshot(
        ok=True,
        roots=list(roots),
        fingerprint=fp,
        file_count=fc,
        total_size_bytes=ts,
        newest_mtime=mt,
        relative_path_hash=rh,
    )


def compare_rawdata_checksum_snapshots(
    before: RawdataChecksumSnapshot,
    after: RawdataChecksumSnapshot,
) -> RawdataChecksumComparison:
    """Compare two rawdata checksum snapshots for equality."""
    warnings: list[str] = []
    errors: list[str] = []

    same_fp = before.fingerprint == after.fingerprint
    same_fc = before.file_count == after.file_count
    same_size = before.total_size_bytes == after.total_size_bytes

    unchanged = same_fp and same_fc and same_size

    if not same_fp:
        errors.append("Rawdata fingerprint changed — possible modification.")
    if not same_fc:
        errors.append(f"File count changed: {before.file_count} → {after.file_count}")
    if not same_size:
        errors.append(f"Total size changed: {before.total_size_bytes} → {after.total_size_bytes}")

    return RawdataChecksumComparison(
        ok=unchanged,
        unchanged=unchanged,
        before_fingerprint=before.fingerprint,
        after_fingerprint=after.fingerprint,
        before_file_count=before.file_count,
        after_file_count=after.file_count,
        before_total_size_bytes=before.total_size_bytes,
        after_total_size_bytes=after.total_size_bytes,
        warnings=warnings,
        errors=errors if not unchanged else [],
    )


def is_rawdata_unchanged(
    comparison: RawdataChecksumComparison,
) -> bool:
    """Return True if rawdata is unchanged according to the comparison."""
    return comparison.unchanged


def is_rollback_path_safe(
    path: str,
    project_dir: str = "",
    rawdata_roots: list[str] | None = None,
) -> bool:
    """Return True if *path* is safe to remove during rollback.

    Paths under rawdata_roots are never safe to remove.
    Paths outside project_dir are unsafe unless explicitly allowed.
    """
    if not path:
        return False
    for root in (rawdata_roots or []):
        if root and path.startswith(root):
            return False
    if project_dir and not path.startswith(project_dir):
        return False
    return True


def build_conversion_rollback_plan(
    output_root: str,
    conversion_run_id: str = "",
    project_dir: str = "",
    rawdata_roots: list[str] | None = None,
) -> DicomConversionRollbackPlan:
    """Build a dry-run rollback plan for conversion outputs."""
    from pathlib import Path

    removable: list[str] = []
    protected: list[str] = []
    warnings: list[str] = []

    root_path = Path(output_root)
    if not root_path.exists():
        return DicomConversionRollbackPlan(
            conversion_run_id=conversion_run_id,
            output_root=output_root,
            rawdata_roots=list(rawdata_roots or []),
            rollback_allowed=False,
            warnings=[f"Output root does not exist: {output_root}"],
        )

    for p in sorted(root_path.rglob("*")):
        if not p.is_file():
            continue
        sp = str(p)
        if is_rollback_path_safe(sp, project_dir, rawdata_roots):
            removable.append(sp)
        else:
            protected.append(sp)
            warnings.append(f"Protected path (unsafe to remove): {sp}")

    return DicomConversionRollbackPlan(
        conversion_run_id=conversion_run_id,
        output_root=output_root,
        removable_paths=removable,
        protected_paths=protected,
        rawdata_roots=list(rawdata_roots or []),
        rollback_allowed=len(removable) > 0 and len(protected) == 0,
        warnings=warnings,
    )


def run_conversion_rollback_dry_run(
    plan: DicomConversionRollbackPlan,
) -> DicomConversionRollbackResult:
    """Dry-run a rollback plan — NEVER deletes files.

    Returns which paths would be removed and which are protected.
    """
    return DicomConversionRollbackResult(
        ok=True,
        status="dry_run",
        removable_paths=list(plan.removable_paths),
        protected_paths=list(plan.protected_paths),
        safety_flags={
            "dry_run_only": True,
            "no_files_deleted": True,
            "no_rawdata_modified": True,
            "metadata_only": True,
        },
    )


def summarize_rollback_plan(
    plan: DicomConversionRollbackPlan,
) -> dict[str, Any]:
    """Summarize a rollback plan."""
    return {
        "conversion_run_id": plan.conversion_run_id,
        "output_root": plan.output_root,
        "removable_count": len(plan.removable_paths),
        "protected_count": len(plan.protected_paths),
        "rollback_allowed": plan.rollback_allowed,
    }
