from __future__ import annotations

import json
import os
from pathlib import Path

import nibabel as nib
import numpy as np
from fastapi.testclient import TestClient

from src.backend.app.api.dependencies import get_project_store
from src.backend.app.main import app
from src.backend.app.services.mock_store import SQLiteDesktopStore


def _store(tmp_path: Path) -> SQLiteDesktopStore:
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    project = store.get_project("brain-tumor-study")
    assert project is not None
    project.metadata = {
        **(project.metadata or {}),
        "project_dir": str(tmp_path),
        "rawdata_dir": str(tmp_path / "rawdata"),
    }
    store.add_project(
        project, health_status="Review", rawdata_dir=str(tmp_path / "rawdata"), overwrite=True
    )
    return store


def _bold_with_sidecar(tmp_path: Path) -> tuple[Path, Path]:
    func = tmp_path / "converted_bids" / "sub-001" / "func"
    func.mkdir(parents=True)
    data = np.ones((3, 3, 3, 12), dtype=np.float32)
    bold = func / "sub-001_task-rest_bold.nii.gz"
    sidecar = func / "sub-001_task-rest_bold.json"
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(bold))
    sidecar.write_text(
        json.dumps({"RepetitionTime": 2.0, "SliceTiming": [0.0, 0.6, 1.2]}),
        encoding="utf-8",
    )
    return bold, sidecar


def _confirmations() -> dict[str, bool]:
    return {
        "confirm_reviewed_native_execution": True,
        "confirm_rawdata_readonly": True,
        "confirm_no_external_tools": True,
        "confirm_research_use_only": True,
        "confirm_no_clinical_use": True,
    }


def _minimal_stage_overrides() -> dict[str, bool]:
    return {
        "dummy_scan_removal": False,
        "slice_timing": False,
        "realignment": False,
        "motion_qc": False,
        "coregistration": False,
        "segmentation": False,
        "normalization": False,
        "smoothing": False,
        "nuisance_regression": False,
        "detrending": False,
        "temporal_filtering": False,
        "alff": False,
        "falff": False,
        "reho": False,
        "atlas_resampling": False,
        "roi_timeseries": False,
        "functional_connectivity": False,
    }


