"""Integration test for internal FunRaw/T1Raw conversion smoke — Phase 4I-1.

Runs the internal-only user-data conversion prototype on the real DemoData
project.  All tests are skipped by default unless all 10 env flags are set,
dcm2niix is on PATH, pydicom is available, and a real dataset path is
provided via env variable.

To enable:
  Set all 10 MEDIMAGE_* flags to "1"
  Set MEDIMAGE_INTERNAL_DICOM_SMOKE_RAWDATA_DIR to the DemoData path
  Ensure dcm2niix and pydicom are available
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _all_flags_present() -> bool:
    required = [
        "MEDIMAGE_ENABLE_DICOM_CONVERSION",
        "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE",
        "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE",
        "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION",
        "MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE",
        "MEDIMAGE_ALLOW_INTERNAL_USER_DICOM_CONVERSION_PROTOTYPE",
        "MEDIMAGE_MATLAB_ENABLED",
        "MEDIMAGE_SPM_SMOKE_ENABLED",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
    ]
    return all(os.environ.get(f) == "1" for f in required)


def _dcm2niix_available() -> bool:
    import shutil
    return shutil.which("dcm2niix") is not None


def _pydicom_available() -> bool:
    try:
        import pydicom  # noqa: F401
        return True
    except ImportError:
        return False


_REQUIRED_SKIP_FLAGS = "all 10 MEDIMAGE env flags + dcm2niix + pydicom + MEDIMAGE_INTERNAL_DICOM_SMOKE_RAWDATA_DIR"


# ═══════════════════════════════════════════════════════════════════════
# All tests skipped by default
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not _all_flags_present(), reason=_REQUIRED_SKIP_FLAGS)
@pytest.mark.skipif(not _dcm2niix_available(), reason="dcm2niix not on PATH")
@pytest.mark.skipif(not _pydicom_available(), reason="pydicom not installed")
def test_internal_demo_conversion_smoke(tmp_path):
    """Run internal conversion on the configured real DemoData project."""
    rawdata_dir = os.environ.get("MEDIMAGE_INTERNAL_DICOM_SMOKE_RAWDATA_DIR", "")
    if not rawdata_dir or not Path(rawdata_dir).exists():
        pytest.skip("MEDIMAGE_INTERNAL_DICOM_SMOKE_RAWDATA_DIR not set or not found")

    # 1. Create project via mock_store
    from src.backend.app.services.mock_store import mock_store
    from src.backend.app.schemas.desktop import ProjectDetail

    project_id = "internal-conv-test"
    project = ProjectDetail(
        id=project_id,
        name="Internal Conv Smoke",
        study_id="ICS-001",
        modality="rs-fMRI",
        sequences=["BOLD", "T1"],
        subjects_count=3,
        scans_count=6,
        total_size="1 GB",
        created_date="2026-06-08",
        current_pipeline_id="dicom-to-nifti",
        current_model_id="dcm2niix",
        metadata={
            "rawdata_dir": rawdata_dir,
            "project_dir": str(tmp_path / "project"),
        },
    )
    mock_store.add_project(project, health_status="Review", rawdata_dir=rawdata_dir)

    # 2. Persist approval package
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )
    from src.backend.app.schemas.dicom_conversion_approval import (
        DicomConversionApprovalRecord,
    )

    approval = DicomConversionApprovalRecord(
        approval_id="internal-test",
        project_id=project_id,
        status="approved",
        approved=True,
        approved_by="internal-smoke",
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

    persist_result = persist_conversion_plan(
        project_id=project_id,
        approval_record=approval,
        project_dir=str(tmp_path / "project"),
        rawdata_dir=rawdata_dir,
    )
    assert persist_result.ok, f"Persist failed: {persist_result.errors}"
    run_id = persist_result.conversion_run_id

    # 3. Run internal conversion
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    result = run_internal_user_dicom_conversion_from_persisted_package(
        project_id=project_id,
        conversion_run_id=run_id,
        env=None,
        project_dir=str(tmp_path / "project"),
        rawdata_dir=rawdata_dir,
    )

    # 4. Validate results
    assert result.status in {"succeeded", "warning"}, (
        f"status={result.status} errors={result.errors} warnings={result.warnings}"
    )
    assert result.manifest_path is not None
    assert result.provenance_path is not None
    assert result.stdout_log_path is not None
    assert result.stderr_log_path is not None

    # Check output files exist
    assert Path(result.manifest_path).exists(), f"Manifest missing: {result.manifest_path}"
    assert Path(result.stdout_log_path).exists(), f"Stdout log missing: {result.stdout_log_path}"

    # Check no output under rawdata
    for p in Path(result.output_root).rglob("*"):
        assert not str(p).startswith(rawdata_dir), f"Output leaked to rawdata: {p}"

    # Check rawdata still has DICOM files
    dcm_files = list(Path(rawdata_dir).rglob("*.dcm"))
    assert len(dcm_files) >= 1, "Rawdata DICOM files missing"


@pytest.mark.skipif(not _all_flags_present(), reason=_REQUIRED_SKIP_FLAGS)
def test_user_conversion_still_disabled():
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True
    assert result.execution_blocked is True
