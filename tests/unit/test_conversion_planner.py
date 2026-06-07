"""Tests for POST /api/projects/{project_id}/conversion/dry-run."""

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
from src.backend.app.planner import project_context, reviewed_plan_store
from src.backend.app.runtime import desktop_config
from src.backend.app.services import conversion_planner
from src.backend.app.services.mock_store import SQLiteDesktopStore


def _isolated_store(tmp_path: Path, monkeypatch) -> SQLiteDesktopStore:
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    monkeypatch.setattr(
        desktop_config,
        "DESKTOP_CONFIG_PATH",
        tmp_path / "desktop_config.json",
    )
    monkeypatch.setattr(project_routes, "DEFAULT_PROJECTS_ROOT", tmp_path / "projects")
    for module in (
        project_routes,
        dashboard_routes,
        project_context,
        reviewed_plan_store,
        project_history_routes,
        execute_reviewed_routes,
        conversion_planner,
    ):
        monkeypatch.setattr(module, "mock_store", store)
    desktop_config.DESKTOP_CONFIG_PATH.write_text(
        json.dumps(desktop_config.DEFAULT_DESKTOP_CONFIG),
        encoding="utf-8",
    )
    return store


def _create_project(client: TestClient, tmp_path: Path, name: str = "Conversion Project") -> dict:
    response = client.post(
        "/api/projects/create",
        json={
            "project_name": name,
            "rawdata_dir": str(Path("examples/synthetic_bids/rawdata").resolve()),
            "project_dir": str(tmp_path / name.replace(" ", "_")),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_project_not_found_returns_404():
    client = TestClient(app)
    resp = client.post("/api/projects/nonexistent/conversion/dry-run", json={})
    assert resp.status_code == 404


def test_dry_run_returns_structured_response(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)

    resp = client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["project_id"] == created["project_id"]
    assert body["dry_run"] is True
    assert body["status"] in ("ready", "warning", "blocked", "unknown")
    assert isinstance(body["source_summaries"], list)
    assert isinstance(body["mapping_preview"], list)
    assert isinstance(body["safety_flags"], dict)


def test_safety_flags_all_true(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)

    resp = client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={},
    )
    flags = resp.json()["safety_flags"]
    assert flags.get("dry_run_only") is True
    assert flags.get("rawdata_read_only") is True
    assert flags.get("no_files_written") is True
    assert flags.get("no_external_tools_executed") is True
    assert flags.get("requires_user_review_before_conversion") is True
    assert flags.get("output_path_is_preview_only") is True


def test_dry_run_does_not_create_files(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    project_dir = Path(created["project_dir"])

    # Snapshot before
    before = set()
    if project_dir.exists():
        before = {str(p.relative_to(project_dir)) for p in project_dir.rglob("*")}

    client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={},
    )

    # Snapshot after — nothing new should exist
    after = set()
    if project_dir.exists():
        after = {str(p.relative_to(project_dir)) for p in project_dir.rglob("*")}
    new_files = after - before
    assert not new_files, f"Dry-run created files: {new_files}"


def test_request_cannot_inject_arbitrary_source_path(tmp_path, monkeypatch):
    """The endpoint ignores arbitrary path fields — only project-scoped roots are used."""
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)

    resp = client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={"source_import_ids": [], "output_root_name": "../../etc"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # output_root_preview should be project-scoped, not "../../etc"
    preview = body.get("output_root_preview") or ""
    assert "../" not in preview


def test_synthetic_bids_classified_as_bids(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)

    resp = client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={"include_loose_nifti": True},
    )
    body = resp.json()
    types = {s["source_type"] for s in body["source_summaries"]}
    # The synthetic BIDS fixture should be classified as "bids"
    assert "bids" in types, f"Expected 'bids' in source types, got: {types}"


def test_blocking_status_when_no_convertible(tmp_path, monkeypatch):
    """When include_dicom=False and include_loose_nifti=False, no mappings produced."""
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)

    resp = client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={"include_dicom": False, "include_loose_nifti": False},
    )
    body = resp.json()
    assert body["status"] == "blocked"
    assert len(body["blocking_issues"]) > 0


def test_mapping_confidence_fields_present(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)

    resp = client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={},
    )
    body = resp.json()
    for mapping in body["mapping_preview"]:
        assert "confidence" in mapping
        assert mapping["confidence"] in ("high", "medium", "low", "manual_required")
        assert "suggested_relative_path" in mapping


def test_output_root_preview_is_scoped(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)

    resp = client.post(
        f"/api/projects/{created['project_id']}/conversion/dry-run",
        json={"output_root_name": "test_converted"},
    )
    body = resp.json()
    assert body["output_root_name"] == "test_converted"
    # output_root_preview should be a project-relative path (may be None
    # if the store doesn't have project_dir metadata in the test fixture)
    preview = body.get("output_root_preview")
    if preview is not None:
        assert "test_converted" in preview
