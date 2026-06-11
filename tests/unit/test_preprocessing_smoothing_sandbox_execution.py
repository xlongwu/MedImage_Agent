"""Tests for Smoothing sandbox execution — Phase 5J."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_smoothing_execution.mock_store", store)
    return store

def _make_func(tmp_path):
    so = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / "cn-ex" / "sandbox_output"
    sub = so / "sub-001"; sub.mkdir(parents=True)
    (sub / "wsub-001_task-rest_bold.nii").write_text("func"); return so

_ALL = {"MEDIMAGE_MATLAB_ENABLED": "1", "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_SPM_PREPROCESSING": "1",
        "MEDIMAGE_ALLOW_SANDBOXED_SPM_SMOOTHING": "1"}

from src.backend.app.schemas.preprocessing_smoothing_execution import SmoothingSandboxExecutionRequest
from src.backend.app.services.preprocessing_smoothing_execution import run_smoothing_sandbox_execution
import subprocess as _sp

def test_disabled_without_env(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    req = SmoothingSandboxExecutionRequest(dry_run_id="dr-test")
    result = run_smoothing_sandbox_execution("test", "pp-test", req, env={}, project_dir=str(tmp_path))
    assert result.status == "disabled"

def test_missing_dry_run_blocks(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = run_smoothing_sandbox_execution("brain-tumor-study", "pp-test",
        SmoothingSandboxExecutionRequest(dry_run_id="nonexistent"), env=_ALL, project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_sandbox_copies_func(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_func(tmp_path)
    dd = tmp_path / "preprocessing_runs" / "pp-test" / "spm_dry_runs" / "dr-test"; dd.mkdir(parents=True)
    (dd / "smoothing_dry_run_manifest.json").write_text('{"status":"dry_run_preview"}')
    monkeypatch.setattr(_sp, "run", lambda *a, **kw: type("R",(),{"returncode":0,"stdout":"ok","stderr":""})())
    req = SmoothingSandboxExecutionRequest(dry_run_id="dr-test", functional_input_dir=str(func_dir), confirm_sandbox_copy=True)
    result = run_smoothing_sandbox_execution("brain-tumor-study", "pp-test", req, env=_ALL, project_dir=str(tmp_path))
    assert result.ok and Path(result.sandbox_input_dir).exists()

def test_safety_flags(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_func(tmp_path)
    dd = tmp_path / "preprocessing_runs" / "pp-test" / "spm_dry_runs" / "dr-test"; dd.mkdir(parents=True)
    (dd / "smoothing_dry_run_manifest.json").write_text('{"status":"dry_run_preview"}')
    monkeypatch.setattr(_sp, "run", lambda *a, **kw: type("R",(),{"returncode":0,"stdout":"ok","stderr":""})())
    req = SmoothingSandboxExecutionRequest(dry_run_id="dr-test", functional_input_dir=str(func_dir), confirm_sandbox_copy=True)
    result = run_smoothing_sandbox_execution("brain-tumor-study", "pp-test", req, env=_ALL, project_dir=str(tmp_path))
    assert result.safety_flags["smoothing_only"] is True

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app; client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/spm/smoothing/execute-sandbox",
        json={"dry_run_id": "dr-test", "confirm_sandbox_copy": True})
    assert resp.status_code == 200
