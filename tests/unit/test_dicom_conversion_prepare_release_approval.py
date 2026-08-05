from __future__ import annotations

import json
from pathlib import Path

from src.backend.app.schemas.desktop import ProjectDetail
from src.backend.app.services.mock_store import SQLiteDesktopStore


class _Store:
    def __init__(self, project_dir: Path, rawdata_dir: Path) -> None:
        self._project = ProjectDetail(
            id="project-001",
            name="DICOM project",
            study_id="study-001",
            modality="rs-fMRI",
            created_date="2026-07-16",
            subjects_count=1,
            current_pipeline_id="",
            sequences=[],
            scans_count=1,
            total_size="1 MB",
            current_model_id="",
            metadata={
                "project_dir": str(project_dir),
                "rawdata_dir": str(rawdata_dir),
            },
        )

    def get_project(self, project_id: str):  # noqa: ANN001
        return self._project if project_id == "project-001" else None

    def update_project_metadata(self, project_id, updates):  # noqa: ANN001
        if project_id != self._project.id:
            return None
        metadata = {**self._project.metadata, **updates}
        self._project = self._project.model_copy(update={"metadata": metadata})
        return self._project


def _all_confirmations():
    from src.backend.app.schemas.dicom_conversion_prepare import (
        DicomConversionPrepareConfirmations,
    )

    return DicomConversionPrepareConfirmations(
        mappings_reviewed=True,
        rawdata_readonly=True,
        research_use_only=True,
        no_clinical_use=True,
        external_converter=True,
        rollback_policy=True,
        risk_acknowledgement=True,
        approval_audit=True,
        public_endpoint=True,
        frontend_execute=True,
        spm_dpabi_matlab_disabled=True,
        confirm_execution=True,
    )


def _fake_preflight(project_dir: Path, rawdata_dir: Path):
    from src.backend.app.schemas.dicom_conversion_execution import (
        Dcm2niixCommandTemplate,
        DicomConversionMapping,
        DicomConversionPreflight,
        DicomConversionSafetyFlags,
    )

    output_root = project_dir / "converted_bids"
    source_dir = rawdata_dir / "sub-001" / "func"
    output_dir = output_root / "sub-001" / "func"
    return DicomConversionPreflight(
        ok=True,
        status="ready",
        mode="preflight",
        conversion_disabled_by_default=False,
        tool_available=True,
        executable_path="dcm2niix",
        tool_version="test-version",
        env_enabled=True,
        missing_env_flags=[],
        output_dir_safe=True,
        output_root_preview=str(output_root),
        rawdata_readonly=True,
        mapping_count=1,
        mappings=[
            DicomConversionMapping(
                source_path=str(source_dir),
                source_type="dicom_series",
                subject_id="sub-001",
                modality="func",
                suffix="bold",
                suggested_relative_path="sub-001/func/sub-001_task-rest_bold.nii.gz",
                output_dir=str(output_dir),
                output_filename="sub-001_task-rest_bold.nii.gz",
                confidence="high",
            )
        ],
        command_templates=[
            Dcm2niixCommandTemplate(
                executable="dcm2niix",
                input_dir=str(source_dir),
                output_dir=str(output_dir),
                filename_pattern="sub-001_task-rest_bold",
                command_preview="dcm2niix -o output input",
            )
        ],
        safety_flags=DicomConversionSafetyFlags(
            conversion_disabled_by_default=False,
            env_flags_missing=False,
        ),
    )


def test_prepare_persists_release_approval_decision_for_execute_gate(tmp_path, monkeypatch):
    import src.backend.app.services.dicom_conversion_execution as execution_module
    from src.backend.app.schemas.dicom_conversion_prepare import (
        DicomConversionPrepareRequest,
    )
    from src.backend.app.services.dicom_conversion_prepare import (
        run_dicom_conversion_prepare,
    )
    from src.backend.app.services.dicom_conversion_release_approval import (
        read_release_approval,
    )

    project_dir = tmp_path / "project"
    rawdata_dir = tmp_path / "rawdata"
    series_dir = rawdata_dir / "sub-001" / "func"
    series_dir.mkdir(parents=True)
    (series_dir / "image-001.dcm").write_bytes(b"dicom-fixture")
    project_dir.mkdir()

    for key in (
        "MEDIMAGE_FRONTEND_DICOM_EXECUTE_UI_ENABLED",
        "MEDIMAGE_DICOM_EXECUTE_UI_ENABLED",
        "VITE_ENABLE_DICOM_EXECUTE_UI",
        "MEDIMAGE_MATLAB_ENABLED",
        "MEDIMAGE_SPM_SMOKE_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(
        execution_module,
        "run_conversion_preflight",
        lambda project_id, request: _fake_preflight(project_dir, rawdata_dir),
    )
    monkeypatch.setattr(
        execution_module,
        "check_native_dicom_converter_availability",
        lambda: {
            "found": True,
            "backend": "medimage-native",
            "version": "test-native-version",
            "versions": {
                "numpy": "test",
                "nibabel": "test",
                "pydicom": "test",
            },
            "error": None,
        },
    )

    store = _Store(project_dir, rawdata_dir)
    response = run_dicom_conversion_prepare(
        store,
        "project-001",
        DicomConversionPrepareRequest(
            approved_by="operator",
            selected_mapping_ids=["sub-001-func"],
            overwrite_policy="fail_if_exists",
            confirmations=_all_confirmations(),
        ),
    )

    assert response.status == "ready"
    assert response.execution_ready is True
    assert response.release_approval_id.startswith("release-approval-")
    assert response.release_approval_decision_path
    assert (
        store.get_project("project-001").metadata["agent_conversion_run_id"]
        == response.conversion_run_id
    )
    assert store.get_project("project-001").metadata["agent_conversion_execution_ready"] is True
    assert Path(response.release_approval_decision_path).exists()
    run_dirs = list((project_dir / "conversion_runs").iterdir())
    assert [path.name for path in run_dirs] == [response.conversion_run_id]
    checksum = json.loads(
        (run_dirs[0] / "rawdata_checksum_before.json").read_text(encoding="utf-8")
    )
    assert checksum["file_count"] == 1
    assert checksum["fingerprint"]

    decision = json.loads(Path(response.release_approval_decision_path).read_text())
    assert decision["approved"] is True
    assert decision["blocked"] is False

    read_back = read_release_approval(
        project_id="project-001",
        conversion_run_id=response.conversion_run_id,
        project_dir=str(project_dir),
    )
    assert read_back.approved is True
    assert read_back.blocked is False


def test_atomic_metadata_merge_preserves_dataset_health(tmp_path: Path) -> None:
    store = SQLiteDesktopStore(tmp_path / "desktop.db")
    project = ProjectDetail(
        id="project-health",
        name="Health-preserving metadata merge",
        study_id="study-health",
        modality="rs-fMRI",
        created_date="2026-07-16",
        subjects_count=1,
        current_pipeline_id="",
        sequences=[],
        scans_count=1,
        total_size="1 MB",
        current_model_id="",
        metadata={"project_dir": str(tmp_path / "project")},
    )
    store.add_project(
        project,
        health_status="Ready",
        rawdata_dir=str(tmp_path / "rawdata"),
    )

    updated = store.update_project_metadata(
        project.id,
        {
            "agent_conversion_run_id": "conversion-001",
            "agent_conversion_execution_ready": True,
        },
    )

    assert updated is not None
    assert updated.metadata["agent_conversion_run_id"] == "conversion-001"
    assert store.get_project(project.id).metadata["agent_conversion_execution_ready"] is True
    assert store.get_dataset_summary(project.id).health_status == "Ready"
