"""Tests for checksum/rollback integration — Phase 4H-2.

Tests that persisted plans include checksum snapshots and rollback plans,
that review packages list these new files, and that export still excludes
image data.  No dcm2niix.  No rawdata modification.
"""

from __future__ import annotations

import json
from pathlib import Path


def _make_persisted_package(tmp_path: Path) -> str:
    """Create a fake project with rawdata and persist a plan."""
    from src.backend.app.schemas.dicom_conversion_approval import (
        DicomConversionApprovalRecord,
    )
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )

    project_dir = str(tmp_path / "project")
    rawdata_dir = str(tmp_path / "rawdata")
    Path(rawdata_dir).mkdir(parents=True)
    (Path(rawdata_dir) / "test.dcm").write_text("FAKE DICOM")

    record = DicomConversionApprovalRecord(
        approval_id="test",
        project_id="test",
        status="approved",
        approved=True,
        approved_by="tester",
        mappings_reviewed=True,
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

    result = persist_conversion_plan(
        project_id="test",
        approval_record=record,
        project_dir=project_dir,
        rawdata_dir=rawdata_dir,
    )
    assert result.ok, f"Persist failed: {result.errors}"
    return project_dir


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Persisted plan writes checksum and rollback
# ═══════════════════════════════════════════════════════════════════════


def test_persisted_plan_writes_checksum_json(tmp_path):
    project_dir = _make_persisted_package(tmp_path)
    run_dir = list(Path(project_dir).glob("conversion_runs/*"))
    assert len(run_dir) == 1
    checksum_path = run_dir[0] / "rawdata_checksum_before.json"
    assert checksum_path.exists()
    data = json.loads(checksum_path.read_text())
    assert "fingerprint" in data or "note" in data


def test_persisted_plan_writes_rollback_plan(tmp_path):
    project_dir = _make_persisted_package(tmp_path)
    run_dir = list(Path(project_dir).glob("conversion_runs/*"))
    assert len(run_dir) == 1
    rollback_path = run_dir[0] / "rollback_plan_dry_run.json"
    assert rollback_path.exists()
    data = json.loads(rollback_path.read_text())
    assert "dry_run_only" in data.get("safety_flags", {})


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Review package lists new files
# ═══════════════════════════════════════════════════════════════════════


def test_review_package_lists_checksum_file(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )

    project_dir = _make_persisted_package(tmp_path)
    run_dir = list(Path(project_dir).glob("conversion_runs/*"))
    run_id = run_dir[0].name

    result = read_conversion_review_package("test", run_id, project_dir=project_dir)
    kinds = {f.kind for f in result.files}
    assert "rawdata_checksum_before" in kinds
    assert "rollback_plan_dry_run" in kinds


def test_review_package_checksum_summary(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )

    project_dir = _make_persisted_package(tmp_path)
    run_dir = list(Path(project_dir).glob("conversion_runs/*"))
    run_id = run_dir[0].name

    result = read_conversion_review_package("test", run_id, project_dir=project_dir)
    assert "rawdata_fingerprint" in result.approval_summary


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Audit export excludes image data
# ═══════════════════════════════════════════════════════════════════════


def test_export_excludes_dcm(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )

    project_dir = _make_persisted_package(tmp_path)
    run_dir = list(Path(project_dir).glob("conversion_runs/*"))
    run_id = run_dir[0].name

    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    import zipfile

    with zipfile.ZipFile(result.export_path) as zf:
        names = zf.namelist()
    for name in names:
        assert not name.endswith(".dcm")


def test_export_excludes_nifti(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )

    project_dir = _make_persisted_package(tmp_path)
    run_dir = list(Path(project_dir).glob("conversion_runs/*"))
    run_id = run_dir[0].name
    (run_dir[0] / "fake.nii.gz").write_text("FAKE")

    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    import zipfile

    with zipfile.ZipFile(result.export_path) as zf:
        names = zf.namelist()
    assert "fake.nii.gz" not in names


def test_export_includes_checksum_metadata(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )

    project_dir = _make_persisted_package(tmp_path)
    run_dir = list(Path(project_dir).glob("conversion_runs/*"))
    run_id = run_dir[0].name

    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    import zipfile

    with zipfile.ZipFile(result.export_path) as zf:
        names = zf.namelist()
    assert "rawdata_checksum_before.json" in names
    assert "rollback_plan_dry_run.json" in names


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Rollback safety
# ═══════════════════════════════════════════════════════════════════════


def test_rollback_protects_rawdata_paths(tmp_path):
    from src.backend.app.schemas.dicom_conversion_safety import (
        build_conversion_rollback_plan,
    )

    rawdata = str(tmp_path / "rawdata")
    Path(rawdata).mkdir()
    (Path(rawdata) / "test.dcm").write_text("x")

    plan = build_conversion_rollback_plan(
        rawdata, project_dir=str(tmp_path), rawdata_roots=[rawdata]
    )
    assert len(plan.removable_paths) == 0
    assert len(plan.protected_paths) >= 1


def test_rollback_dry_run_deletes_nothing(tmp_path):
    from src.backend.app.schemas.dicom_conversion_safety import (
        build_conversion_rollback_plan,
        run_conversion_rollback_dry_run,
    )

    output = tmp_path / "output"
    output.mkdir()
    test_file = output / "data.json"
    test_file.write_text("test")

    plan = build_conversion_rollback_plan(str(output), project_dir=str(tmp_path))
    result = run_conversion_rollback_dry_run(plan)
    assert result.safety_flags["no_files_deleted"] is True
    assert test_file.exists()


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Approval schema checksum fields
# ═══════════════════════════════════════════════════════════════════════


def test_approval_record_has_checksum_fields():
    from src.backend.app.schemas.dicom_conversion_approval import (
        DicomConversionApprovalRecord,
    )

    record = DicomConversionApprovalRecord()
    d = record.model_dump()
    assert "rawdata_checksum_confirmed" in d
    assert "pre_conversion_checksum_required" in d
    assert "checksum_mismatch_policy" in d
    assert "rollback_plan_confirmed" in d


def test_approval_checksum_defaults():
    from src.backend.app.schemas.dicom_conversion_approval import (
        DicomConversionApprovalRecord,
    )

    record = DicomConversionApprovalRecord()
    assert record.rawdata_checksum_confirmed is False
    assert record.pre_conversion_checksum_required is True
    assert record.checksum_mismatch_policy == "block"


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Existing safety
# ═══════════════════════════════════════════════════════════════════════


def test_user_conversion_still_disabled():
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )

    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True


def test_no_subprocess_in_safety_schema():
    import src.backend.app.schemas.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content


def test_spm_dpabi_matlab_still_disabled():
    import src.backend.app.schemas.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import spm" not in content.lower()
    assert "import matlab" not in content.lower()
