"""Tests for ALFF/ReHo sandbox execution — Phase 5M."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_alff_reho_execution.mock_store", store)
    return store

def _make_func(tmp_path):
    so = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / "tf-ex" / "sandbox_output"
    sub = so / "sub-001"; sub.mkdir(parents=True)
    (sub / "filtered_sub-001_task-rest_bold.nii").write_text("filtered"); return so

_ALL = {"MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_ALFF_REHO": "1"}

from src.backend.app.schemas.preprocessing_alff_reho_execution import AlffRehoSandboxExecutionRequest
from src.backend.app.services.preprocessing_alff_reho_execution import run_alff_reho_sandbox_execution

def test_disabled_without_env(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = run_alff_reho_sandbox_execution("test", "pp-test",
        AlffRehoSandboxExecutionRequest(dry_run_id="dr"), env={}, project_dir=str(tmp_path))
    assert result.status == "disabled"

def test_missing_dry_run_blocks(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = run_alff_reho_sandbox_execution("brain-tumor-study", "pp-test",
        AlffRehoSandboxExecutionRequest(dry_run_id="nonexistent"), env=_ALL, project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_metadata_first_exec_writes_plans(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); func_dir = _make_func(tmp_path)
    dd = tmp_path / "preprocessing_runs" / "pp-test" / "spm_dry_runs" / "dr-test"; dd.mkdir(parents=True)
    (dd / "alff_reho_dry_run_manifest.json").write_text('{"status":"dry_run_preview"}')
    import builtins; ri = builtins.__import__
    def mi(name, *a, **kw):
        if name in ("nibabel", "numpy"): raise ImportError("mock")
        return ri(name, *a, **kw)
    monkeypatch.setattr(builtins, "__import__", mi)
    req = AlffRehoSandboxExecutionRequest(dry_run_id="dr-test", functional_input_dir=str(func_dir), confirm_sandbox_copy=True)
    result = run_alff_reho_sandbox_execution("brain-tumor-study", "pp-test", req, env=_ALL, project_dir=str(tmp_path))
    assert result.ok and Path(result.metric_plan_path).exists()

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app; client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/alff-reho/execute-sandbox",
        json={"dry_run_id": "dr", "confirm_sandbox_copy": True})
    assert resp.status_code == 200
