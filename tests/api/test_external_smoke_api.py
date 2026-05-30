from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.tools import external_smoke


def _write_config(tmp_path: Path) -> Path:
    fake_matlab = tmp_path / "fake_matlab"
    fake_matlab.write_text("fake", encoding="utf-8")
    spm_dir = tmp_path / "spm12"
    dpabi_dir = tmp_path / "DPABI"
    raw_func = tmp_path / "rawdata" / "sub-001" / "func"
    spm_dir.mkdir()
    dpabi_dir.mkdir()
    raw_func.mkdir(parents=True)
    (raw_func / "sub-001_task-rest_bold.nii").write_bytes(b"fake nifti")

    def yml(path: Path) -> str:
        return str(path).replace("\\", "/")

    config = tmp_path / "project_config.yaml"
    config.write_text(
        "\n".join([
            "third_party:",
            f"  spm_dir: \"{yml(spm_dir)}\"",
            f"  dpabi_dir: \"{yml(dpabi_dir)}\"",
            "data:",
            f"  rawdata_dir: \"{yml(tmp_path / 'rawdata')}\"",
            "runtime:",
            f"  matlab_command: \"{yml(fake_matlab)}\"",
            f"  work_dir: \"{yml(tmp_path / 'work')}\"",
            f"  log_dir: \"{yml(tmp_path / 'logs')}\"",
            f"  derivatives_dir: \"{yml(tmp_path / 'derivatives')}\"",
            "",
        ]),
        encoding="utf-8",
    )
    return config


def test_external_smoke_status_without_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "external_smoke")
    client = TestClient(app)

    response = client.get("/api/external-smoke/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "No external smoke package" in " ".join(payload["errors"])


def test_external_smoke_manual_package_api_does_not_launch_matlab(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "external_smoke")
    config = _write_config(tmp_path)

    def fail_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("manual_package must not launch MATLAB")

    monkeypatch.setattr(subprocess, "run", fail_run)
    client = TestClient(app)

    response = client.post(
        "/api/external-smoke/run",
        json={"target": "all", "mode": "manual_package", "config_path": str(config)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert Path(payload["artifacts"]["report_md"]).exists()

    status = client.get("/api/external-smoke/status").json()
    assert status["checklist_text"]
    assert status["commands_text"]


def test_external_smoke_approved_mode_without_approval_is_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "external_smoke")
    config = _write_config(tmp_path)

    def fail_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("approved=false must not launch MATLAB")

    monkeypatch.setattr(subprocess, "run", fail_run)
    client = TestClient(app)

    response = client.post(
        "/api/external-smoke/run",
        json={"target": "spm", "mode": "approved_smoke", "config_path": str(config), "approved": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "approved_smoke requires --approve" in " ".join(payload["errors"])


def test_external_smoke_rejects_non_allowlisted_dpabi_function(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "external_smoke")
    config = _write_config(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/external-smoke/run",
        json={
            "target": "dpabi",
            "mode": "manual_package",
            "config_path": str(config),
            "dpabi_function": "DPARSF_run",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "Invalid DPABI function" in " ".join(payload["errors"])


def test_external_smoke_approved_mode_fake_runner_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "external_smoke")
    config = _write_config(tmp_path)

    def fake_spm(**kwargs):  # type: ignore[no-untyped-def]
        return {
            "ok": True,
            "warnings": [],
            "errors": [],
            "external_tool_result": {
                "ok": True,
                "tool_name": "spm.smoke_test",
                "backend": "matlab-spm",
                "returncode": 0,
                "logs": {},
            },
        }

    monkeypatch.setattr(external_smoke, "run_spm_smoke_test", fake_spm)
    client = TestClient(app)

    response = client.post(
        "/api/external-smoke/run",
        json={"target": "spm", "mode": "approved_smoke", "config_path": str(config), "approved": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert any(item.get("tool_name") == "spm.smoke_test" for item in payload["external_tool_results"])
