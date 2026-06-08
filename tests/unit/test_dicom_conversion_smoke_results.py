"""Tests for synthetic smoke result reader — Phase 4F-1.

Tests reading synthetic conversion smoke result metadata (manifest,
provenance, logs, output files).  No dcm2niix called.  No image data
parsed.  No rawdata modified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_smoke_results(tmp_path: Path) -> tuple[str, str]:
    """Create synthetic smoke results and return (project_dir, run_id)."""
    project_dir = str(tmp_path / "project")
    run_id = "conv-smoke001"
    run_dir = Path(project_dir) / "conversion_runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "logs").mkdir()

    # Write output manifest (post-execution)
    manifest = {
        "project_id": "test", "run_id": run_id, "node_id": "dicom_to_nifti",
        "items": [{"kind": "nifti", "path": f"{run_dir}/test.nii.gz", "exists": True, "size_bytes": 100}],
    }
    (run_dir / "output_manifest.json").write_text(json.dumps(manifest))

    # Write provenance
    provenance = {"project_id": "test", "backend": "external", "return_code": 0}
    (run_dir / "execution_provenance.json").write_text(json.dumps(provenance))

    # Write logs
    (run_dir / "logs" / "dcm2niix_stdout.log").write_text("Conversion successful\n")
    (run_dir / "logs" / "dcm2niix_stderr.log").write_text("")

    # Write a fake NIfTI output
    (run_dir / "test_output.nii.gz").write_text("FAKE NIFTI")

    return project_dir, run_id


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Read smoke results
# ═══════════════════════════════════════════════════════════════════════


def test_read_returns_manifest_and_provenance(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_synthetic_smoke_results,
    )
    project_dir, run_id = _make_smoke_results(tmp_path)
    result = read_synthetic_smoke_results("test", run_id, project_dir=project_dir)
    assert result.ok is True
    assert result.status == "results_available"
    assert result.manifest_path is not None
    assert result.provenance_path is not None


def test_read_reports_created_artifacts(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_synthetic_smoke_results,
    )
    project_dir, run_id = _make_smoke_results(tmp_path)
    result = read_synthetic_smoke_results("test", run_id, project_dir=project_dir)
    kinds = {f.kind for f in result.files}
    assert "manifest" in kinds
    assert "provenance" in kinds
    assert "stdout_log" in kinds
    assert "nifti_output" in kinds


def test_nifti_is_metadata_only(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_synthetic_smoke_results,
    )
    project_dir, run_id = _make_smoke_results(tmp_path)
    result = read_synthetic_smoke_results("test", run_id, project_dir=project_dir)
    nifti_files = [f for f in result.files if f.kind == "nifti_output"]
    assert len(nifti_files) >= 1
    for nf in nifti_files:
        assert nf.metadata_only is True


def test_missing_manifest_returns_warning(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_synthetic_smoke_results,
    )
    project_dir = str(tmp_path / "project")
    run_id = "conv-empty"
    run_dir = Path(project_dir) / "conversion_runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "logs").mkdir()

    result = read_synthetic_smoke_results("test", run_id, project_dir=project_dir)
    assert result.ok is True  # Not an error, just no results
    assert result.status == "no_results"


def test_missing_logs_returns_warning_not_500(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_synthetic_smoke_results,
    )
    project_dir, run_id = _make_smoke_results(tmp_path)
    # Remove the logs dir
    import shutil
    shutil.rmtree(Path(project_dir) / "conversion_runs" / run_id / "logs")
    result = read_synthetic_smoke_results("test", run_id, project_dir=project_dir)
    assert result.ok is True
    log_files = [f for f in result.files if f.kind in ("stdout_log", "stderr_log")]
    for lf in log_files:
        assert not lf.exists


def test_safety_flags_present(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_synthetic_smoke_results,
    )
    project_dir, run_id = _make_smoke_results(tmp_path)
    result = read_synthetic_smoke_results("test", run_id, project_dir=project_dir)
    assert result.safety_flags["synthetic_only"] is True
    assert result.safety_flags["no_user_rawdata_conversion"] is True
    assert result.safety_flags["metadata_only"] is True
    assert result.safety_flags["clinical_use_prohibited"] is True


def test_no_dcm2niix_called(tmp_path):
    from src.backend.app.services.dicom_conversion_review_package import (
        read_synthetic_smoke_results,
    )
    import inspect
    source = inspect.getsource(read_synthetic_smoke_results)
    assert "import subprocess" not in source
    assert "from subprocess" not in source
