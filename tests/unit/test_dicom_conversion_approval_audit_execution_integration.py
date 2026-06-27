"""Tests for DICOM conversion approval/audit execution integration — Phase 4J-1.

Tests that the internal conversion execution path:
- Loads and validates approval records before execution
- Loads and validates audit previews before execution
- Blocks on incomplete approval/audit evidence
- Writes audit execution start before dcm2niix
- Writes audit execution final after dcm2niix
- References approval/audit/checksum/rollback in provenance
- Maintains all safety boundaries

Uses monkeypatched runner/fake dcm2niix in tmp_path.
No real dcm2niix is called.  No rawdata is modified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

_ALL_FLAGS: dict[str, str] = {
    "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
    "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE": "1",
    "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE": "1",
    "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION": "1",
    "MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE": "1",
    "MEDIMAGE_ALLOW_INTERNAL_USER_DICOM_CONVERSION_PROTOTYPE": "1",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
}


def _make_approved_approval_record() -> dict:
    return {
        "approval_id": "approval-test-001",
        "project_id": "test-project",
        "approved": True,
        "approved_by": "tester",
        "mappings_reviewed": True,
        "output_root_confirmed": True,
        "output_root_under_project": True,
        "output_root_not_rawdata": True,
        "rawdata_read_only_confirmed": True,
        "command_templates_reviewed": True,
        "no_shell_string_confirmed": True,
        "dcm2niix_availability_confirmed": True,
        "env_flags_confirmed": True,
        "overwrite_policy": "fail_if_exists",
        "rollback_policy_acknowledged": True,
        "clinical_use_prohibited_acknowledged": True,
        "external_tool_acknowledgement": True,
        "risk_acknowledgement": True,
        "confirm_execution": True,
    }


def _make_audit_preview(output_root: str = "/tmp/test-output") -> dict:
    return {
        "audit_id": "audit-test-001",
        "approval_id": "approval-test-001",
        "project_id": "test-project",
        "reviewed_plan_id": "rp-test",
        "preflight_hash": "abc123",
        "input_dicom_checksum": "def456",
        "output_root": output_root,
        "persisted_at": "2026-01-01T00:00:00Z",
    }


def _make_command_templates(
    count: int = 1,
    *,
    input_dir: str = "/tmp/test-input",
    output_dir: str = "/tmp/test-output/sub-001",
) -> dict:
    return {
        "templates": [
            {
                "executable": "dcm2niix",
                "input_dir": input_dir,
                "output_dir": output_dir,
                "filename_pattern": "sub-001_task-rest_bold",
                "compress": "y",
                "bids_sidecar": True,
                "create_bids": True,
            }
        ] * count,
    }


def _make_mapping_snapshot(count: int = 1) -> dict:
    return {
        "mappings": [
            {
                "source_path": "/tmp/test-input",
                "subject_id": "sub-001",
                "modality": "func",
                "suffix": "bold",
                "suggested_relative_path": "sub-001/func/sub-001_task-rest_bold.nii.gz",
            }
        ] * count,
    }


def _make_checksum_snapshot() -> dict:
    return {
        "ok": True,
        "roots": ["/tmp/test-rawdata"],
        "fingerprint": "sha256:abc123",
        "file_count": 100,
        "total_size_bytes": 5000000,
    }


def _make_rollback_plan() -> dict:
    return {
        "conversion_run_id": "conv-test",
        "output_root": "/tmp/test-output",
        "removable_paths": [],
        "protected_paths": [],
        "rollback_allowed": True,
    }


def _setup_complete_review_package(project_dir: Path, conversion_run_id: str) -> Path:
    """Create a fully populated review package with all required files."""
    run_dir = project_dir / "conversion_runs" / conversion_run_id
    run_dir.mkdir(parents=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True)
    input_dir = project_dir / "test-input" / "sub-001"
    input_dir.mkdir(parents=True)
    output_dir = project_dir / "converted_bids" / "sub-001" / "func"

    (run_dir / "approval_record.json").write_text(
        json.dumps(_make_approved_approval_record())
    )
    (run_dir / "audit_preview.json").write_text(
        json.dumps(_make_audit_preview(str(project_dir / "converted_bids")))
    )
    (run_dir / "preflight_snapshot.json").write_text(
        json.dumps({"status": "ready", "ok": True})
    )
    (run_dir / "mapping_snapshot.json").write_text(
        json.dumps(_make_mapping_snapshot(1))
    )
    (run_dir / "command_templates.json").write_text(
        json.dumps(
            _make_command_templates(
                1,
                input_dir=str(input_dir),
                output_dir=str(output_dir),
            )
        )
    )
    (run_dir / "rawdata_checksum_before.json").write_text(
        json.dumps(_make_checksum_snapshot())
    )
    (run_dir / "rollback_plan_dry_run.json").write_text(
        json.dumps(_make_rollback_plan())
    )
    (run_dir / "planned_output_manifest.json").write_text('{"items": []}')
    (run_dir / "planned_execution_provenance.json").write_text('{}')
    (logs_dir / "stdout.log").write_text("")
    (logs_dir / "stderr.log").write_text("")
    (run_dir / "README.md").write_text("# test")
    return run_dir


def _fake_successful_runner(argv):
    """Fake dcm2niix runner that always succeeds."""
    if "-o" in argv and "-f" in argv:
        output_dir = Path(argv[argv.index("-o") + 1])
        filename = argv[argv.index("-f") + 1]
        compress = argv[argv.index("-z") + 1] if "-z" in argv else "y"
        suffix = ".nii" if str(compress).lower() in {"n", "3"} else ".nii.gz"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{filename}{suffix}").write_bytes(b"FAKE_NIFTI")
    return type("R", (), {
        "returncode": 0,
        "stdout": "dcm2niix v1.0 — OK",
        "stderr": "",
    })()


def _fake_failing_runner(argv):
    """Fake dcm2niix runner that always fails."""
    return type("R", (), {
        "returncode": 1,
        "stdout": "",
        "stderr": "Conversion failed",
    })()


def _monkeypatch_dcm2niix_available(monkeypatch, tmp_path):
    """Make dcm2niix appear available for happy-path tests.

    Patches shutil.which to return a fake path.  Individual tests should
    use _patch_subprocess_with(monkeypatch, runner) for the conversion runner.
    """
    import shutil
    fake_exe = tmp_path / "dcm2niix.exe"
    fake_exe.write_text("fake")
    monkeypatch.setattr(shutil, "which", lambda x, path=None: str(fake_exe) if x == "dcm2niix" else None)


def _version_result():
    return type("R", (), {
        "returncode": 0,
        "stdout": "Chris Rorden's dcm2niix version v1.0.20260416",
        "stderr": "",
    })()


def _patch_subprocess_with(monkeypatch, runner):
    """Patch subprocess.run to use *runner* for conversion, but still handle --version."""
    import subprocess as sp
    def _smart_run(argv, **kwargs):
        if "--version" in argv:
            return _version_result()
        return runner(argv)
    monkeypatch.setattr(sp, "run", _smart_run)


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Precondition: Missing approval record blocks execution
# ═══════════════════════════════════════════════════════════════════════


def test_missing_approval_record_blocks_execution(tmp_path, monkeypatch):
    """Gate 1: Execution must be blocked if approval_record.json is missing."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    run_dir = _setup_complete_review_package(project_dir, "conv-test")
    (run_dir / "approval_record.json").unlink()

    import subprocess as sp
    called = []
    def track(*args, **kwargs):
        called.append(args)
        return _fake_successful_runner(args[0])

    monkeypatch.setattr(sp, "run", track)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "blocked", f"Expected blocked, got {result.status}"
    assert len(called) == 0, "Subprocess must not be called"


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Precondition: Missing audit preview blocks execution
# ═══════════════════════════════════════════════════════════════════════


