"""Tests for Smoothing dry-run - Phase 5I."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_smoothing_dry_run.mock_store", store)
    return store

def _make_registered_output(tmp_path):
    so = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / "cn-ex-1" / "sandbox_output"
    sub = so / "sub-001"; sub.mkdir(parents=True)
    (sub / "wsub-001_task-rest_bold.nii").write_text("norm")
    return so

from src.backend.app.schemas.preprocessing_smoothing_dry_run import SmoothingDryRunRequest
from src.backend.app.services.preprocessing_smoothing_dry_run import run_smoothing_dry_run

def test_blocks_no_func_input(tmp_path):
    result = run_smoothing_dry_run("test", "pp-test", SmoothingDryRunRequest(), project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_succeeds_with_func(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); sandbox = _make_registered_output(tmp_path)
    result = run_smoothing_dry_run("brain-tumor-study", "pp-test",
        SmoothingDryRunRequest(functional_input_dir=str(sandbox), confirm_dry_run_only=True), project_dir=str(tmp_path))
    assert result.ok; assert result.functional_input_count == 1

def test_writes_batch(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); sandbox = _make_registered_output(tmp_path)
    result = run_smoothing_dry_run("brain-tumor-study", "pp-test",
        SmoothingDryRunRequest(functional_input_dir=str(sandbox), confirm_dry_run_only=True), project_dir=str(tmp_path))
    assert len(result.batch_preview_paths) > 0
    assert "SMOOTHING_DRY_RUN_ONLY" in Path(result.batch_preview_paths[0]).read_text()

def test_no_nifti_outputs(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); sandbox = _make_registered_output(tmp_path)
    result = run_smoothing_dry_run("brain-tumor-study", "pp-test",
        SmoothingDryRunRequest(functional_input_dir=str(sandbox), confirm_dry_run_only=True), project_dir=str(tmp_path))
    if result.dry_run_dir:
        assert len(list(Path(result.dry_run_dir).rglob("*.nii*"))) == 0

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/spm/smoothing/dry-run",
        json={"confirm_dry_run_only": True})
    assert resp.status_code == 200
