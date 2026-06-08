"""Tests for DICOM conversion review package reader and audit export — Phase 4E-1.

Tests reading persisted packages and exporting metadata-only audit bundles.
No dcm2niix called. No image data exported. No rawdata modified.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest


def _make_persisted_package(tmp_path: Path, project_id: str = "test") -> tuple[str, str]:
    """Create a fake persisted review package and return (project_dir, conversion_run_id)."""
    project_dir = str(tmp_path / "project")
    run_id = "conv-test1234"
    run_dir = Path(project_dir) / "conversion_runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "logs").mkdir()

    files = {
        "approval_record.json": {"status": "approved", "approved": False},
        "audit_preview.json": {"note": "no conversion executed"},
        "preflight_snapshot.json": {"status": "ready"},
        "mapping_snapshot.json": {"mappings": [{"subject_id": "sub-001"}]},
        "command_templates.json": {"templates": [{"executable": "dcm2niix"}]},
        "planned_output_manifest.json": {"note": "planned manifest"},
        "planned_execution_provenance.json": {"note": "planned provenance"},
        "README.md": "# No conversion executed\n",
    }
    for name, content in files.items():
        (run_dir / name).write_text(json.dumps(content) if isinstance(content, dict) else content)
    (run_dir / "logs" / "stdout.log").write_text("# stdout placeholder\n")
    (run_dir / "logs" / "stderr.log").write_text("# stderr placeholder\n")
    return project_dir, run_id


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Read package
# ═══════════════════════════════════════════════════════════════════════


def test_read_package_returns_all_files(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = read_conversion_review_package("test", run_id, project_dir=project_dir)
    assert result.ok is True
    assert len(result.files) == 12  # 10 original + 2 Phase 4H-2 (checksum, rollback)
    kinds = {f.kind for f in result.files}
    assert "approval_record" in kinds
    assert "readme" in kinds


def test_read_package_missing_project_dir(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    result = read_conversion_review_package("test", "any", project_dir="")
    assert result.ok is False


def test_read_package_refuses_rawdata_path(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    # Pretend rawdata_dir overlaps — our path safety checks this
    result = read_conversion_review_package(
        "test", run_id, project_dir=project_dir, rawdata_dir=project_dir,
    )
    assert result.ok is False


def test_read_package_approval_summary(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = read_conversion_review_package("test", run_id, project_dir=project_dir)
    assert result.approval_summary.get("status") == "approved"


def test_read_package_mapping_count(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = read_conversion_review_package("test", run_id, project_dir=project_dir)
    assert result.mapping_count == 1
    assert result.command_template_count == 1


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Export bundle
# ═══════════════════════════════════════════════════════════════════════


def test_export_contains_metadata_files(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    assert result.ok is True
    assert result.export_path is not None
    assert Path(result.export_path).exists()
    assert result.size_bytes > 0
    assert result.sha256 is not None


def test_export_contains_sha256sums(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    with zipfile.ZipFile(result.export_path) as zf:
        names = zf.namelist()
    assert "SHA256SUMS.txt" in names


def test_export_uses_relative_paths(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    with zipfile.ZipFile(result.export_path) as zf:
        names = zf.namelist()
    for name in names:
        assert not name.startswith("/")
        assert not name.startswith("\\")
        assert ".." not in name


def test_export_excludes_dcm_files(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    # Plant a fake .dcm file in the run dir
    (Path(project_dir) / "conversion_runs" / run_id / "fake.dcm").write_text("FAKE")
    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    with zipfile.ZipFile(result.export_path) as zf:
        names = zf.namelist()
    assert "fake.dcm" not in names


def test_export_excludes_nifti_files(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    (Path(project_dir) / "conversion_runs" / run_id / "fake.nii").write_text("FAKE")
    (Path(project_dir) / "conversion_runs" / run_id / "fake.nii.gz").write_text("FAKE")
    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    with zipfile.ZipFile(result.export_path) as zf:
        names = zf.namelist()
    assert "fake.nii" not in names
    assert "fake.nii.gz" not in names


def test_export_stays_under_project_dir(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    assert result.export_path.startswith(project_dir)


def test_export_does_not_call_dcm2niix(tmp_path):
    """Export must not import or call subprocess."""
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    import inspect
    source = inspect.getsource(export_conversion_review_package)
    assert "import subprocess" not in source
    assert "shell=True" not in source


def test_export_safety_flags(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    project_dir, run_id = _make_persisted_package(tmp_path)
    result = export_conversion_review_package("test", run_id, project_dir=project_dir)
    assert result.safety_flags["metadata_only"] is True
    assert result.safety_flags["no_raw_dicom_included"] is True
    assert result.safety_flags["no_nifti_included"] is True
    assert result.safety_flags["no_conversion_executed"] is True
    assert result.safety_flags["clinical_use_prohibited"] is True


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Missing package
# ═══════════════════════════════════════════════════════════════════════


def test_read_missing_package_returns_ok_false(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_conversion_review_package,
    )
    result = read_conversion_review_package(
        "test", "nonexistent", project_dir=str(tmp_path / "project"),
    )
    assert result.ok is False


def test_export_missing_package_returns_ok_false(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        export_conversion_review_package,
    )
    result = export_conversion_review_package(
        "test", "nonexistent", project_dir=str(tmp_path / "project"),
    )
    assert result.ok is False
