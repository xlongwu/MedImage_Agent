"""Tests for pipeline report — Phase 5N."""

from __future__ import annotations

from pathlib import Path


def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_pipeline_report.mock_store", store)
    return store


from src.backend.app.services.preprocessing_pipeline_report import (  # noqa: E402
    generate_pipeline_report,  # noqa: E402
)


def test_handles_empty_pipeline(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = generate_pipeline_report("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.ok and result.status == "generated"
    assert len(result.stage_statuses) > 0


def test_writes_json_report(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = generate_pipeline_report("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert (Path(result.report_path) / "preprocessing_pipeline_report.json").exists()


def test_writes_md_report(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = generate_pipeline_report("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert (Path(result.report_path) / "preprocessing_pipeline_report.md").exists()


def test_safety_flags(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = generate_pipeline_report("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.safety_flags["no_clinical_diagnosis"] is True


def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient

    from src.backend.app.main import app

    client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/report")
    assert resp.status_code == 200
