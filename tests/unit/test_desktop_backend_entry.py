from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.app.desktop_backend_entry import (
    APP_IMPORT_STRING,
    DEFAULT_DESKTOP_HOST,
    DesktopBackendConfig,
    ensure_packaged_windows_runtime_dirs,
    parse_args,
    run_backend,
    validate_host,
)
from src.backend.app.main import app


def test_desktop_backend_entry_defaults_to_loopback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEDIMAGE_DESKTOP_BACKEND_HOST", raising=False)
    monkeypatch.delenv("MEDIMAGE_DESKTOP_BACKEND_PORT", raising=False)
    config = parse_args([])

    assert config.host == DEFAULT_DESKTOP_HOST
    assert config.port == 8765


def test_desktop_backend_entry_reads_port_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEDIMAGE_DESKTOP_BACKEND_PORT", "8999")
    config = parse_args([])

    assert config.port == 8999


def test_desktop_backend_entry_rejects_non_loopback_host():
    with pytest.raises(ValueError, match="127.0.0.1"):
        validate_host("0.0.0.0")


def test_desktop_backend_entry_runs_uvicorn_without_reload(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_run(app_import: str, **kwargs: object) -> None:
        captured["app_import"] = app_import
        captured.update(kwargs)

    monkeypatch.setattr("src.backend.app.desktop_backend_entry.uvicorn.run", fake_run)
    run_backend(DesktopBackendConfig(host="127.0.0.1", port=8765, log_level="info"))

    assert captured["app_import"] == APP_IMPORT_STRING
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8765
    assert captured["reload"] is False
    assert captured["factory"] is False


def test_frozen_windows_runtime_bin_stays_inside_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    monkeypatch.setattr("src.backend.app.desktop_backend_entry.os.name", "nt")
    monkeypatch.setenv("MEDIMAGE_DESKTOP_WORKSPACE", str(tmp_path))

    created = ensure_packaged_windows_runtime_dirs()

    assert created == (tmp_path / "bin",)
    assert (tmp_path / "bin").is_dir()


def test_windows_runtime_bin_is_noop_without_desktop_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    monkeypatch.setattr("src.backend.app.desktop_backend_entry.os.name", "nt")
    monkeypatch.delenv("MEDIMAGE_DESKTOP_WORKSPACE", raising=False)

    assert ensure_packaged_windows_runtime_dirs() == ()
    assert not (tmp_path / "bin").exists()


def test_backend_health_endpoints_available_for_desktop_shell():
    client = TestClient(app)

    root_health = client.get("/health")
    api_health = client.get("/api/health")

    assert root_health.status_code == 200
    assert root_health.json()["ok"] is True
    assert api_health.status_code == 200