def test_missing_audit_preview_blocks_execution(tmp_path, monkeypatch):
    """Gate 2: Execution must be blocked if audit_preview.json is missing."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    run_dir = _setup_complete_review_package(project_dir, "conv-test")
    (run_dir / "audit_preview.json").unlink()

    import subprocess as sp
    called = []
    monkeypatch.setattr(sp, "run", lambda *a, **kw: called.append(a) or _fake_successful_runner(a[0]))
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "blocked", f"Expected blocked, got {result.status}"
    assert len(called) == 0


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Precondition: Incomplete approval gate blocks execution
# ═══════════════════════════════════════════════════════════════════════


def test_incomplete_approval_gate_blocks_execution(tmp_path, monkeypatch):
    """Gate 3: Incomplete approval gate blocks execution."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    run_dir = _setup_complete_review_package(project_dir, "conv-test")
    # Write an approval record with approved=False
    bad_approval = _make_approved_approval_record()
    bad_approval["approved"] = False
    (run_dir / "approval_record.json").write_text(json.dumps(bad_approval))

    import subprocess as sp
    called = []
    monkeypatch.setattr(sp, "run", lambda *a, **kw: called.append(a) or _fake_successful_runner(a[0]))
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "blocked", f"Expected blocked, got {result.status}"
    assert len(called) == 0


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Precondition: Missing checksum snapshot blocks execution
# ═══════════════════════════════════════════════════════════════════════


