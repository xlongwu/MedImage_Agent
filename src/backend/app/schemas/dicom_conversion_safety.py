"""DICOM Conversion Safety Schema — Phase 4H-1.

Defines rawdata checksum snapshot, comparison, rollback plan, and
rollback result models, plus pure helper functions for verifying
rawdata integrity before/after DICOM conversion.

Schema-only module.  No subprocess.  No file writes.  No dcm2niix.
No rawdata modification.  No SPM/DPABI/MATLAB.

Reference:
  docs/预处理与科学计算/DICOM转换/DICOM到NIfTI执行包装契约.md
  docs/预处理与科学计算/DICOM转换/用户数据转换放行审查.md
"""

from __future__ import annotations

from typing import Any, Literal

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


# ═══════════════════════════════════════════════════════════════════════
# Phase 4J-0 — Real rollback execution
# ═══════════════════════════════════════════════════════════════════════

DicomConversionRollbackMode = Literal[
    "dry_run",
    "quarantine",
    "delete",
]


class DicomConversionRollbackRequest(BaseModel):
    """Request to execute a real rollback on conversion outputs."""

    project_id: str = ""
    conversion_run_id: str = ""
    rollback_mode: DicomConversionRollbackMode = "dry_run"
    confirm_rollback: bool = False
    reason: str = ""
    requested_by: str = ""
    expected_output_root: str | None = None
    expected_manifest_path: str | None = None


class DicomConversionRollbackExecResult(BaseModel):
    """Result of executing a real rollback."""

    ok: bool = True
    status: str = "dry_run"
    mode: DicomConversionRollbackMode = "dry_run"
    conversion_run_id: str = ""
    output_root: str = ""
    removed_paths: list[str] = Field(default_factory=list)
    quarantined_paths: list[str] = Field(default_factory=list)
    protected_paths: list[str] = Field(default_factory=list)
    skipped_paths: list[str] = Field(default_factory=list)
    rollback_manifest_path: str | None = None
    rollback_provenance_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


def _rollback_safety_flags() -> dict[str, bool]:
    return {
        "rawdata_protected": True,
        "output_under_project": True,
        "no_path_traversal": True,
        "manifest_bound": True,
        "dry_run_default": True,
        "confirmed": False,
        "no_external_tools": True,
        "clinical_use_prohibited": True,
    }


def validate_rollback_request(
    request: DicomConversionRollbackRequest,
) -> tuple[bool, list[str]]:
    """Validate a rollback request. Returns (ok, issues)."""
    issues: list[str] = []
    if not request.conversion_run_id:
        issues.append("conversion_run_id is required")
    if request.rollback_mode not in {"dry_run", "quarantine", "delete"}:
        issues.append(f"Invalid rollback_mode: {request.rollback_mode}")
    if request.rollback_mode == "delete" and not request.confirm_rollback:
        issues.append("Delete mode requires confirm_rollback=True")
    return len(issues) == 0, issues


def is_rollback_confirmed(
    request: DicomConversionRollbackRequest,
) -> bool:
    """Return True if the rollback is explicitly confirmed."""
    return request.confirm_rollback


_PROTECTED_ROLLBACK_NAMES: frozenset[str] = frozenset({
    "approval_record.json",
    "audit_preview.json",
    "preflight_snapshot.json",
    "mapping_snapshot.json",
    "command_templates.json",
    "rawdata_checksum_before.json",
    "rawdata_checksum_after.json",
    "rawdata_checksum_comparison.json",
    "rollback_plan_dry_run.json",
    "planned_output_manifest.json",
    "planned_execution_provenance.json",
    "output_manifest.json",
    "execution_provenance.json",
    "README.md",
})


def classify_rollback_candidate(
    path: str,
    project_dir: str = "",
    output_root: str = "",
    rawdata_roots: list[str] | None = None,
) -> str:
    """Classify a path for rollback: removable, protected, or skipped."""
    if not path or not output_root:
        return "protected"
    # Resolve the path
    from pathlib import Path as _Path
    rp = _Path(path).resolve()
    rr = _Path(output_root).resolve()

    # Check if under output_root
    try:
        rp.relative_to(rr)
    except ValueError:
        return "protected"  # Outside output_root

    # Check rawdata
    for root in (rawdata_roots or []):
        try:
            rp.relative_to(_Path(root).resolve())
            return "protected"  # Under rawdata
        except ValueError:
            pass

    # Check protected file names
    if rp.name in _PROTECTED_ROLLBACK_NAMES:
        return "protected"

    # Check for path traversal
    if ".." in path or ".." in str(rp):
        return "protected"

    return "removable"


def build_rollback_result_summary(
    result: "DicomConversionRollbackExecResult",
) -> dict[str, Any]:
    """Summarize a rollback execution result."""
    return {
        "status": result.status,
        "mode": result.mode,
        "removed_count": len(result.removed_paths),
        "quarantined_count": len(result.quarantined_paths),
        "protected_count": len(result.protected_paths),
        "rollback_manifest_path": result.rollback_manifest_path,
    }
