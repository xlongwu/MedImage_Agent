"""Tests for Coreg/Norm output registration - Phase 5I."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_stage_outputs.mock_store", store)
    return store

def _make_exec_dir(tmp_path, exec_id="cn-ex-abc", with_outputs=True):
    ed = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / exec_id
    ed.mkdir(parents=True)
    (ed / "manifest.json").write_text('{"status":"succeeded"}')
    so = ed / "sandbox_output"; so.mkdir()
    if with_outputs:
        sub = so / "sub-001"; sub.mkdir()
        (sub / "wsub-001_task-rest_bold.nii").write_text("norm_func")
    return ed

from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
from src.backend.app.services.preprocessing_stage_outputs import register_coreg_norm_outputs

def test_registers_norm_outputs(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); _make_exec_dir(tmp_path)
    req = StageOutputRegistrationRequest(execution_id="cn-ex-abc", confirm_sandbox_outputs=True)
    result = register_coreg_norm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert result.ok; assert len(result.registered_bold_outputs) > 0

def test_blocks_missing_exec_id(tmp_path):
    result = register_coreg_norm_outputs("test", "pp-test", StageOutputRegistrationRequest(execution_id=""))
    assert result.status == "blocked"

def test_blocks_missing_exec_dir(tmp_path):
    result = register_coreg_norm_outputs("brain-tumor-study", "pp-test",
        StageOutputRegistrationRequest(execution_id="nonexistent"), project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_blocks_zero_outputs(tmp_path):
    _make_exec_dir(tmp_path, with_outputs=False)
    result = register_coreg_norm_outputs("brain-tumor-study", "pp-test",
        StageOutputRegistrationRequest(execution_id="cn-ex-abc"), project_dir=str(tmp_path))
    assert result.status == "blocked"

def test_writes_registry(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); _make_exec_dir(tmp_path)
    result = register_coreg_norm_outputs("brain-tumor-study", "pp-test",
        StageOutputRegistrationRequest(execution_id="cn-ex-abc", confirm_sandbox_outputs=True), project_dir=str(tmp_path))
    assert (Path(result.stage_output_dir) / "coreg_norm_stage_output_registry.json").exists()

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    _make_exec_dir(tmp_path)
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/stage-outputs/register-coreg-norm",
        json={"execution_id": "cn-ex-abc", "confirm_sandbox_outputs": True})
    assert resp.status_code == 200
