"""DICOM conversion safety service — Phase 4H-1.

Builds pre/post rawdata checksum snapshots, compares them, and builds
dry-run rollback plans.  External tools are never called.  Rawdata is
never modified.  No files are deleted in dry-run mode.

Reference:
  docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md
  src/backend/app/schemas/dicom_conversion_safety.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.schemas.dicom_conversion_safety import (
    DicomConversionRollbackPlan,
    DicomConversionRollbackResult,
    RawdataChecksumComparison,
    RawdataChecksumSnapshot,
    build_conversion_rollback_plan,
    build_rawdata_checksum_snapshot,
    compare_rawdata_checksum_snapshots,
    run_conversion_rollback_dry_run,
    summarize_rollback_plan,
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
