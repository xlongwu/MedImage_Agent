"""Opt-in Windows smoke test for the in-project DICOM converter.

The test exercises the real ``DemoData/FunRaw`` and ``DemoData/T1Raw``
layout without MATLAB, SPM, DPABI, dcm2niix, or any other external program.
It is disabled unless the three reviewed-conversion gates and an explicit
dataset path are supplied.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_REQUIRED_FLAGS = (
    "MEDIMAGE_ENABLE_DICOM_CONVERSION",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION",
)


def _all_flags_present() -> bool:
    return all(os.environ.get(flag) == "1" for flag in _REQUIRED_FLAGS)


def _native_dependencies_available() -> bool:
    try:
        import nibabel  # noqa: F401
        import numpy  # noqa: F401
        import pydicom  # noqa: F401
    except ImportError:
        return False
    return True


_REQUIRED_SKIP_FLAGS = (
    "the three reviewed-conversion MEDIMAGE flags, native Python dependencies, "
    "and MEDIMAGE_INTERNAL_DICOM_SMOKE_RAWDATA_DIR"
)


@pytest.mark.skipif(not _all_flags_present(), reason=_REQUIRED_SKIP_FLAGS)
@pytest.mark.skipif(
    not _native_dependencies_available(),
    reason="native DICOM converter dependencies are unavailable",
)
def test_internal_demo_conversion_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Convert three DemoData subjects and prove rawdata remains unchanged."""
    rawdata_dir = Path(os.environ.get("MEDIMAGE_INTERNAL_DICOM_SMOKE_RAWDATA_DIR", "")).resolve()
    if not rawdata_dir.is_dir():
        pytest.skip("MEDIMAGE_INTERNAL_DICOM_SMOKE_RAWDATA_DIR is not a directory")

    from src.backend.app.schemas.desktop import ProjectDetail
    from src.backend.app.services.mock_store import mock_store

    project_id = "internal-native-conv-smoke"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project = ProjectDetail(
        id=project_id,
        name="Internal Native Conversion Smoke",
        study_id="ICS-001",
        modality="rs-fMRI",
        sequences=["BOLD", "T1"],
        subjects_count=3,
        scans_count=6,
        total_size="unknown",
        created_date="2026-07-16",
        current_pipeline_id="dicom-to-nifti",
        current_model_id="medimage-native",
        metadata={
            "rawdata_dir": str(rawdata_dir),
            "project_dir": str(project_dir),
        },
    )
    mock_store.add_project(
        project,
        health_status="Review",
        rawdata_dir=str(rawdata_dir),
    )

    from src.backend.app.schemas.dicom_conversion_approval import (
        DicomConversionApprovalRecord,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_preflight,
        run_internal_user_dicom_conversion_from_persisted_package,
    )
    from src.backend.app.services.dicom_conversion_plan_persistence import (
        persist_conversion_plan,
    )
    from src.backend.app.services.dicom_conversion_safety import (
        build_pre_conversion_rawdata_snapshot,
    )

    output_root = project_dir / "converted_bids"
    preflight = run_conversion_preflight(
        project_id,
        DicomConversionExecutionRequest(
            project_id=project_id,
            output_root=str(output_root),
        ),
    )
    assert preflight.status == "review_required", preflight.blocking_issues
    assert preflight.tool_available is True
    assert preflight.executable_path is None
    assert preflight.mapping_count == 6
    assert len(preflight.command_templates) == 6
    assert {mapping.subject_id for mapping in preflight.mappings} == {
        "sub-001",
        "sub-002",
        "sub-003",
    }
    assert all(template.tool == "medimage-native" for template in preflight.command_templates)

    approval = DicomConversionApprovalRecord(
        approval_id="internal-native-smoke-approval",
        project_id=project_id,
        status="approved",
        approved=True,
        approved_by="internal-smoke",
        mappings_reviewed=True,
        output_root=str(output_root),
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
    persisted = persist_conversion_plan(
        project_id=project_id,
        approval_record=approval,
        preflight_snapshot=preflight.model_dump(mode="json"),
        mappings=[mapping.model_dump(mode="json") for mapping in preflight.mappings],
        command_templates=[
            template.model_dump(mode="json") for template in preflight.command_templates
        ],
        safety_flags=preflight.safety_flags.model_dump(mode="json"),
        project_dir=str(project_dir),
        rawdata_dir=str(rawdata_dir),
    )
    assert persisted.ok is True, persisted.errors
    assert persisted.conversion_run_id

    before = build_pre_conversion_rawdata_snapshot([str(rawdata_dir)])
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("the native converter must not launch an external process")
        ),
    )
    result = run_internal_user_dicom_conversion_from_persisted_package(
        project_id=project_id,
        conversion_run_id=persisted.conversion_run_id,
        project_dir=str(project_dir),
        rawdata_dir=str(rawdata_dir),
    )
    after = build_pre_conversion_rawdata_snapshot([str(rawdata_dir)])

    assert result.ok is True, result.errors
    assert result.status == "succeeded"
    assert result.mode == "native"
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
    assert result.manifest_path
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert result.mapping_count == 6
    assert result.command_template_count == 6
    assert result.created_artifact_count == 12
    assert manifest["verified_count"] == 12
    assert manifest["missing_required_count"] == 0
    assert len(list(output_root.rglob("*.nii.gz"))) == 6
    assert len(list(output_root.rglob("*.json"))) == 6


@pytest.mark.skipif(not _all_flags_present(), reason=_REQUIRED_SKIP_FLAGS)
def test_legacy_direct_conversion_endpoint_remains_disabled() -> None:
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )

    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True
    assert result.execution_blocked is True
