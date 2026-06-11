"""Tests for stage output registration — Phase 5F."""
from __future__ import annotations
from pathlib import Path
import json, pytest


def _setup_store(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_stage_outputs.mock_store", store)
    return store


def _make_exec_dir(tmp_path, exec_id="spm-ex-abc123", with_outputs=True):
    ed = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / exec_id
    ed.mkdir(parents=True)
    (ed / "manifest.json").write_text('{"status":"succeeded"}')
    so = ed / "sandbox_output"; so.mkdir()
    if with_outputs:
        sub = so / "sub-001"; sub.mkdir()
        (sub / "rasub-001_task-rest_bold.nii").write_text("output")
        (sub / "rp_sub-001.txt").write_text("motion params")
        (sub / "meansub-001_task-rest_bold.nii").write_text("mean")
    return ed


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════

def test_registers_sandbox_outputs(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch); _make_exec_dir(tmp_path)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="spm-ex-abc123", confirm_sandbox_outputs=True)
    result = register_sandbox_spm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert result.ok; assert result.status == "registered"
    assert len(result.registered_bold_outputs) == 1


def test_blocks_missing_execution_id(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="")
    result = register_sandbox_spm_outputs("test", "pp-test", req)
    assert result.status == "blocked"


def test_blocks_missing_exec_dir(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="nonexistent")
    result = register_sandbox_spm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert result.status == "blocked"


def test_blocks_zero_output_bold(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch); _make_exec_dir(tmp_path, with_outputs=False)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="spm-ex-abc123")
    result = register_sandbox_spm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert result.status == "blocked"


def test_records_motion_files(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch); _make_exec_dir(tmp_path)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="spm-ex-abc123", confirm_sandbox_outputs=True)
    result = register_sandbox_spm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert len(result.motion_files) == 1


def test_records_mean_image(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch); _make_exec_dir(tmp_path)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="spm-ex-abc123", confirm_sandbox_outputs=True)
    result = register_sandbox_spm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert len(result.mean_images) == 1


def test_writes_registry_artifacts(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch); _make_exec_dir(tmp_path)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="spm-ex-abc123", confirm_sandbox_outputs=True)
    result = register_sandbox_spm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert Path(result.stage_output_dir).exists()
    assert (Path(result.stage_output_dir) / "stage_output_registry.json").exists()


def test_safety_flags(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch); _make_exec_dir(tmp_path)
    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs
    req = StageOutputRegistrationRequest(execution_id="spm-ex-abc123", confirm_sandbox_outputs=True)
    result = register_sandbox_spm_outputs("brain-tumor-study", "pp-test", req, project_dir=str(tmp_path))
    assert result.safety_flags["no_matlab_executed"] is True
    assert result.safety_flags["no_additional_execution"] is True


def test_endpoint_returns_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    _make_exec_dir(tmp_path)
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/stage-outputs/register-sandbox-spm",
        json={"execution_id": "spm-ex-abc123", "confirm_sandbox_outputs": True})
    assert resp.status_code == 200
