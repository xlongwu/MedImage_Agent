"""Tests for SPM runtime preflight and synthetic smoke — Phase 5C."""
from __future__ import annotations
from pathlib import Path
import pytest


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Env flag gating
# ═══════════════════════════════════════════════════════════════════════

def test_preflight_disabled_without_env_flags(monkeypatch):
    from src.backend.app.services.spm_runtime import spm_runtime_preflight
    result = spm_runtime_preflight("test", env={})
    assert result.status == "disabled"
    assert not result.matlab_available


def test_synthetic_smoke_disabled_without_env_flags(monkeypatch):
    from src.backend.app.schemas.spm_runtime import SpmSyntheticSmokeRequest
    from src.backend.app.services.spm_runtime import run_synthetic_spm_smoke
    req = SpmSyntheticSmokeRequest()
    result = run_synthetic_spm_smoke("test", req, env={})
    assert result.status == "disabled"


def test_validate_env_helper():
    from src.backend.app.schemas.spm_runtime import validate_synthetic_spm_env
    ok, missing = validate_synthetic_spm_env({})
    assert not ok; assert len(missing) == 5


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Preflight
# ═══════════════════════════════════════════════════════════════════════

def test_preflight_reports_missing_matlab(monkeypatch):
    import shutil as _sh
    monkeypatch.setattr(_sh, "which", lambda x: None)
    env = {"MEDIMAGE_MATLAB_ENABLED": "1", "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
           "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
           "MEDIMAGE_ALLOW_SYNTHETIC_SPM_PREPROCESSING_SMOKE": "1"}
    from src.backend.app.services.spm_runtime import spm_runtime_preflight
    result = spm_runtime_preflight("test", env=env)
    assert result.status == "blocked"


def test_preflight_ready_when_all_available(monkeypatch):
    import shutil as _sh
    monkeypatch.setattr(_sh, "which", lambda x: "/fake/matlab")
    env = {"MEDIMAGE_MATLAB_ENABLED": "1", "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
           "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
           "MEDIMAGE_ALLOW_SYNTHETIC_SPM_PREPROCESSING_SMOKE": "1",
           "MEDIMAGE_SPM_DIR": "/fake/spm"}
    monkeypatch.setattr(Path, "exists", lambda self: True)
    from src.backend.app.services.spm_runtime import spm_runtime_preflight
    result = spm_runtime_preflight("test", env=env)
    assert result.status == "ready_for_synthetic_smoke"
    assert result.matlab_available
    assert result.spm_available


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Synthetic smoke
# ═══════════════════════════════════════════════════════════════════════

_ALL_FLAGS = {"MEDIMAGE_MATLAB_ENABLED": "1", "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
              "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
              "MEDIMAGE_ALLOW_SYNTHETIC_SPM_PREPROCESSING_SMOKE": "1"}


def test_smoke_generates_artifacts(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.spm_runtime.mock_store", store)
    monkeypatch.setattr("src.backend.app.services.spm_runtime._gen_synthetic_nifti",
        lambda d: d / "synth_bold.nii" if (d / "synth_bold.nii").write_text("fake") or True else None)
    from src.backend.app.schemas.spm_runtime import SpmSyntheticSmokeRequest
    from src.backend.app.services.spm_runtime import run_synthetic_spm_smoke
    req = SpmSyntheticSmokeRequest(confirm_synthetic_only=True)
    result = run_synthetic_spm_smoke("brain-tumor-study", req, env=_ALL_FLAGS, project_dir=str(tmp_path))
    assert result.ok; assert result.status == "generated"
    assert Path(result.batch_script_path).exists()
    assert "spm" in Path(result.batch_script_path).read_text().lower()


def test_smoke_writes_batch_script(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.spm_runtime.mock_store", store)
    monkeypatch.setattr("src.backend.app.services.spm_runtime._gen_synthetic_nifti",
        lambda d: (d / "synth_bold.nii").write_text("fake") or d / "synth_bold.nii")
    from src.backend.app.schemas.spm_runtime import SpmSyntheticSmokeRequest
    from src.backend.app.services.spm_runtime import run_synthetic_spm_smoke
    req = SpmSyntheticSmokeRequest(confirm_synthetic_only=True)
    result = run_synthetic_spm_smoke("brain-tumor-study", req, env=_ALL_FLAGS, project_dir=str(tmp_path))
    batch = Path(result.batch_script_path).read_text()
    assert "spm_jobman" in batch
    assert "realign" in batch.lower()


def test_smoke_command_template_no_shell(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.spm_runtime.mock_store", store)
    monkeypatch.setattr("src.backend.app.services.spm_runtime._gen_synthetic_nifti",
        lambda d: (d / "synth_bold.nii").write_text("fake") or d / "synth_bold.nii")
    from src.backend.app.schemas.spm_runtime import SpmSyntheticSmokeRequest
    from src.backend.app.services.spm_runtime import run_synthetic_spm_smoke
    req = SpmSyntheticSmokeRequest(confirm_synthetic_only=True)
    result = run_synthetic_spm_smoke("brain-tumor-study", req, env=_ALL_FLAGS, project_dir=str(tmp_path))
    template = __import__("json").loads(Path(result.command_template_path).read_text())
    assert template["shell"] is False
    assert "shell=True" not in str(template)


def test_smoke_safety_flags(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.spm_runtime.mock_store", store)
    monkeypatch.setattr("src.backend.app.services.spm_runtime._gen_synthetic_nifti",
        lambda d: (d / "synth_bold.nii").write_text("fake") or d / "synth_bold.nii")
    from src.backend.app.schemas.spm_runtime import SpmSyntheticSmokeRequest
    from src.backend.app.services.spm_runtime import run_synthetic_spm_smoke
    req = SpmSyntheticSmokeRequest(confirm_synthetic_only=True)
    result = run_synthetic_spm_smoke("brain-tumor-study", req, env=_ALL_FLAGS, project_dir=str(tmp_path))
    assert result.safety_flags["synthetic_only"] is True
    assert result.safety_flags["no_user_rawdata_execution"] is True
    assert result.safety_flags["no_dpabi_execution"] is True


def test_preflight_endpoint_returns_200():
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/preprocessing/spm-runtime/preflight")
    assert resp.status_code == 200; assert "status" in resp.json()