def test_native_full_dry_run_is_planned_and_does_not_write_artifacts(tmp_path) -> None:
    store = _store(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    bold, sidecar = _bold_with_sidecar(tmp_path)

    try:
        response = client.post(
            "/api/projects/brain-tumor-study/preprocessing/native/full/dry-run",
            json={
                "run_id": "native-dry-run",
                "input_bold": str(bold),
                "sidecar_json": str(sidecar),
                "enable_slice_timing": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is True
    assert payload["status"] in {"planned", "blocked"}
    assert payload["artifact_count"] == 0
    assert payload["safety_flags"]["no_external_tools_executed"] is True
    assert not (tmp_path / "preprocessing_native_runs" / "native-dry-run").exists()


def test_native_full_execute_requires_explicit_safety_confirmations(tmp_path) -> None:
    store = _store(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    bold, sidecar = _bold_with_sidecar(tmp_path)

    try:
        response = client.post(
            "/api/projects/brain-tumor-study/preprocessing/native/full/execute",
            json={
                "run_id": "native-blocked",
                "input_bold": str(bold),
                "sidecar_json": str(sidecar),
            },
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 410
    payload = response.json()["detail"]
    assert payload["error_code"] == "EXECUTION_CONTRACT_REQUIRED"
    assert payload["replacement"] == "/api/plans/execute-reviewed"
    assert not (tmp_path / "preprocessing_native_runs" / "native-blocked").exists()


def test_native_full_get_routes_return_successful_run_validation_and_report(tmp_path) -> None:
    store = _store(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    bold, sidecar = _bold_with_sidecar(tmp_path)
    run_dir = tmp_path / "preprocessing_native_runs" / "native-get-routes"
    run_dir.mkdir(parents=True)
    manifest_path = run_dir / "native_full_run_manifest.json"
    validation_path = run_dir / "native_full_validation_report.json"
    report_path = run_dir / "native_preproc_final_report.json"
    manifest_path.write_text(
        json.dumps(
            {
                "ok": True,
                "status": "succeeded",
                "dry_run": False,
                "project_id": "brain-tumor-study",
                "run_id": "native-get-routes",
                "run_dir": str(run_dir),
                "artifact_count": 1,
                "manifest_path": str(manifest_path),
                "validation_report_path": str(validation_path),
                "final_report_path": str(report_path),
            }
        ),
        encoding="utf-8",
    )

    try:
        execute = client.post(
            "/api/projects/brain-tumor-study/preprocessing/native/full/execute",
            json={
                "run_id": "native-get-routes",
                "input_bold": str(bold),
                "sidecar_json": str(sidecar),
                "stage_overrides": _minimal_stage_overrides(),
                "confirmations": _confirmations(),
            },
        )
        run = client.get(
            "/api/projects/brain-tumor-study/preprocessing/native/runs/native-get-routes"
        )
        validation = client.get(
            "/api/projects/brain-tumor-study/preprocessing/native/runs/native-get-routes/validation"
        )
        report = client.get(
            "/api/projects/brain-tumor-study/preprocessing/native/runs/native-get-routes/report"
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert execute.status_code == 410
    assert execute.json()["detail"]["error_code"] == "EXECUTION_CONTRACT_REQUIRED"
    assert run.status_code == 200
    assert run.json()["run_id"] == "native-get-routes"
    assert run.json()["manifest_path"].endswith("native_full_run_manifest.json")
    assert validation.status_code == 200
    assert validation.json()["run_id"] == "native-get-routes"
    assert "validation_report_path" in validation.json()
    assert report.status_code == 200
    assert report.json()["run_id"] == "native-get-routes"
    assert report.json()["final_report_path"].endswith("native_preproc_final_report.json")


def test_native_full_get_latest_route_returns_newest_manifest(tmp_path) -> None:
    store = _store(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    native_root = tmp_path / "preprocessing_native_runs"

    def write_manifest(run_id: str, artifact_count: int, mtime: float) -> None:
        run_dir = native_root / run_id
        run_dir.mkdir(parents=True)
        manifest = run_dir / "native_full_run_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "ok": True,
                    "status": "succeeded",
                    "dry_run": False,
                    "project_id": "brain-tumor-study",
                    "run_id": run_id,
                    "run_dir": str(run_dir),
                    "artifact_count": artifact_count,
                    "manifest_path": str(manifest),
                }
            ),
            encoding="utf-8",
        )
        os.utime(manifest, (mtime, mtime))

    write_manifest("native-old", 1, 1000)
    write_manifest("native-new", 7, 2000)

    try:
        response = client.get("/api/projects/brain-tumor-study/preprocessing/native/runs/latest")
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "native-new"
    assert payload["artifact_count"] == 7


def test_native_full_get_missing_manifest_returns_blocked_response(tmp_path) -> None:
    store = _store(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)

    try:
        response = client.get(
            "/api/projects/brain-tumor-study/preprocessing/native/runs/missing-native-run"
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["blocking_issues"] == ["Native preprocessing run manifest not found."]


def test_native_full_get_missing_project_returns_404(tmp_path) -> None:
    store = _store(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)

    try:
        response = client.get("/api/projects/missing-project/preprocessing/native/runs/run-1")
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 404


def test_native_full_dry_run_resolves_conversion_registry_inputs(tmp_path) -> None:
    store = _store(tmp_path)
    project = store.get_project("brain-tumor-study")
    assert project is not None
    bold, sidecar = _bold_with_sidecar(tmp_path)
    registry = {
        "conversion_run_id": "conv-native-001",
        "artifacts": [
            {
                "artifact_type": "converted_bold",
                "path": bold.relative_to(tmp_path).as_posix(),
                "path_kind": "project_relative",
            },
            {
                "artifact_type": "sidecar_json",
                "path": sidecar.relative_to(tmp_path).as_posix(),
                "path_kind": "project_relative",
            },
        ],
    }
    registry_path = tmp_path / "preprocessing_input_registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    project.metadata = {
        **(project.metadata or {}),
        "project_dir": str(tmp_path),
        "preprocessing_conversion_run_id": "conv-native-001",
        "preprocessing_input_registry_path": str(registry_path),
    }
    store.add_project(
        project, health_status="Review", rawdata_dir=str(tmp_path / "rawdata"), overwrite=True
    )
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)

    try:
        response = client.post(
            "/api/projects/brain-tumor-study/preprocessing/native/full/dry-run",
            json={
                "run_id": "native-registry-dry-run",
                "conversion_run_id": "conv-native-001",
                "stage_overrides": _minimal_stage_overrides(),
            },
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "planned"
    assert (
        "Resolved native preprocessing BOLD input from conversion artifact registry."
        in payload["warnings"]
    )
    assert (
        "Resolved native preprocessing sidecar input from conversion artifact registry."
        in payload["warnings"]
    )


def test_native_full_dry_run_propagates_registered_bold_to_planned_stages(tmp_path) -> None:
    store = _store(tmp_path)
    project = store.get_project("brain-tumor-study")
    assert project is not None
    bold, sidecar = _bold_with_sidecar(tmp_path)
    anat = tmp_path / "converted_bids" / "sub-001" / "anat"
    anat.mkdir(parents=True)
    t1w = anat / "sub-001_T1w.nii.gz"
    nib.save(nib.Nifti1Image(np.ones((3, 3, 3), dtype=np.float32), affine=np.eye(4)), str(t1w))
    registry = {
        "conversion_run_id": "conv-native-002",
        "artifacts": [
            {
                "artifact_type": "converted_bold",
                "path": bold.relative_to(tmp_path).as_posix(),
                "path_kind": "project_relative",
            },
            {
                "artifact_type": "sidecar_json",
                "path": sidecar.relative_to(tmp_path).as_posix(),
                "path_kind": "project_relative",
            },
            {
                "artifact_type": "converted_t1w",
                "path": t1w.relative_to(tmp_path).as_posix(),
                "path_kind": "project_relative",
            },
        ],
    }
    registry_path = tmp_path / "preprocessing_input_registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    project.metadata = {
        **(project.metadata or {}),
        "project_dir": str(tmp_path),
        "preprocessing_conversion_run_id": "conv-native-002",
        "preprocessing_input_registry_path": str(registry_path),
    }
    store.add_project(
        project, health_status="Review", rawdata_dir=str(tmp_path / "rawdata"), overwrite=True
    )
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)

    try:
        response = client.post(
            "/api/projects/brain-tumor-study/preprocessing/native/full/dry-run",
            json={
                "run_id": "native-registry-propagation-dry-run",
                "conversion_run_id": "conv-native-002",
            },
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 200
    payload = response.json()
    issues = [
        issue for stage in payload["stage_results"] for issue in stage.get("blocking_issues", [])
    ]
    assert "Missing required input: bold_4d" not in issues
    assert "Missing required input: t" not in issues
    assert "Missing required input: 1" not in issues
    assert "Missing required input: w" not in issues
    stages = {stage["stage_id"]: stage for stage in payload["stage_results"]}
    assert stages["realignment"]["status"] == "planned"
    assert stages["segmentation"]["status"] == "planned"
    assert stages["temporal_filtering"]["status"] == "planned"
