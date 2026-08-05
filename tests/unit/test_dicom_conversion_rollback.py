"""Tests for DICOM conversion real rollback — Phase 4J-0.

Tests dry-run, quarantine, delete modes, path protection, and safety.
Never touches rawdata.  Uses tmp_path for all test files.
"""

from __future__ import annotations

from pathlib import Path

from src.backend.app.schemas.dicom_conversion_safety import (
    DicomConversionRollbackRequest,
    classify_rollback_candidate,
)


def _make_fake_outputs(tmp_path: Path) -> tuple[str, str, Path]:
    """Create fake conversion outputs. Returns (project_dir, output_root, test_file_path)."""
    project_dir = str(tmp_path / "project")
    output_root = str(Path(project_dir) / "conversion_runs" / "conv-test")
    Path(output_root).mkdir(parents=True)
    test_file = Path(output_root) / "generated.nii.gz"
    test_file.write_text("FAKE NIFTI")
    (Path(output_root) / "approval_record.json").write_text("{}")
    return project_dir, output_root, test_file


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Dry-run mode
# ═══════════════════════════════════════════════════════════════════════


def test_dry_run_deletes_nothing(tmp_path):
    from src.backend.app.services.dicom_conversion_safety import run_conversion_rollback

    project_dir, output_root, test_file = _make_fake_outputs(tmp_path)
    req = DicomConversionRollbackRequest(
        conversion_run_id="conv-test",
        rollback_mode="dry_run",
        expected_output_root=output_root,
    )
    result = run_conversion_rollback(req, project_dir=project_dir)
    assert result.mode == "dry_run"
    assert result.status in {"completed", "dry_run"}
    assert test_file.exists(), "Dry-run must not delete files"


def test_dry_run_reports_removable_paths(tmp_path):
    from src.backend.app.services.dicom_conversion_safety import run_conversion_rollback

    project_dir, output_root, test_file = _make_fake_outputs(tmp_path)
    req = DicomConversionRollbackRequest(
        conversion_run_id="conv-test",
        rollback_mode="dry_run",
        expected_output_root=output_root,
    )
    result = run_conversion_rollback(req, project_dir=project_dir)
    assert len(result.removed_paths) >= 1  # At least the generated.nii.gz
    assert str(test_file) in result.removed_paths


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Quarantine mode
# ═══════════════════════════════════════════════════════════════════════


def test_quarantine_moves_file(tmp_path):
    from src.backend.app.services.dicom_conversion_safety import run_conversion_rollback

    project_dir, output_root, test_file = _make_fake_outputs(tmp_path)
    req = DicomConversionRollbackRequest(
        conversion_run_id="conv-test",
        rollback_mode="quarantine",
        expected_output_root=output_root,
    )
    result = run_conversion_rollback(req, project_dir=project_dir)
    assert result.mode == "quarantine"
    assert len(result.quarantined_paths) >= 1
    assert not test_file.exists(), "Quarantine must move the file"


def test_quarantine_does_not_move_protected_files(tmp_path):
    from src.backend.app.services.dicom_conversion_safety import run_conversion_rollback

    project_dir, output_root, test_file = _make_fake_outputs(tmp_path)
    approval = Path(output_root) / "approval_record.json"
    assert approval.exists()

    req = DicomConversionRollbackRequest(
        conversion_run_id="conv-test",
        rollback_mode="quarantine",
        expected_output_root=output_root,
    )
    result = run_conversion_rollback(req, project_dir=project_dir)
    assert approval.exists(), "Protected files must not be moved"
    assert any("approval_record.json" in p for p in result.protected_paths)


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Delete mode
# ═══════════════════════════════════════════════════════════════════════


def test_delete_without_confirmation_blocked(tmp_path):
    from src.backend.app.services.dicom_conversion_safety import run_conversion_rollback

    project_dir, output_root, test_file = _make_fake_outputs(tmp_path)
    req = DicomConversionRollbackRequest(
        conversion_run_id="conv-test",
        rollback_mode="delete",
        confirm_rollback=False,
        expected_output_root=output_root,
    )
    result = run_conversion_rollback(req, project_dir=project_dir)
    assert result.status == "blocked"
    assert test_file.exists()


def test_delete_with_confirmation_deletes_file(tmp_path):
    from src.backend.app.services.dicom_conversion_safety import run_conversion_rollback

    project_dir, output_root, test_file = _make_fake_outputs(tmp_path)
    req = DicomConversionRollbackRequest(
        conversion_run_id="conv-test",
        rollback_mode="delete",
        confirm_rollback=True,
        expected_output_root=output_root,
    )
    result = run_conversion_rollback(req, project_dir=project_dir)
    assert result.mode == "delete"
    assert len(result.removed_paths) >= 1
    assert not test_file.exists()


def test_delete_does_not_delete_protected_files(tmp_path):
    from src.backend.app.services.dicom_conversion_safety import run_conversion_rollback

    project_dir, output_root, test_file = _make_fake_outputs(tmp_path)
    approval = Path(output_root) / "approval_record.json"

    req = DicomConversionRollbackRequest(
        conversion_run_id="conv-test",
        rollback_mode="delete",
        confirm_rollback=True,
        expected_output_root=output_root,
    )
    result = run_conversion_rollback(req, project_dir=project_dir)
    assert approval.exists()
    assert any("approval_record.json" in p for p in result.protected_paths)


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Path safety
# ═══════════════════════════════════════════════════════════════════════


def test_rawdata_path_protected(tmp_path):
    classification = classify_rollback_candidate(
        str(tmp_path / "rawdata" / "file.dcm"),
        output_root=str(tmp_path / "output"),
        rawdata_roots=[str(tmp_path / "rawdata")],
    )
    assert classification == "protected"


def test_path_outside_output_root_protected(tmp_path):
    classification = classify_rollback_candidate(
        str(tmp_path / "other" / "file.nii"),
        output_root=str(tmp_path / "output"),
    )
    assert classification == "protected"


def test_path_traversal_rejected():
    classification = classify_rollback_candidate(
        "/output/../rawdata/file.nii",
        output_root="/output",
    )
    assert classification == "protected"


def test_protected_filename_identified():
    classification = classify_rollback_candidate(
        "/output/approval_record.json",
        output_root="/output",
    )
    assert classification == "protected"


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Existing safety
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


def test_rollback_service_no_subprocess():
    import src.backend.app.services.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content


def test_rollback_schema_no_subprocess():
    import src.backend.app.schemas.dicom_conversion_safety as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content
