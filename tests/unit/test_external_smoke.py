from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from src.backend.app.tools import external_smoke
from src.backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke
from src.backend.app.tools.dpabi_wrapper import run_dpabi_smoke_test


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
    config = tmp_path / "project_config.yaml"
    def yml(path: Path) -> str:
        return str(path).replace("\\", "/")

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


def test_external_smoke_manual_package_does_not_launch_matlab(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = _write_config(tmp_path)
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "reports" / "external_smoke")

    def fail_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("manual_package must not launch MATLAB")

    monkeypatch.setattr(subprocess, "run", fail_run)

    result = external_smoke.run_external_smoke(
        target="all",
        mode="manual_package",
        config_path=str(config),
    )

    assert result["ok"] is True
    assert Path(result["artifacts"]["checklist"]).exists()
    assert Path(result["artifacts"]["approval_template"]).exists()
    assert result["next_actions"]


def test_external_smoke_approved_mode_requires_explicit_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = _write_config(tmp_path)
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "reports" / "external_smoke")

    def fail_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("approved_smoke without --approve must not launch MATLAB")

    monkeypatch.setattr(subprocess, "run", fail_run)

    result = external_smoke.run_external_smoke(
        target="spm",
        mode="approved_smoke",
        config_path=str(config),
        approve=False,
    )

    assert result["ok"] is False
    assert "approved_smoke requires --approve" in " ".join(result["errors"])


def test_external_smoke_approved_mode_collects_fake_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = _write_config(tmp_path)
    monkeypatch.setattr(external_smoke, "REPORT_DIR", tmp_path / "reports" / "external_smoke")

    def fake_spm(**kwargs):  # type: ignore[no-untyped-def]
        return {
            "ok": True,
            "errors": [],
            "warnings": [],
            "external_tool_result": {
                "ok": True,
                "tool_name": "spm.smoke_test",
                "backend": "matlab-spm",
                "returncode": 0,
                "logs": {},
            },
        }

    monkeypatch.setattr(external_smoke, "run_spm_smoke_test", fake_spm)

    result = external_smoke.run_external_smoke(
        target="spm",
        mode="approved_smoke",
        config_path=str(config),
        approve=True,
    )

    assert result["ok"] is True
    assert any(item.get("tool_name") == "spm.smoke_test" for item in result["external_tool_results"])


def test_dpabi_smoke_unapproved_returns_external_tool_result(tmp_path: Path):
    result = run_dpabi_smoke_test(
        dpabi_dir=str(tmp_path / "DPABI"),
        matlab_command="matlab",
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
    )

    assert result["ok"] is False
    assert result["external_tool_result"]["tool_name"] == "dpabi.smoke_test"
    assert result["external_tool_result"]["approval"]["required"] is True


def test_dpabi_smoke_fake_matlab_success_has_external_tool_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd: list[str], stdout=None, stderr=None, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        if stdout:
            stdout.write("fake DPABI smoke stdout\n")
        if stderr:
            stderr.write("fake DPABI smoke stderr\n")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    dpabi_dir = tmp_path / "DPABI"
    dpabi_dir.mkdir()
    result = run_dpabi_smoke_test(
        dpabi_dir=str(dpabi_dir),
        matlab_command="matlab",
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )

    assert result["ok"] is True
    assert result["external_tool_result"]["returncode"] == 0
    assert Path(result["external_tool_result"]["logs"]["stdout"]).exists()


def test_dpabi_sandbox_missing_plan_returns_external_tool_result(tmp_path: Path):
    result = run_dpabi_sandbox_smoke(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "DPABI"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )

    assert result["ok"] is False
    assert result["external_tool_result"]["tool_name"] == "dpabi.sandbox_smoke"
    assert "Missing DPABI run plan" in " ".join(result["external_tool_result"]["errors"])


def _write_dpabi_run_plan(tmp_path: Path) -> None:
    plan = tmp_path / "work" / "dpabi" / "dpabi_run_plan.json"
    plan.parent.mkdir(parents=True)
    plan.write_text(
        json.dumps({"ok": True, "approved": False, "steps": [{"function_name": "y_Smooth"}]}),
        encoding="utf-8",
    )


def _fake_dpabi_sandbox_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int = 0,
    write_result: bool = True,
) -> None:
    def fake_run(cmd: list[str], stdout=None, stderr=None, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        if stdout:
            stdout.write("fake sandbox stdout\n")
        if stderr:
            stderr.write("fake sandbox stderr\n")
        joined = " ".join(str(part) for part in cmd)
        match = re.search(r"'([^']*dpabi_sandbox_smoke_result\.json)'", joined)
        if write_result and match:
            result_json = Path(match.group(1))
            result_json.parent.mkdir(parents=True, exist_ok=True)
            result_json.write_text(
                json.dumps({
                    "ok": returncode == 0,
                    "outputs": [str(result_json.parent / "sandbox_marker.txt")],
                    "warnings": [],
                    "errors": [],
                    "metrics": {"smoke": "ok"},
                }),
                encoding="utf-8",
            )
            (result_json.parent / "sandbox_marker.txt").write_text("ok", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


def test_dpabi_sandbox_fake_matlab_success_has_external_tool_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_dpabi_run_plan(tmp_path)
    _fake_dpabi_sandbox_subprocess(monkeypatch, returncode=0, write_result=True)

    result = run_dpabi_sandbox_smoke(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "DPABI"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )

    assert result["ok"] is True
    assert result["external_tool_result"]["returncode"] == 0
    assert Path(result["external_tool_result"]["logs"]["stdout"]).exists()


def test_dpabi_sandbox_missing_result_json_fails_with_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_dpabi_run_plan(tmp_path)
    _fake_dpabi_sandbox_subprocess(monkeypatch, returncode=0, write_result=False)

    result = run_dpabi_sandbox_smoke(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "DPABI"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )

    assert result["ok"] is False
    assert "did not produce result JSON" in " ".join(result["external_tool_result"]["errors"])
    assert Path(result["external_tool_result"]["logs"]["stderr"]).exists()


def test_dpabi_sandbox_nonzero_returncode_is_diagnosed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_dpabi_run_plan(tmp_path)
    _fake_dpabi_sandbox_subprocess(monkeypatch, returncode=5, write_result=True)

    result = run_dpabi_sandbox_smoke(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "DPABI"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )

    assert result["ok"] is False
    assert result["external_tool_result"]["returncode"] == 5
    assert "MATLAB exited with return code 5" in " ".join(result["external_tool_result"]["errors"])
