"""Tests for GET /api/projects/{project_id}/motion-qc/readiness."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.app.api import (
    dashboard_routes,
    execute_reviewed_routes,
    project_history_routes,
    project_routes,
)
from src.backend.app.main import app
from src.backend.app.planner import project_context, reviewed_plan_store, pipeline_presets
from src.backend.app.runtime import desktop_config
from src.backend.app.services import motion_qc_readiness
import src.backend.app.services.mock_store as mock_store_module
from src.backend.app.services.mock_store import SQLiteDesktopStore


def _isolated_store(tmp_path: Path, monkeypatch) -> SQLiteDesktopStore:
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    monkeypatch.setattr(desktop_config, "DESKTOP_CONFIG_PATH", tmp_path / "desktop_config.json")
    monkeypatch.setattr(project_routes, "DEFAULT_PROJECTS_ROOT", tmp_path / "projects")
    for module in (project_routes, dashboard_routes, project_context, reviewed_plan_store, project_history_routes, execute_reviewed_routes, motion_qc_readiness,
        mock_store_module,
    ):
        monkeypatch.setattr(module, "mock_store", store)
    desktop_config.DESKTOP_CONFIG_PATH.write_text(json.dumps(desktop_config.DEFAULT_DESKTOP_CONFIG), encoding="utf-8")
    return store


def _create_project(client: TestClient, tmp_path: Path) -> dict:
    resp = client.post("/api/projects/create", json={
        "project_name": "Motion QC Project", "rawdata_dir": str(Path("examples/synthetic_bids/rawdata").resolve()),
        "project_dir": str(tmp_path / "motion_qc_proj"),
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_project_not_found_returns_404():
    client = TestClient(app)
    resp = client.get("/api/projects/nonexistent/motion-qc/readiness")
    assert resp.status_code == 404


def test_created_project_returns_structured_response(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    resp = client.get(f"/api/projects/{created['project_id']}/motion-qc/readiness")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["project_id"] == created["project_id"]
    assert body["status"] in ("ready", "warning", "blocked", "unknown")
    assert isinstance(body["candidates"], list)
    assert isinstance(body["safety_flags"], dict)


def test_safety_flags_all_true(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    resp = client.get(f"/api/projects/{created['project_id']}/motion-qc/readiness")
    flags = resp.json()["safety_flags"]
    assert flags.get("read_only") is True
    assert flags.get("rawdata_not_modified") is True
    assert flags.get("no_realign_executed") is True
    assert flags.get("no_external_tools_executed") is True
    assert flags.get("planning_only") is True


def test_candidate_fields_present(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    resp = client.get(f"/api/projects/{created['project_id']}/motion-qc/readiness")
    body = resp.json()
    for c in body["candidates"]:
        assert "subject_id" in c
        assert "bold_path" in c
        assert "has_sidecar" in c
        assert "has_motion_params" in c
        assert "has_fd_column" in c


def test_endpoint_ignores_arbitrary_path_query(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    resp = client.get(f"/api/projects/{created['project_id']}/motion-qc/readiness?path=../../etc")
    assert resp.status_code == 200


def test_preset_metadata_reflects_read_only_status():
    preset = pipeline_presets.get_preset("rsfmri_preproc_mvp")
    assert preset is not None
    for node in preset.nodes:
        if node.id == "rsfmri_motion_qc_plan":
            assert node.executable is False
            assert node.backend == "contract"
            assert "read-only" in " ".join(node.safety_notes).lower()
            assert "inspectable" in str(node.params)
            break
    else:
        raise AssertionError("rsfmri_motion_qc_plan not found in preset")
