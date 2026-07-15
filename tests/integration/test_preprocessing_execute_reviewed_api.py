"""The legacy preprocessing-specific execute route cannot bypass Phase 7 authority."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app.api.dependencies import get_project_store
from src.backend.app.main import app
from src.backend.app.services.mock_store import SQLiteDesktopStore


def test_preprocessing_execute_reviewed_route_requires_execution_contract(tmp_path):
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    project = store.get_project("brain-tumor-study")
    assert project is not None
    project.metadata = {
        **(project.metadata or {}),
        "project_dir": str(tmp_path),
        "rawdata_dir": str(tmp_path / "rawdata"),
    }
    store.add_project(
        project,
        health_status="Review",
        rawdata_dir=str(tmp_path / "rawdata"),
        overwrite=True,
    )
    app.dependency_overrides[get_project_store] = lambda: store
    try:
        response = TestClient(app).post(
            "/api/projects/brain-tumor-study/preprocessing/runs/legacy-run/execute-reviewed",
            json={
                "confirmations": {
                    "confirm_rawdata_readonly": True,
                    "confirm_reviewed_execution": True,
                    "confirm_external_tools_if_needed": True,
                    "confirm_research_use_only": True,
                    "confirm_no_clinical_use": True,
                }
            },
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 410
    detail = response.json()["detail"]
    assert detail["error_code"] == "EXECUTION_CONTRACT_REQUIRED"
    assert detail["replacement"] == "/api/plans/execute-reviewed"
    assert not (tmp_path / "derivatives").exists()