def test_missing_checksum_snapshot_blocks_execution(tmp_path, monkeypatch):
    """Gate 4: Missing checksum snapshot blocks execution."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    run_dir = _setup_complete_review_package(project_dir, "conv-test")
    (run_dir / "rawdata_checksum_before.json").unlink()

    import subprocess as sp
    called = []
    monkeypatch.setattr(sp, "run", lambda *a, **kw: called.append(a) or _fake_successful_runner(a[0]))
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "blocked", f"Expected blocked, got {result.status}"
    assert len(called) == 0


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Precondition: Missing rollback plan blocks execution
# ═══════════════════════════════════════════════════════════════════════


def test_missing_rollback_plan_blocks_execution(tmp_path, monkeypatch):
    """Gate 5: Missing rollback plan blocks execution."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    run_dir = _setup_complete_review_package(project_dir, "conv-test")
    (run_dir / "rollback_plan_dry_run.json").unlink()

    import subprocess as sp
    called = []
    monkeypatch.setattr(sp, "run", lambda *a, **kw: called.append(a) or _fake_successful_runner(a[0]))
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "blocked", f"Expected blocked, got {result.status}"
    assert len(called) == 0


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Audit start file written before runner invocation
# ═══════════════════════════════════════════════════════════════════════


def test_audit_start_file_written_before_runner(tmp_path, monkeypatch):
    """Gate 6: audit_execution_start.json must be written before subprocess."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    audit_start_seen = []

    def track_and_run(argv):
        # Check that audit start file exists at subprocess call time
        run_dir = project_dir / "conversion_runs" / "conv-test"
        audit_start_path = run_dir / "audit_execution_start.json"
        audit_start_seen.append(audit_start_path.exists())
        return _fake_successful_runner(argv)

    _patch_subprocess_with(monkeypatch, track_and_run)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "succeeded", f"Expected succeeded, got {result.status}"
    assert len(audit_start_seen) > 0, "Subprocess must have been called"
    assert all(audit_start_seen), "Audit start file must exist before each subprocess call"

    # Verify the audit start file content
    audit_start_path = project_dir / "conversion_runs" / "conv-test" / "audit_execution_start.json"
    assert audit_start_path.exists(), "audit_execution_start.json must exist after execution"
    data = json.loads(audit_start_path.read_text())
    assert data["audit_state"] == "execution_started"
    assert data["started_at"] is not None


# ═══════════════════════════════════════════════════════════════════════
# Group 7 — Audit final file written on success
# ═══════════════════════════════════════════════════════════════════════


def test_audit_final_file_written_on_success(tmp_path, monkeypatch):
    """Gate 7: audit_execution_final.json written with succeeded state."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_successful_runner)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "succeeded"

    audit_final_path = project_dir / "conversion_runs" / "conv-test" / "audit_execution_final.json"
    assert audit_final_path.exists(), "audit_execution_final.json must exist"
    data = json.loads(audit_final_path.read_text())
    assert data["audit_state"] == "execution_succeeded"
    assert data["finished_at"] is not None
    assert data["return_code"] == 0
    assert data["output_manifest_path"] is not None
    assert data["execution_provenance_path"] is not None


