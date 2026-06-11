"""Tests for pipeline validation — Phase 5O."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_pipeline_validation.mock_store", store)
    return store

from src.backend.app.services.preprocessing_pipeline_validation import validate_preprocessing_pipeline

def test_not_started_for_missing_run(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.status == "not_started"

def test_detects_partial_pipeline(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    rd = tmp_path / "preprocessing_runs" / "pp-test"; rd.mkdir(parents=True)
    (rd / "reports").mkdir()
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.status in ("warning", "ready_for_review")

def test_includes_stage_summary(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    rd = tmp_path / "preprocessing_runs" / "pp-test"; rd.mkdir(parents=True)
    (rd / "spm_dry_runs").mkdir(); (rd / "spm_exec").mkdir(); (rd / "reports").mkdir()
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert len(result.stage_summary) > 0

def test_no_dpabi_in_safety_flags(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    rd = tmp_path / "preprocessing_runs" / "pp-test"; rd.mkdir(parents=True)
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.safety_flags["no_dpabi_execution"] is True

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app; client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/validation")
    assert resp.status_code == 200
