from __future__ import annotations

import asyncio
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.schemas.desktop import PipelineRunRequest, TaskDetail
from src.backend.app.services.mock_store import SQLiteDesktopStore, mock_store, utc_now_iso
from src.backend.app.services.pipeline_runner import run_external_smoke_package
from src.backend.app.services.task_manager import task_manager


def test_desktop_dashboard_health_and_projects():
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "medimage-agent-backend",
        "version": "0.1.0",
    }

    projects = client.get("/api/projects")
    assert projects.status_code == 200
    payload = projects.json()
    assert payload
    assert payload[0]["id"] == "brain-tumor-study"


def test_desktop_dashboard_cards_and_tasks():
    client = TestClient(app)
    project = client.get("/api/projects/brain-tumor-study").json()

    overview = client.get(f"/api/studies/{project['study_id']}/overview")
    assert overview.status_code == 200
    assert overview.json()["study_name"] == "Brain Tumor Study"

    dataset = client.get("/api/datasets/summary", params={"project_id": project["id"]})
    assert dataset.status_code == 200
    assert dataset.json()["subjects"] == 128

    model = client.get("/api/models/status", params={"project_id": project["id"]})
    assert model.status_code == 200
    assert model.json()["model_name"] == "UNet 3D"

    tasks = client.get("/api/tasks")
    assert tasks.status_code == 200
    assert any(task["status"] == "running" for task in tasks.json())


