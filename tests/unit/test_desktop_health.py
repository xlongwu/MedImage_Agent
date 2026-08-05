"""Tests for environment health MATLAB/SPM extension."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime import desktop_config
from src.backend.app.services.environment_health import build_matlab_spm_health


def _mock_config(tmp_path: Path, monkeypatch, **overrides) -> None:
    """Write a minimal desktop config with overrides for testing."""
    base = dict(desktop_config.DEFAULT_DESKTOP_CONFIG)
    base.update(overrides)
    config_path = tmp_path / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(base), encoding="utf-8")
    monkeypatch.setattr(desktop_config, "DESKTOP_CONFIG_PATH", config_path)


def test_no_matlab_configured_returns_not_configured(tmp_path, monkeypatch):
    _mock_config(tmp_path, monkeypatch, matlab_command="", spm_dir="")
    health = build_matlab_spm_health()
    assert health["status"] in ("not_configured", "disabled")
    assert health["matlab"]["configured"] is False
    assert health["spm"]["configured"] is False


def test_matlab_spm_not_exist_returns_warning(tmp_path, monkeypatch):
    _mock_config(
        tmp_path,
        monkeypatch,
        matlab_command="nonexistent_matlab_binary",
        spm_dir="./third_party/nonexistent_spm",
    )
    health = build_matlab_spm_health()
    assert health["matlab"]["exists"] is False
    assert health["spm"]["exists"] is False
    assert health["status"] in ("warning", "not_configured")


def test_matlab_spm_ghost_path_returns_exists_true(tmp_path, monkeypatch):
    """Configure paths to existing directories (tmp_path) — exists=true."""
    _mock_config(
        tmp_path,
        monkeypatch,
        matlab_command=str(tmp_path),  # exists as dir
        spm_dir=str(tmp_path),
    )
    health = build_matlab_spm_health()
    assert health["matlab"]["exists"] is True
    assert health["spm"]["exists"] is True


def test_real_execution_disabled(tmp_path, monkeypatch):
    _mock_config(tmp_path, monkeypatch)
    health = build_matlab_spm_health()
    assert health["real_execution_enabled"] is False
    assert health["safe_allowlist_enabled"] is False


def test_desktop_health_endpoint_includes_matlab_spm(tmp_path, monkeypatch):
    _mock_config(tmp_path, monkeypatch)
    client = TestClient(app)
    resp = client.get("/api/desktop/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "matlab_spm" in body
    ms = body["matlab_spm"]
    assert "status" in ms
    assert "matlab" in ms
    assert "spm" in ms
    assert "real_execution_enabled" in ms
    assert "notes" in ms


def test_desktop_health_backward_compatible(tmp_path, monkeypatch):
    """Existing fields still present."""
    _mock_config(tmp_path, monkeypatch)
    client = TestClient(app)
    resp = client.get("/api/desktop/health")
    body = resp.json()
    assert body["ok"] is True
    assert "config" in body
    assert "checks" in body
    assert "gpu" in body
