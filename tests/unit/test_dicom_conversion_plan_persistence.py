"""Tests for DICOM conversion plan persistence — Phase 4E-0.

Tests approval gate evaluation, run directory reservation, metadata write,
and safety invariants.  No dcm2niix is called.  No NIfTI files are created.
No rawdata is modified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.backend.app.schemas.dicom_conversion_approval import (
    DicomConversionApprovalRecord,
    DicomConversionGateDecision,
    DicomConversionOverwritePolicy,
    DicomConversionPlanPersistenceResponse,
    DicomConversionRunReservation,
    build_conversion_run_id,
    build_conversion_run_paths,
    evaluate_conversion_approval_gate,
    is_reserved_run_directory_safe,
    validate_conversion_run_paths,
)


def _make_approved_record() -> DicomConversionApprovalRecord:
    return DicomConversionApprovalRecord(
        approval_id="test-approval",
        project_id="test-project",
        status="approved",
        approved=True,
        approved_by="researcher",
        mappings_reviewed=True,
        output_root="/project/converted",
        output_root_confirmed=True,
        output_root_under_project=True,
        output_root_not_rawdata=True,
        overwrite_policy="fail_if_exists",
        rawdata_read_only_confirmed=True,
        command_templates_reviewed=True,
        no_shell_string_confirmed=True,
        dcm2niix_availability_confirmed=True,
        env_flags_confirmed=True,
        rollback_policy_acknowledged=True,
        clinical_use_prohibited_acknowledged=True,
        external_tool_acknowledgement=True,
        risk_acknowledgement=True,
        confirm_execution=True,
    )


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Blocked approval returns blocked persistence
# ═══════════════════════════════════════════════════════════════════════


def test_incomplete_approval_returns_blocked(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = DicomConversionApprovalRecord()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
    )
    assert result.ok is False
    assert result.status == "blocked"


def test_missing_project_dir_returns_invalid(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir="",
    )
    assert result.ok is False
    assert result.status == "invalid"


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Safe approval reserves run directory
# ═══════════════════════════════════════════════════════════════════════


def test_safe_approval_reserves_run_directory(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    project_dir = str(tmp_path / "project")
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
    )
    assert result.ok is True
    assert result.status == "reserved"
    assert result.conversion_run_id is not None
    assert result.reservation is not None
    assert result.reservation.run_dir is not None
    assert result.reservation.run_dir.startswith(project_dir)


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Reservation path safety
# ═══════════════════════════════════════════════════════════════════════


def test_reservation_under_project_dir(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    project_dir = str(tmp_path / "my_project")
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
    )
    assert result.reservation.run_dir.startswith(project_dir)


def test_reservation_not_under_rawdata(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    project_dir = str(tmp_path / "project")
    rawdata_dir = str(tmp_path / "rawdata")
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
        rawdata_dir=rawdata_dir,
    )
    assert result.ok
    assert not result.reservation.run_dir.startswith(rawdata_dir)


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Files written
# ═══════════════════════════════════════════════════════════════════════


def test_writes_approval_record_json(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
    )
    assert Path(result.reservation.approval_record_path).exists()


def test_writes_preflight_snapshot_json(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
        preflight_snapshot={"status": "ready"},
    )
    assert Path(result.reservation.preflight_snapshot_path).exists()
    content = json.loads(Path(result.reservation.preflight_snapshot_path).read_text())
    assert content["status"] == "ready"


def test_writes_mapping_snapshot(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
        mappings=[{"subject_id": "sub-001"}],
    )
    assert Path(result.reservation.mapping_snapshot_path).exists()


def test_writes_command_templates(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
        command_templates=[{"executable": "dcm2niix"}],
    )
    assert Path(result.reservation.command_templates_path).exists()


def test_writes_planned_manifest_and_provenance(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
    )
    assert Path(result.reservation.planned_manifest_path).exists()
    assert Path(result.reservation.planned_provenance_path).exists()


def test_writes_readme(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
    )
    readme = Path(result.reservation.run_dir) / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "NO CONVERSION EXECUTED" in content


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — No NIfTI files, no dcm2niix
# ═══════════════════════════════════════════════════════════════════════


def test_no_nifti_files_created(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=str(tmp_path / "project"),
    )
    run_dir = Path(result.reservation.run_dir)
    nifti_files = list(run_dir.rglob("*.nii*"))
    assert len(nifti_files) == 0


def test_persistence_service_has_no_subprocess():
    import inspect
    from src.backend.app.services import dicom_conversion_plan_persistence as mod

    source = inspect.getsource(mod.persist_conversion_plan)
    assert "import subprocess" not in source
    # Only check actual code, not docstring text
    lines = [l for l in source.splitlines() if '"""' not in l and not l.strip().startswith("#")]
    code = "\n".join(lines)
    assert "shell=True" not in code


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Run directory collision
# ═══════════════════════════════════════════════════════════════════════


def test_fail_if_exists_blocks_collision(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    project_dir = str(tmp_path / "project")

    # First persist
    result1 = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
        overwrite_policy="fail_if_exists",
    )
    assert result1.ok

    # Second with same ID → collision
    result2 = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
        overwrite_policy="fail_if_exists",
    )
    assert result2.status == "already_exists"


def test_write_new_run_directory_creates_distinct_id(tmp_path):
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    record = _make_approved_record()
    project_dir = str(tmp_path / "project")

    result1 = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
        overwrite_policy="write_new_run_directory",
    )
    result2 = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
        overwrite_policy="write_new_run_directory",
    )
    assert result1.conversion_run_id != result2.conversion_run_id


# ═══════════════════════════════════════════════════════════════════════
# Group 7 — Pure helpers
# ═══════════════════════════════════════════════════════════════════════


def test_build_conversion_run_id():
    rid1 = build_conversion_run_id("proj", "hash1")
    rid2 = build_conversion_run_id("proj", "hash2")
    assert rid1.startswith("conv-")
    assert rid1 != rid2


def test_build_conversion_run_paths():
    paths = build_conversion_run_paths("/project", "conv-abc")
    assert paths["run_dir"] == "/project/conversion_runs/conv-abc"
    assert paths["approval_record_path"].startswith("/project/")


def test_validate_paths_safe():
    ok, issues = validate_conversion_run_paths(
        {"run_dir": "/project/runs/conv-001"}, "/project", "/rawdata"
    )
    assert ok is True


def test_validate_paths_under_rawdata_blocked():
    ok, issues = validate_conversion_run_paths(
        {"run_dir": "/rawdata/runs/conv-001"}, "/project", "/rawdata"
    )
    assert ok is False


def test_is_reserved_run_directory_safe():
    reservation = DicomConversionRunReservation(
        run_dir="/project/runs/conv-001",
        approval_record_path="/project/runs/conv-001/approval.json",
        output_root="/project/runs/conv-001",
    )
    assert is_reserved_run_directory_safe(reservation, "/project", "/rawdata") is True

    bad = DicomConversionRunReservation(
        run_dir="/rawdata/runs/conv-001",
        approval_record_path="/rawdata/runs/conv-001/approval.json",
        output_root="/rawdata/runs/conv-001",
    )
    assert is_reserved_run_directory_safe(bad, "/project", "/rawdata") is False