# ═══════════════════════════════════════════════════════════════════════
# Group 8 — Audit final file written on failure
# ═══════════════════════════════════════════════════════════════════════


def test_audit_final_file_written_on_failure(tmp_path, monkeypatch):
    """Gate 8: audit_execution_final.json written with failed state on failure."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_failing_runner)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    # Status is "warning" because dcm2niix failure with no checksum change
    assert result.status in ("warning", "failed")

    audit_final_path = project_dir / "conversion_runs" / "conv-test" / "audit_execution_final.json"
    assert audit_final_path.exists(), "audit_execution_final.json must exist even on failure"
    data = json.loads(audit_final_path.read_text())
    assert data["audit_state"] == "execution_failed"
    assert data["return_code"] == 1


# ═══════════════════════════════════════════════════════════════════════
# Group 9 — Provenance references approval record
# ═══════════════════════════════════════════════════════════════════════


def test_stdout_error_with_zero_return_code_fails_execution(tmp_path, monkeypatch):
    """Phase 6B: dcm2niix stdout errors fail even when return code is 0."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    def stdout_error_runner(argv):
        return type("R", (), {
            "returncode": 0,
            "stdout": "Error: invalid option '-b -ba'",
            "stderr": "",
        })()

    _patch_subprocess_with(monkeypatch, stdout_error_runner)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )

    assert result.status == "failed"
    assert any("reported_error=True" in err for err in result.errors)


def test_missing_expected_nifti_fails_execution(tmp_path, monkeypatch):
    """Phase 6B: a zero-return dcm2niix run without NIfTI output fails."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    def no_output_runner(argv):
        return type("R", (), {
            "returncode": 0,
            "stdout": "Conversion ok",
            "stderr": "",
        })()

    _patch_subprocess_with(monkeypatch, no_output_runner)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )

    assert result.status == "failed"
    assert any("expected_nifti_exists=False" in err for err in result.errors)


def test_provenance_references_approval_record(tmp_path, monkeypatch):
    """Gate 9: Execution provenance references approval record path."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_successful_runner)
    run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )

    provenance_path = project_dir / "conversion_runs" / "conv-test" / "execution_provenance.json"
    assert provenance_path.exists()
    data = json.loads(provenance_path.read_text())
    meta = data.get("metadata", {})
    assert "approval_record_path" in meta, "Provenance must reference approval record"
    assert "approval_status" in meta


# ═══════════════════════════════════════════════════════════════════════
# Group 10 — Provenance references audit final
# ═══════════════════════════════════════════════════════════════════════


def test_provenance_references_audit_final(tmp_path, monkeypatch):
    """Gate 10: Execution provenance references audit final path."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_successful_runner)
    run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )

    provenance_path = project_dir / "conversion_runs" / "conv-test" / "execution_provenance.json"
    data = json.loads(provenance_path.read_text())
    meta = data.get("metadata", {})
    assert "audit_record_path" in meta
    assert "audit_final_path" in meta
    assert "audit_state" in meta


# ═══════════════════════════════════════════════════════════════════════
# Group 11 — Provenance references checksum snapshots
# ═══════════════════════════════════════════════════════════════════════


def test_provenance_references_checksum_snapshots(tmp_path, monkeypatch):
    """Gate 11: Execution provenance references checksum paths."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_successful_runner)
    run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )

    provenance_path = project_dir / "conversion_runs" / "conv-test" / "execution_provenance.json"
    data = json.loads(provenance_path.read_text())
    meta = data.get("metadata", {})
    assert "checksum_before_path" in meta
    assert "checksum_after_path" in meta


