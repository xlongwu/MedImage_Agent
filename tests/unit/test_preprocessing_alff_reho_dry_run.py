"""Tests for ALFF/ReHo dry-run — Phase 5L."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_alff_reho_dry_run.mock_store", store)
    return store

def _make_func(tmp_path):
    so = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / "tf-ex" / "sandbox_output"
    sub = so / "sub-001"; sub.mkdir(parents=True)
    (sub / "filtered_sub-001_task-rest_bold.nii").write_text("filtered"); return so

from src.backend.app.schemas.preprocessing_alff_reho_dry_run import AlffRehoDryRunRequest
from src.backend.app.services.preprocessing_alff_reho_dry_run import run_alff_reho_dry_run

def test_blocks_no_func(tmp_path):
    result = run_alff_reho_dry_run("test", "pp-test", AlffRehoDryRunRequest(), project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_blocks_no_metrics(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_func(tmp_path)
    result = run_alff_reho_dry_run("brain-tumor-study", "pp-test",
        AlffRehoDryRunRequest(functional_input_dir=str(func_dir), compute_alff=False, compute_falff=False, compute_reho=False), project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_succeeds(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_func(tmp_path)
    result = run_alff_reho_dry_run("brain-tumor-study", "pp-test",
        AlffRehoDryRunRequest(functional_input_dir=str(func_dir), confirm_dry_run_only=True), project_dir=str(tmp_path))
    assert result.ok and result.functional_input_count == 1

def test_writes_plans(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_func(tmp_path)
    result = run_alff_reho_dry_run("brain-tumor-study", "pp-test",
        AlffRehoDryRunRequest(functional_input_dir=str(func_dir), confirm_dry_run_only=True), project_dir=str(tmp_path))
    assert len(result.alff_plan_paths) + len(result.reho_plan_paths) > 0

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app; client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/alff-reho/dry-run",
        json={"confirm_dry_run_only": True})
    assert resp.status_code == 200
