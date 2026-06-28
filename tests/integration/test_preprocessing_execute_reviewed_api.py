from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np
from fastapi.testclient import TestClient

from src.backend.app.api.dependencies import get_project_store
from src.backend.app.main import app
from src.backend.app.services.mock_store import SQLiteDesktopStore
from src.backend.app.services.preprocessing_artifact_registry import append_stage_output_artifacts, load_artifact_registry


def _make_converted_bids(root: Path, tr: float) -> Path:
    bids = root / "converted_bids"
    func = bids / "sub-001" / "func"
    anat = bids / "sub-001" / "anat"
    func.mkdir(parents=True)
    anat.mkdir(parents=True)
    nib.save(
        nib.Nifti1Image(np.zeros((3, 3, 3, 8), dtype=np.float32), affine=np.eye(4)),
        str(func / "sub-001_task-rest_bold.nii.gz"),
    )
    (func / "sub-001_task-rest_bold.json").write_text(
        json.dumps({"RepetitionTime": tr, "TaskName": "rest"}),
        encoding="utf-8",
    )
    nib.save(
        nib.Nifti1Image(np.zeros((3, 3, 3), dtype=np.float32), affine=np.eye(4)),
        str(anat / "sub-001_T1w.nii.gz"),
    )
    return bids


def _configured_store(tmp_path: Path, monkeypatch) -> SQLiteDesktopStore:
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    project = store.get_project("brain-tumor-study")
    assert project is not None
    project.metadata = {
        **(project.metadata or {}),
        "project_dir": str(tmp_path),
        "rawdata_dir": str(tmp_path / "rawdata"),
    }
    store.add_project(project, health_status="Review", rawdata_dir=str(tmp_path / "rawdata"), overwrite=True)
    for module in (
        "src.backend.app.services.preprocessing_pipeline_report",
        "src.backend.app.services.preprocessing_pipeline_validation",
    ):
        monkeypatch.setattr(f"{module}.mock_store", store)
    return store


def test_execute_reviewed_api_runs_registered_minimal_fc_chain(tmp_path, monkeypatch):
    store = _configured_store(tmp_path, monkeypatch)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    tr = 2.0
    bids = _make_converted_bids(tmp_path, tr)

    try:
        create = client.post(
            "/api/projects/brain-tumor-study/preprocessing/runs",
            json={
                "preprocessing_input_dir": str(bids),
                "confirm_use_converted_input": True,
                "confirm_no_rawdata_modification": True,
                "confirm_python_only_execution": True,
                "confirm_no_spm_matlab": True,
            },
        )
        assert create.status_code == 200
        created = create.json()
        assert created["ok"] is True
        run_id = created["preprocessing_run_id"]
        registry_path = Path(created["artifact_registry_path"])

        derivatives = tmp_path / "derivatives"
        func_dir = derivatives / "rsfmri_preproc" / "sub-001" / "func"
        qc_dir = derivatives / "rsfmri_qc" / "sub-001"
        func_dir.mkdir(parents=True)
        qc_dir.mkdir(parents=True)
        n_time = 36
        time = np.arange(n_time, dtype=np.float32) * tr
        data = np.zeros((4, 4, 3, n_time), dtype=np.float32)
        data[:2, :, :, :] = np.sin(2 * np.pi * 0.03 * time)
        data[2:, :, :, :] = np.cos(2 * np.pi * 0.03 * time)
        realigned = func_dir / "rsub-001_task-rest_bold.nii.gz"
        nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(realigned))
        (func_dir / "sub-001_task-rest_bold.json").write_text(
            json.dumps({"RepetitionTime": tr, "TaskName": "rest"}),
            encoding="utf-8",
        )
        motion = func_dir / "rp_sub-001_task-rest_bold.txt"
        motion.write_text("\n".join(["0 0 0 0 0 0"] * n_time) + "\n", encoding="utf-8")
        fd = qc_dir / "fd_timeseries.tsv"
        fd.write_text("frame\tframewise_displacement\n0\t0.0\n", encoding="utf-8")
        append_stage_output_artifacts(
            registry_path=registry_path,
            project_id="brain-tumor-study",
            preprocessing_run_id=run_id,
            stage_id="realignment",
            output_paths_by_type={
                "realigned_bold": [realigned],
                "motion_parameters": [motion],
                "fd_timeseries": [fd],
            },
            project_dir=str(tmp_path),
            source_execution_id="reviewed-spm-existing",
            backend="spm12",
        )

        atlas = np.zeros((4, 4, 3), dtype=np.int16)
        atlas[:2, :, :] = 1
        atlas[2:, :, :] = 2
        atlas_path = derivatives / "atlases" / "sub-001_space-native_atlas.nii.gz"
        atlas_path.parent.mkdir(parents=True)
        nib.save(nib.Nifti1Image(atlas, affine=np.eye(4)), str(atlas_path))
        labels_path = derivatives / "atlases" / "sub-001_space-native_labels.tsv"
        labels_path.write_text("label\tname\n1\tSinROI\n2\tCosROI\n", encoding="utf-8")

        response = client.post(
            f"/api/projects/brain-tumor-study/preprocessing/runs/{run_id}/execute-reviewed",
            json={
                "pipeline_profile": "custom",
                "stages": {
                    "nuisance_regression": "enabled",
                    "temporal_filtering": "enabled",
                    "functional_connectivity": "enabled",
                },
                "atlas": {
                    "atlas_path": str(atlas_path),
                    "labels_path": str(labels_path),
                    "atlas_space": "native_or_matched",
                    "allow_resample": False,
                },
                "filtering": {"low_hz": 0.01, "high_hz": 0.08, "fallback_tr": tr},
                "confirmations": {
                    "confirm_rawdata_readonly": True,
                    "confirm_reviewed_execution": True,
                    "confirm_external_tools_if_needed": True,
                    "confirm_research_use_only": True,
                    "confirm_no_clinical_use": True,
                },
                "generate_report": True,
                "run_validation": True,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "succeeded", payload
        assert {"nuisance_regression", "temporal_filtering", "functional_connectivity"} <= set(payload["completed_stages"])
        fc = next(item for item in payload["stage_results"] if item["stage_id"] == "functional_connectivity")
        assert fc["status"] == "succeeded"
        assert fc["output_artifact_ids"]
        assert payload["validation_status"] in {"ready_for_review", "warning"}

        registry = load_artifact_registry(registry_path)
        artifact_types = {item["artifact_type"] for item in registry["artifacts"]}
        assert {"denoised_bold", "filtered_bold", "roi_timeseries", "fc_matrix", "fisher_z_matrix", "roi_labels"} <= artifact_types
        fc_matrix = next(item for item in registry["artifacts"] if item["artifact_type"] == "fc_matrix")
        artifact_metadata = client.get(
            f"/api/projects/brain-tumor-study/preprocessing/runs/{run_id}/artifacts/{fc_matrix['artifact_id']}"
        )
        assert artifact_metadata.status_code == 200
        assert artifact_metadata.json()["artifact"]["artifact_type"] == "fc_matrix"
        artifact_file = client.get(
            f"/api/projects/brain-tumor-study/preprocessing/runs/{run_id}/artifacts/{fc_matrix['artifact_id']}/file"
        )
        assert artifact_file.status_code == 200
        assert artifact_file.content
    finally:
        app.dependency_overrides.pop(get_project_store, None)
