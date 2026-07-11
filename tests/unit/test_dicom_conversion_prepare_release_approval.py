from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace


class _Store:
    def __init__(self, project_dir: Path, rawdata_dir: Path) -> None:
        self._project = SimpleNamespace(
            metadata={
                "project_dir": str(project_dir),
                "rawdata_dir": str(rawdata_dir),
            }
        )

    def get_project(self, project_id: str):  # noqa: ANN001
        return self._project if project_id == "project-001" else None


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
    from src.backend.app.schemas.dicom_conversion_prepare import (
        DicomConversionPrepareRequest,
    )
    import src.backend.app.services.dicom_conversion_execution as execution_module
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
        "_detect_dcm2niix_runtime",
        lambda: {
            "found": True,
            "executable_path": "dcm2niix",
            "version": "test-version",
            "sha256": "abc123",
            "strategy": "test",
        },
    )

    response = run_dicom_conversion_prepare(
        _Store(project_dir, rawdata_dir),
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
    assert Path(response.release_approval_decision_path).exists()

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
