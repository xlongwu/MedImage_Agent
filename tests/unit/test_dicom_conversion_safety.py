"""Tests for DICOM conversion safety schema and service — Phase 4H-1.

Tests rawdata checksum snapshot, comparison, rollback plan, rollback
dry-run, and safety invariants.  No dcm2niix.  No rawdata modification.
No file deletion.
"""

from __future__ import annotations

from src.backend.app.schemas.dicom_conversion_safety import (
    DicomConversionRollbackPlan,
    RawdataChecksumSnapshot,
    build_conversion_rollback_plan,
    build_rawdata_checksum_snapshot,
    compare_rawdata_checksum_snapshots,
    is_rawdata_unchanged,
    is_rollback_path_safe,
    run_conversion_rollback_dry_run,
    summarize_rollback_plan,
)


def _mock_fingerprint(fp="abc123", fc=10, ts=1000):
    """Mock a RawdataFingerprint-like dict."""
    return {
        "fingerprint": fp,
        "file_count": fc,
        "total_size_bytes": ts,
        "newest_mtime_iso": "2026-01-01T00:00:00Z",
        "relative_path_hash": "hash123",
        "roots": ["/data/rawdata"],
    }


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Checksum snapshot
# ═══════════════════════════════════════════════════════════════════════


def test_build_snapshot_from_fingerprint():
    fp = _mock_fingerprint()
    snap = build_rawdata_checksum_snapshot(fp)
    assert snap.ok is True
    assert snap.fingerprint == "abc123"
    assert snap.file_count == 10
    assert snap.total_size_bytes == 1000


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Checksum comparison
# ═══════════════════════════════════════════════════════════════════════


def test_identical_snapshots_unchanged():
    before = RawdataChecksumSnapshot(fingerprint="abc", file_count=5, total_size_bytes=100)
    after = RawdataChecksumSnapshot(fingerprint="abc", file_count=5, total_size_bytes=100)
    comp = compare_rawdata_checksum_snapshots(before, after)
    assert comp.unchanged is True
    assert is_rawdata_unchanged(comp) is True


def test_different_fingerprint_changed():
    before = RawdataChecksumSnapshot(fingerprint="abc", file_count=5)
    after = RawdataChecksumSnapshot(fingerprint="xyz", file_count=5)
    comp = compare_rawdata_checksum_snapshots(before, after)
    assert comp.unchanged is False


def test_different_file_count_changed():
    before = RawdataChecksumSnapshot(fingerprint="abc", file_count=5, total_size_bytes=100)
    after = RawdataChecksumSnapshot(fingerprint="abc", file_count=6, total_size_bytes=100)
    comp = compare_rawdata_checksum_snapshots(before, after)
    assert comp.unchanged is False


def test_different_total_size_changed():
    before = RawdataChecksumSnapshot(fingerprint="abc", file_count=5, total_size_bytes=100)
    after = RawdataChecksumSnapshot(fingerprint="abc", file_count=5, total_size_bytes=200)
    comp = compare_rawdata_checksum_snapshots(before, after)
    assert comp.unchanged is False


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Rollback path safety
# ═══════════════════════════════════════════════════════════════════════


def test_rollback_path_safe_under_project():
    assert is_rollback_path_safe("/project/output/file.nii", "/project") is True


def test_rollback_path_unsafe_under_rawdata():
    assert is_rollback_path_safe("/data/rawdata/file.nii", "/project", ["/data/rawdata"]) is False


def test_rollback_path_outside_project_unsafe():
    assert is_rollback_path_safe("/other/file.nii", "/project") is False


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Rollback plan (dry-run)
# ═══════════════════════════════════════════════════════════════════════


def test_rollback_plan_excludes_rawdata_paths(tmp_path):
    output_root = tmp_path / "output"
    output_root.mkdir()
    (output_root / "test.nii").write_text("fake")
    (output_root / "manifest.json").write_text("{}")

    rawdata_roots = [str(tmp_path / "rawdata")]
    plan = build_conversion_rollback_plan(
        str(output_root),
        project_dir=str(tmp_path),
        rawdata_roots=rawdata_roots,
    )
    assert len(plan.removable_paths) >= 1
    assert len(plan.protected_paths) == 0


def test_rollback_plan_blocks_rawdata_root(tmp_path):
    rawdata_dir = tmp_path / "rawdata"
    rawdata_dir.mkdir()
    (rawdata_dir / "test.dcm").write_text("fake")

    plan = build_conversion_rollback_plan(
        str(rawdata_dir),
        project_dir=str(tmp_path),
        rawdata_roots=[str(rawdata_dir)],
    )
    assert len(plan.removable_paths) == 0
    assert len(plan.protected_paths) >= 1


def test_rollback_dry_run_deletes_nothing(tmp_path):
    output_root = tmp_path / "output"
    output_root.mkdir()
    test_file = output_root / "test.json"
    test_file.write_text("data")

    plan = build_conversion_rollback_plan(str(output_root), project_dir=str(tmp_path))
    result = run_conversion_rollback_dry_run(plan)
    assert result.status == "dry_run"
    assert result.safety_flags["dry_run_only"] is True
    assert result.safety_flags["no_files_deleted"] is True
    # File must still exist after dry-run
    assert test_file.exists()


def test_rollback_summary():
    plan = DicomConversionRollbackPlan(
        conversion_run_id="test",
        output_root="/tmp/out",
        removable_paths=["/tmp/out/a.json", "/tmp/out/b.nii"],
        protected_paths=[],
        rollback_allowed=True,
    )
    summary = summarize_rollback_plan(plan)
    assert summary["removable_count"] == 2
    assert summary["rollback_allowed"] is True


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Service purity and safety
# ═══════════════════════════════════════════════════════════════════════


def test_schema_has_no_subprocess():
    import src.backend.app.schemas.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content


def test_service_has_no_subprocess():
    import src.backend.app.services.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content


def test_service_has_no_subprocess_import():
    import src.backend.app.services.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content
    assert "from subprocess" not in content


def test_no_spm_dpabi_matlab():
    import src.backend.app.schemas.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import spm" not in content.lower()
    assert "import matlab" not in content.lower()
    assert "import dpabi" not in content.lower()