# ═══════════════════════════════════════════════════════════════════════
# Group 12 — Provenance references rollback plan
# ═══════════════════════════════════════════════════════════════════════


def test_provenance_records_dcm2niix_binary_and_commands(tmp_path, monkeypatch):
    """Phase 6B: provenance records dcm2niix binary SHA, strategy, argv, and duration."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_successful_runner)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "succeeded"

    provenance_path = project_dir / "conversion_runs" / "conv-test" / "execution_provenance.json"
    data = json.loads(provenance_path.read_text())
    meta = data.get("metadata", {})

    assert meta["dcm2niix_version"] == "v1.0.20260416"
    assert meta["dcm2niix_expected_version"] == "v1.0.20260416"
    assert meta["dcm2niix_executable_path"]
    assert meta["dcm2niix_detection_strategy"] in {"env_var", "mamba_env", "path", "bundled"}
    assert meta["dcm2niix_binary_sha256"]
    assert meta["dcm2niix_command_count"] >= 1
    first_command = meta["dcm2niix_commands"][0]
    assert isinstance(first_command["argv"], list)
    assert first_command["argv"][0] == meta["dcm2niix_executable_path"]
    assert first_command["duration_ms"] >= 0
    assert first_command["return_code"] == 0


def test_provenance_references_rollback_plan(tmp_path, monkeypatch):
    """Gate 12: Execution provenance references rollback plan path."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_successful_runner)
    run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )

    provenance_path = project_dir / "conversion_runs" / "conv-test" / "execution_provenance.json"
    data = json.loads(provenance_path.read_text())
    meta = data.get("metadata", {})
    assert "rollback_plan_path" in meta


# ═══════════════════════════════════════════════════════════════════════
# Group 13 — Failure result references rollback plan
# ═══════════════════════════════════════════════════════════════════════


def test_failure_references_rollback_plan(tmp_path, monkeypatch):
    """Gate 13: On failure, audit final references rollback result path."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_failing_runner)
    run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )

    audit_final_path = project_dir / "conversion_runs" / "conv-test" / "audit_execution_final.json"
    data = json.loads(audit_final_path.read_text())
    assert data["rollback_plan_path"], "Rollback plan path must be present on failure"
    assert data["rollback_result_path"] is not None, "Rollback result path must be referenced on failure"


# ═══════════════════════════════════════════════════════════════════════
# Group 14 — No rawdata modification
# ═══════════════════════════════════════════════════════════════════════


def test_no_rawdata_modification(tmp_path, monkeypatch):
    """Gate 14: Rawdata must not be modified during execution."""
    _monkeypatch_dcm2niix_available(monkeypatch, tmp_path)
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    rawdata_dir = tmp_path / "rawdata"
    rawdata_dir.mkdir()
    (rawdata_dir / "test.dcm").write_text("FAKE DICOM")
    rawdata_mtime_before = (rawdata_dir / "test.dcm").stat().st_mtime

    _setup_complete_review_package(project_dir, "conv-test")

    _patch_subprocess_with(monkeypatch, _fake_successful_runner)
    run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
        rawdata_dir=str(rawdata_dir),
    )

    rawdata_mtime_after = (rawdata_dir / "test.dcm").stat().st_mtime
    assert rawdata_mtime_before == rawdata_mtime_after, "Rawdata must not be modified"
    assert rawdata_dir.exists(), "Rawdata must still exist"


# ═══════════════════════════════════════════════════════════════════════
# Group 15 — run_conversion_execute() remains blocked
# ═══════════════════════════════════════════════════════════════════════


def test_run_conversion_execute_still_blocked():
    """Gate 15: run_conversion_execute() must still block for normal users."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True, "Public conversion must remain disabled"


# ═══════════════════════════════════════════════════════════════════════
# Group 16 — No public endpoint added
# ═══════════════════════════════════════════════════════════════════════