def test_dataset_import_and_pipeline_run_create_task(tmp_path):
    client = TestClient(app)
    import nibabel as nib
    import numpy as np

    import_root = tmp_path / "imported_bids"
    anat_dir = import_root / "sub-import" / "anat"
    anat_dir.mkdir(parents=True)
    nifti_path = anat_dir / "sub-import_T1w.nii.gz"
    data = np.arange(4 * 5 * 6, dtype=np.float32).reshape((4, 5, 6))
    nib.Nifti1Image(data, affine=np.diag([2.0, 2.0, 2.5, 1.0])).to_filename(str(nifti_path))

    imported = client.post(
        "/api/datasets/import",
        json={"project_id": "brain-tumor-study", "path": str(import_root), "type": "bids"},
    )
    assert imported.status_code == 200
    assert imported.json()["success"] is True
    assert imported.json()["image_source_count"] >= 1
    assert Path(imported.json()["manifest_path"]).exists()
    assert imported.json()["validation_issue_count"] >= 1
    assert Path(imported.json()["validation_report_path"]).exists()
    assert imported.json()["validation_report_text"].startswith("# Image Validation Report")

    imports = client.get("/api/datasets/imports", params={"project_id": "brain-tumor-study"})
    assert imports.status_code == 200
    import_payload = imports.json()
    assert import_payload["ok"] is True
    assert any(item["path"] == str(import_root) and item["exists"] is True for item in import_payload["imports"])

    package = client.post("/api/datasets/diagnostics/package", params={"project_id": "brain-tumor-study"})
    assert package.status_code == 200
    package_payload = package.json()
    assert Path(package_payload["report_path"]).exists()
    assert Path(package_payload["json_path"]).exists()
    assert Path(package_payload["zip_path"]).exists()
    assert Path(package_payload["checksum_path"]).exists()
    assert package_payload["report_text"].startswith("# Import Diagnostics Package")
    assert package_payload["import_count"] >= 1
    assert package_payload["file_inventory"]["total_files"] >= 1
    assert package_payload["safety_flags"]["rawdata_not_bundled"] is True
    assert package_payload["safety_flags"]["read_only_validation"] is True
    assert "import_diagnostics_package.md" in package_payload["checksums"]
    with zipfile.ZipFile(package_payload["zip_path"]) as archive:
        names = set(archive.namelist())
    assert not any(name.lower().endswith((".nii", ".nii.gz", ".dcm", ".ima")) for name in names)
    assert "import_diagnostics_package.md" in names
    assert "import_diagnostics_package.json" in names
    assert "CHECKSUMS.sha256" in names
    assert "artifacts/image_source_manifest.json" in names
    assert "artifacts/image_validation_report.md" in names

    latest_package = client.get("/api/datasets/diagnostics/package/latest", params={"project_id": "brain-tumor-study"})
    assert latest_package.status_code == 200
    latest_payload = latest_package.json()
    assert latest_payload["ok"] is True
    assert latest_payload["latest"]["zip_path"] == package_payload["zip_path"]
    assert latest_payload["latest"]["checksums"] == package_payload["checksums"]
    assert latest_payload["latest"]["safety_flags"]["rawdata_not_bundled"] is True
    assert latest_payload["latest"]["report_text"].startswith("# Import Diagnostics Package")

    verify_package = client.post("/api/datasets/diagnostics/package/verify", params={"project_id": "brain-tumor-study"})
    assert verify_package.status_code == 200
    verify_payload = verify_package.json()
    assert verify_payload["ok"] is True
    assert verify_payload["checked_files"] == len(package_payload["checksums"])
    assert verify_payload["passed_files"] == verify_payload["checked_files"]
    assert verify_payload["failed_files"] == []
    assert verify_payload["missing_files"] == []

    sources = client.get("/api/images/sources", params={"project_id": "brain-tumor-study"})
    assert sources.status_code == 200
    source_payload = sources.json()
    imported_source = next(item for item in source_payload["manifest"] if item["subject_id"] == "sub-import")
    assert imported_source["sequence"] == "T1"
    assert imported_source["dimensions"] == [4, 5, 6]
    assert imported_source["plane_slice_counts"]["axial"] == 6

    preview = client.get(
        "/api/images/preview",
        params={"project_id": "brain-tumor-study", "subject_id": "sub-import", "sequence": "T1", "plane": "axial"},
    )
    assert preview.status_code == 200
    assert preview.json()["source"] == "nifti"
    assert preview.json()["source_path"].endswith("sub-import_T1w.nii.gz")

    validation = client.get("/api/images/validation", params={"project_id": "brain-tumor-study"})
    assert validation.status_code == 200
    validation_payload = validation.json()
    assert validation_payload["source_count"] >= imported.json()["image_source_count"]
    assert validation_payload["status"] in {"pass", "warning", "fail"}
    assert Path(validation_payload["report_path"]).exists()
    assert Path(validation_payload["json_path"]).exists()
    assert validation_payload["report_text"].startswith("# Image Validation Report")
    assert any(issue["code"] == "missing_expected_sequence" for issue in validation_payload["issues"])

    run = client.post(
        "/api/pipelines/run",
        json={
            "project_id": "brain-tumor-study",
            "pipeline_id": "brain-tumor-segmentation",
            "model_id": "unet3d-v2.1",
            "input_sequences": ["T1", "T2", "FLAIR", "T1ce"],
            "output_type": "segmentation_metrics",
            "execution_mode": "external_smoke",
        },
    )
    assert run.status_code == 200
    task_id = run.json()["task_id"]
    detail = client.get(f"/api/tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "running"
    assert detail.json()["execution_mode"] == "external_smoke"

    events = client.get(f"/api/tasks/{task_id}/events")
    assert events.status_code == 200
    assert events.json()[0]["message"] == "Pipeline request accepted"


def test_dicom_preflight_api_reads_demodata_metadata_only():
    pytest.importorskip("pydicom")
    demo_data = Path("data/DemoData")
    if not demo_data.exists():
        pytest.skip("DemoData is not available in this checkout.")

    client = TestClient(app)
    response = client.get(
        "/api/datasets/dicom/preflight",
        params={"project_id": "brain-tumor-study", "path": str(demo_data), "max_files": 8},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["dicom_file_count"] >= 1
    assert payload["sampled_file_count"] == 8
    assert payload["series_count"] >= 1
    assert payload["safety_flags"]["read_only"] is True
    assert payload["safety_flags"]["stop_before_pixels"] is True
    assert payload["safety_flags"]["rawdata_not_bundled"] is True
    assert payload["safety_flags"]["dicom_uids_hashed"] is True
    assert payload["safety_flags"]["sample_paths_relative"] is True
    assert all(str(item["series_instance_uid"]).startswith("sha256:") for item in payload["series"])
    assert "1.3.12.2" not in json.dumps(payload["series"])
    assert all(not Path(item["sample_file"]).is_absolute() for item in payload["series"] if item.get("sample_file"))
    assert payload["report_text"].startswith("# DICOM Metadata Preflight")
    assert Path(payload["report_path"]).exists()
    assert Path(payload["json_path"]).exists()
    assert not any("PixelData" in item for item in payload["report_text"].splitlines())

    imported = client.post(
        "/api/datasets/import",
        json={"project_id": "brain-tumor-study", "path": str(demo_data), "type": "dicom"},
    )
    assert imported.status_code == 200


def test_real_data_inspect_api_reads_demodata_inventory():
    pytest.importorskip("pydicom")
    demo_data = Path("data/DemoData")
    if not demo_data.exists():
        pytest.skip("DemoData is not available in this checkout.")

    client = TestClient(app)
    response = client.post(
        "/api/real-data/inspect",
        json={
            "root_dir": str(demo_data),
            "report_dir": "outputs/reports",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["mode"] == "readonly_sandbox"
    assert payload["format"] == "DICOM"
    assert payload["completeness"]["subjects_total"] == 3
    assert payload["completeness"]["has_t1w"] == 3
    assert payload["completeness"]["has_bold"] == 3
    assert Path("outputs/reports/real_data_sandbox/data_inventory.json").exists()

    risk = client.post("/api/real-data/risk-report")
    recommendation = client.post("/api/real-data/protocol-recommend")
    assert risk.status_code == 200
    assert recommendation.status_code == 200
    assert risk.json()["ok"] is True
    assert recommendation.json()["ok"] is True
    assert Path("outputs/reports/real_data_sandbox/risk_report.json").exists()
    assert Path("outputs/reports/real_data_sandbox/protocol_recommendation.json").exists()

    package = client.post("/api/datasets/diagnostics/package", params={"project_id": "brain-tumor-study"})
    assert package.status_code == 200
    package_payload = package.json()
    assert package_payload["dicom_file_count"] >= 1
    assert package_payload["dicom_series_count"] >= 1
    assert Path(package_payload["dicom_preflight_report_path"]).exists()
    assert Path(package_payload["dicom_preflight_json_path"]).exists()
    assert "DICOM Metadata Preflight" in package_payload["report_text"]
    with zipfile.ZipFile(package_payload["zip_path"]) as archive:
        names = set(archive.namelist())
    assert "artifacts/dicom_preflight_report.md" in names
    assert "artifacts/dicom_preflight_result.json" in names
    assert not any(name.lower().endswith((".dcm", ".ima")) for name in names)


def test_assistant_image_preview_and_task_websocket():
    client = TestClient(app)
    assistant = client.post(
        "/api/assistant/chat",
        json={"project_id": "brain-tumor-study", "message": "What pipeline should I run?"},
    )
    assert assistant.status_code == 200
    assert "pipeline" in assistant.json()["reply"].lower()

    preview = client.get(
        "/api/images/preview",
        params={"project_id": "brain-tumor-study", "subject_id": "sub-001", "sequence": "T1"},
    )
    assert preview.status_code == 200
    assert preview.json()["source"] in {"nifti", "fallback"}
    if preview.json()["source"] == "nifti":
        assert preview.json()["preview_url"].startswith("data:image/svg+xml;base64,")
        assert preview.json()["slice_count"] >= 1

    with client.websocket_connect("/ws/tasks/task-001") as websocket:
        message = websocket.receive_json()
        assert message["task_id"] == "task-001"
        assert message["status"] == "running"


def test_sqlite_desktop_store_persists_task_events(tmp_path):
    db_path = tmp_path / "desktop_state.sqlite"
    store = SQLiteDesktopStore(db_path)
    assert store.health_check()["ok"] is True
    assert store.get_project("brain-tumor-study") is not None

    task = TaskDetail(
        id="task-persisted",
        run_name="Run_test",
        pipeline="Persisted Pipeline",
        dataset="Brain Tumor Study",
        status="running",
        progress=1,
        started_at="10:00",
        duration="00:00:00",
        owner="Dr. Alex Morgan",
        logs=["created"],
        result_path=None,
        execution_mode="simulated",
        project_id="brain-tumor-study",
        pipeline_id="persisted-pipeline",
        model_id="mock-model",
        input_sequences=["T1"],
        output_type="diagnostics",
        updated_at=utc_now_iso(),
    )
    store.add_task(task)
    store.append_task_event(
        "task-persisted",
        status="running",
        progress=10,
        message="persisted event",
    )

    reopened = SQLiteDesktopStore(db_path)
    assert reopened.get_task("task-persisted") is not None
    assert reopened.list_task_events("task-persisted")[-1].message == "persisted event"


def test_desktop_health_includes_runtime_and_store_checks():
    client = TestClient(app)
    health = client.get("/api/desktop/health")
    assert health.status_code == 200
    check_names = {item["name"] for item in health.json()["checks"]}
    assert {"websocket_runtime", "desktop_store", "pipeline_adapters"}.issubset(check_names)


def test_approved_smoke_requires_explicit_approval():
    client = TestClient(app)
    blocked = client.post(
        "/api/pipelines/run",
        json={
            "project_id": "brain-tumor-study",
            "pipeline_id": "external-smoke",
            "model_id": "matlab-runner",
            "input_sequences": ["T1", "BOLD"],
            "output_type": "diagnostics",
            "execution_mode": "external_smoke",
            "external_smoke_mode": "approved_smoke",
            "approved": False,
        },
    )
    assert blocked.status_code == 403

    missing_name = client.post(
        "/api/pipelines/run",
        json={
            "project_id": "brain-tumor-study",
            "pipeline_id": "external-smoke",
            "model_id": "matlab-runner",
            "input_sequences": ["T1", "BOLD"],
            "output_type": "diagnostics",
            "execution_mode": "external_smoke",
            "external_smoke_mode": "approved_smoke",
            "approved": True,
            "approved_by": "",
        },
    )
    assert missing_name.status_code == 400


def test_task_approval_records_event_and_diagnostics(monkeypatch):
    async def fake_run_pipeline_task(task_id, request, manager):
        await manager.update_task(
            task_id,
            status="running",
            progress=12,
            message="fake approved smoke queued",
            source="external_smoke",
        )

    monkeypatch.setattr("src.backend.app.api.dashboard_routes.run_pipeline_task", fake_run_pipeline_task)
    client = TestClient(app)
    created = client.post(
        "/api/pipelines/run",
        json={
            "project_id": "brain-tumor-study",
            "pipeline_id": "external-smoke",
            "model_id": "matlab-runner",
            "input_sequences": ["T1", "BOLD"],
            "output_type": "diagnostics",
            "execution_mode": "external_smoke",
        },
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    approval = client.post(
        f"/api/tasks/{task_id}/approve",
        json={"approved": True, "approved_by": "QA Lead"},
    )
    assert approval.status_code == 200
    assert approval.json()["approval"]["approved_by"] == "QA Lead"

    diagnostics = client.get(f"/api/tasks/{task_id}/diagnostics")
    assert diagnostics.status_code == 200
    assert diagnostics.json()["approval"]["approved_by"] == "QA Lead"


def test_fake_external_smoke_artifacts_and_diagnostics(monkeypatch):
    def fake_external_smoke(request: PipelineRunRequest) -> dict:
        return {
            "ok": True,
            "target": "all",
            "mode": request.external_smoke_mode,
            "checks": [],
            "external_tool_results": [
                {
                    "command": ["matlab", "-batch", "spm_jobman initcfg"],
                    "returncode": 0,
                    "logs": {"stdout": "ok", "stderr": ""},
                    "outputs": {"result_json": "outputs/reports/external_smoke/fake_result.json"},
                }
            ],
            "artifacts": {"result_json": "outputs/reports/external_smoke/fake_result.json"},
            "warnings": [],
            "errors": [],
            "next_actions": [],
        }

    monkeypatch.setattr("src.backend.app.services.pipeline_runner._run_external_smoke", fake_external_smoke)
    request = PipelineRunRequest(
        project_id="brain-tumor-study",
        pipeline_id="external-smoke",
        model_id="matlab-runner",
        input_sequences=["T1", "BOLD"],
        output_type="diagnostics",
        execution_mode="external_smoke",
        external_smoke_mode="approved_smoke",
        approved=True,
        approved_by="QA Lead",
    )
    task = task_manager.create_pipeline_task(request)
    mock_store.add_approval(task.id, approved=True, approved_by="QA Lead")
    asyncio.run(run_external_smoke_package(task.id, request, task_manager))

    client = TestClient(app)
    detail = client.get(f"/api/tasks/{task.id}")
    assert detail.json()["status"] == "completed"

    artifacts = client.get(f"/api/tasks/{task.id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json()["artifacts"]["result_json"].endswith("fake_result.json")

    diagnostics = client.get(f"/api/tasks/{task.id}/diagnostics")
    assert diagnostics.status_code == 200
    assert diagnostics.json()["external_tool_results"][0]["returncode"] == 0


def test_task_audit_package_generates_markdown_and_json():
    client = TestClient(app)
    package = client.post("/api/tasks/task-001/audit-package")
    assert package.status_code == 200
    payload = package.json()
    assert payload["ok"] is True
    assert payload["task_id"] == "task-001"
    assert payload["report_path"].endswith("task_audit_report.md")
    assert payload["json_path"].endswith("task_audit_package.json")
    assert "Task Audit Package: task-001" in payload["report_text"]
    assert "Safety Boundaries" in payload["report_text"]

    report_path = payload["report_path"]
    json_path = payload["json_path"]
    assert client.get("/api/tasks/task-001/artifacts").status_code == 200
    assert Path(report_path).exists()
    assert Path(json_path).exists()


def test_image_preview_uses_nifti_when_available():
    client = TestClient(app)
    preview = client.get(
        "/api/images/preview",
        params={
            "project_id": "brain-tumor-study",
            "subject_id": "sub-001",
            "sequence": "BOLD",
            "slice_index": 1,
            "plane": "sagittal",
        },
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["source"] == "nifti"
    assert payload["preview_url"].startswith("data:image/svg+xml;base64,")
    assert payload["source_path"].endswith(".nii.gz")
    assert payload["plane"] == "sagittal"
    assert payload["slice_index"] == 1
    assert payload["dimensions"]

    sources = client.get("/api/images/sources", params={"project_id": "brain-tumor-study"})
    assert sources.status_code == 200
    source_payload = sources.json()
    assert "sub-001" in {item["subject_id"] for item in source_payload["subjects"]}
    assert {"T1", "BOLD"}.issubset(set(source_payload["sequences"]))
    assert source_payload["manifest"]
    assert source_payload["manifest_path"]
    assert Path(source_payload["manifest_path"]).exists()
    bold_manifest = next(item for item in source_payload["manifest"] if item["subject_id"] == "sub-001" and item["sequence"] == "BOLD")
    assert bold_manifest["dimensions"]
    assert bold_manifest["voxel_spacing"]
    assert bold_manifest["plane_slice_counts"]["sagittal"] >= 1
    assert bold_manifest["relative_path"].endswith(".nii.gz")

    manifest = client.get("/api/images/manifest", params={"project_id": "brain-tumor-study"})
    assert manifest.status_code == 200
    assert manifest.json()["manifest_path"] == source_payload["manifest_path"]

    validation = client.get("/api/images/validation", params={"project_id": "brain-tumor-study"})
    assert validation.status_code == 200
    validation_payload = validation.json()
    assert validation_payload["source_count"] >= len(source_payload["manifest"])
    assert validation_payload["manifest_path"] == source_payload["manifest_path"]
    assert validation_payload["report_path"].endswith("image_validation_report.md")
