"""Tests for DICOM conversion result registration.

No dcm2niix is called. No rawdata is modified.
"""

from __future__ import annotations

from pathlib import Path

from src.backend.app.schemas.desktop import ProjectDetail
from src.backend.app.services.dicom_conversion_result_registration import (
    register_conversion_result,
)


class _FakeStore:
    def __init__(self, project: ProjectDetail) -> None:
        self.project = project
        self.persisted = False

    def get_project(self, project_id: str) -> ProjectDetail | None:
        return self.project if self.project.id == project_id else None

    def add_project(self, project: ProjectDetail, **_kwargs) -> None:
        self.project = project
        self.persisted = True


def _make_project(tmp_path: Path) -> ProjectDetail:
    return ProjectDetail(
        id="proj-1",
        name="DICOM Result Registration",
        study_id="study-1",
        modality="rs-fMRI",
        created_date="2026-06-27",
        subjects_count=0,
        current_pipeline_id="dicom-to-nifti",
        sequences=["BOLD", "T1w"],
        scans_count=0,
        total_size="0 MB",
        current_model_id="dcm2niix",
        metadata={
            "project_dir": str(tmp_path / "project"),
            "rawdata_dir": str(tmp_path / "rawdata"),
        },
    )


def test_register_conversion_result_updates_project_closure_metadata(tmp_path):
    project = _make_project(tmp_path)
    store = _FakeStore(project)
    output_root = tmp_path / "project" / "converted_bids"
    func_dir = output_root / "sub-001" / "func"
    anat_dir = output_root / "sub-001" / "anat"
    func_dir.mkdir(parents=True)
    anat_dir.mkdir(parents=True)
    (func_dir / "sub-001_task-rest_bold.nii.gz").write_bytes(b"FAKE_NIFTI")
    (func_dir / "sub-001_task-rest_bold.json").write_text("{}", encoding="utf-8")
    (anat_dir / "sub-001_T1w.nii.gz").write_bytes(b"FAKE_NIFTI")
    (anat_dir / "sub-001_T1w.json").write_text("{}", encoding="utf-8")
    manifest_path = tmp_path / "project" / "conversion_runs" / "conv-1" / "output_manifest.json"
    provenance_path = tmp_path / "project" / "conversion_runs" / "conv-1" / "execution_provenance.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}", encoding="utf-8")
    provenance_path.write_text("{}", encoding="utf-8")

    result = register_conversion_result(
        store,
        "proj-1",
        conversion_run_id="conv-1",
        output_root=str(output_root),
        execution_status="succeeded",
        manifest_path=str(manifest_path),
        provenance_path=str(provenance_path),
        checksum_verified=True,
    )

    metadata = store.project.metadata
    assert result["ok"] is True
    assert result["nifti_count"] == 2
    assert result["subject_count"] == 1
    assert result["dashboard_refresh_required"] is True
    assert result["viewer_refresh_required"] is True
    assert store.persisted is True
    assert metadata["converted_bids_available"] is True
    assert metadata["converted_bids_dir"] == str(output_root)
    assert metadata["last_conversion_manifest_path"] == str(manifest_path)
    assert metadata["last_conversion_provenance_path"] == str(provenance_path)
    assert Path(metadata["preprocessing_input_registry_path"]).exists()
    assert result["preprocessing_input_registry_path"] == metadata["preprocessing_input_registry_path"]
    assert metadata["native_full_preproc_handoff"] == {
        "conversion_run_id": "conv-1",
        "artifact_registry_path": metadata["preprocessing_input_registry_path"],
        "input_resolution": "preprocessing_input_registry_path",
        "status": "ready",
    }
    assert result["native_full_preproc_handoff"] == metadata["native_full_preproc_handoff"]
    assert metadata["recent_activity"][0]["kind"] == "dicom_conversion"
    assert metadata["recent_activity"][0]["conversion_run_id"] == "conv-1"
    artifact_paths = {item["path"] for item in metadata["results_artifacts"]}
    assert str(manifest_path) in artifact_paths
    assert str(provenance_path) in artifact_paths
    assert metadata["preprocessing_input_source"] == "converted_bids"
