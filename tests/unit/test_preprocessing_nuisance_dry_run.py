"""Tests for Nuisance regression dry-run — Phase 5J."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_nuisance_dry_run.mock_store", store)
    return store

def _make_smoothed(tmp_path):
    so = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / "s-ex" / "sandbox_output"
    sub = so / "sub-001"; sub.mkdir(parents=True)
    (sub / "ssub-001_task-rest_bold.nii").write_text("smooth")
    (sub / "rp_sub-001.txt").write_text("motion params"); return so

from src.backend.app.schemas.preprocessing_nuisance_dry_run import NuisanceDryRunRequest
from src.backend.app.services.preprocessing_nuisance_dry_run import run_nuisance_dry_run

def test_blocks_no_func(tmp_path):
    result = run_nuisance_dry_run("test", "pp-test", NuisanceDryRunRequest(), project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_succeeds_with_smoothed(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_smoothed(tmp_path)
    result = run_nuisance_dry_run("brain-tumor-study", "pp-test",
        NuisanceDryRunRequest(functional_input_dir=str(func_dir), confirm_dry_run_only=True), project_dir=str(tmp_path))
    assert result.ok; assert result.functional_input_count == 1

def test_writes_regressor_design(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_smoothed(tmp_path)
    result = run_nuisance_dry_run("brain-tumor-study", "pp-test",
        NuisanceDryRunRequest(functional_input_dir=str(func_dir), confirm_dry_run_only=True), project_dir=str(tmp_path))
    assert len(result.regressor_design_paths) > 0

def test_detects_motion_files(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_smoothed(tmp_path)
    result = run_nuisance_dry_run("brain-tumor-study", "pp-test",
        NuisanceDryRunRequest(functional_input_dir=str(func_dir), confirm_dry_run_only=True), project_dir=str(tmp_path))
    assert result.motion_parameter_count == 1

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app; client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/nuisance-regression/dry-run",
        json={"confirm_dry_run_only": True})
    assert resp.status_code == 200
