"""Tests for ALFF/ReHo output registration — Phase 5M."""
from __future__ import annotations
from pathlib import Path
import json, pytest

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_stage_outputs.mock_store", store)
    return store

def _make_exec(tmp_path, exec_id="ar-ex-abc"):
    ed = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / exec_id
    ed.mkdir(parents=True)
    (ed / "sandbox_output").mkdir(); return ed

from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
from src.backend.app.services.preprocessing_stage_outputs import register_alff_reho_outputs

def test_registers_metadata_only_warning(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); _make_exec(tmp_path)
    result = register_alff_reho_outputs("brain-tumor-study", "pp-test",
        StageOutputRegistrationRequest(execution_id="ar-ex-abc", confirm_sandbox_outputs=True), project_dir=str(tmp_path))
    assert result.status == "warning"

def test_blocks_missing_exec(tmp_path):
    result = register_alff_reho_outputs("test", "pp-test", StageOutputRegistrationRequest(execution_id=""))
    assert result.status == "blocked"

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app; _make_exec(tmp_path); client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/stage-outputs/register-alff-reho",
        json={"execution_id": "ar-ex-abc", "confirm_sandbox_outputs": True})
    assert resp.status_code == 200