def test_no_public_conversion_endpoint():
    """Gate 16: Public /conversion/execute endpoint exists but is blocked by default.

    In Phase 4L-2 the endpoint is implemented behind env flags and approval gates.
    Without env flags, it returns 200 with status=disabled/blocked.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.backend.app.main import app

    client = TestClient(app)
    resp = client.post("/api/projects/test/conversion/execute", json={})
    assert resp.status_code == 200, f"Expected 200 blocked, got {resp.status_code}"
    data = resp.json()
    assert data["ok"] is False
    assert data["status"] in ("disabled", "blocked")

    # /conversion/run must still not exist
    resp2 = client.post("/api/projects/test/conversion/run", json={})
    assert resp2.status_code in (404, 405, 422), f"Expected 404/405/422, got {resp2.status_code}"


# ═══════════════════════════════════════════════════════════════════════
# Group 17 — No frontend execute button
# ═══════════════════════════════════════════════════════════════════════


def test_no_frontend_execute_button():
    """Gate 17: No frontend execute button with onClick handler exists."""
    import os
    review_panel_paths = [
        "src/frontend/src/components/DicomConversionReviewPanel.tsx",
        "src/frontend/src/components/DicomConversionReviewPanel.jsx",
    ]
    found_execute_button = False
    for rel_path in review_panel_paths:
        full_path = os.path.join(os.getcwd(), rel_path)
        if os.path.exists(full_path):
            lines = open(full_path, encoding="utf-8").read().splitlines()
            for line in lines:
                stripped = line.strip()
                # Skip comments
                if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("#"):
                    continue
                # Look for onClick handlers that trigger conversion execution
                if ("Run Conversion" in stripped or "Execute Conversion" in stripped) and "onClick" in stripped:
                    found_execute_button = True
                    break
    assert not found_execute_button, (
        "No 'Run Conversion' or 'Execute Conversion' onClick handler must exist in frontend"
    )


# ═══════════════════════════════════════════════════════════════════════
# Group 18 — No SPM/DPABI/MATLAB enabled
# ═══════════════════════════════════════════════════════════════════════


def test_no_spm_dpabi_matlab_enabled():
    """Gate 18: SPM/DPABI/MATLAB must remain disabled."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    import inspect
    source = inspect.getsource(run_internal_user_dicom_conversion_from_persisted_package)
    assert "import spm" not in source.lower()
    assert "import matlab" not in source.lower()
    assert "import dpabi" not in source.lower()
    assert "spm(" not in source
    assert "dpabi(" not in source.lower()
    assert "MATLAB" not in source


# ═══════════════════════════════════════════════════════════════════════
# Group 19 — No shell=True
# ═══════════════════════════════════════════════════════════════════════


def test_no_shell_true():
    """Gate 19: No shell=True anywhere in the internal conversion function."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    import inspect
    source = inspect.getsource(run_internal_user_dicom_conversion_from_persisted_package)
    # Remove docstrings to avoid false positives in comments
    lines = [l for l in source.splitlines() if '"""' not in l]
    code = "\n".join(lines)
    assert "shell=True" not in code, "shell=True must never be used"


# ═══════════════════════════════════════════════════════════════════════
# Group 20 — No subprocess when approval incomplete
# ═══════════════════════════════════════════════════════════════════════


def test_no_subprocess_when_approval_incomplete(tmp_path, monkeypatch):
    """Gate 20: No subprocess when approval is incomplete."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    run_dir = _setup_complete_review_package(project_dir, "conv-test")
    # Missing confirm_execution in approval
    bad_approval = _make_approved_approval_record()
    bad_approval["confirm_execution"] = False
    (run_dir / "approval_record.json").write_text(json.dumps(bad_approval))

    import subprocess as sp
    called = []
    monkeypatch.setattr(sp, "run", lambda *a, **kw: called.append(a) or _fake_successful_runner(a[0]))
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test", "conv-test", env=_ALL_FLAGS, project_dir=str(project_dir),
    )
    assert result.status == "blocked"
    assert len(called) == 0, "Subprocess must not be called when approval incomplete"
