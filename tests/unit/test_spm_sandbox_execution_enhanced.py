"""Enhanced safety tests for SPM sandbox execution — Phase 5E-Complete."""
from __future__ import annotations
from pathlib import Path
import pytest


def _make_bold_input(tmp_path: Path) -> Path:
    cb = tmp_path / "converted_bids"
    sub = cb / "sub-001" / "func"; sub.mkdir(parents=True)
    (sub / "sub-001_task-rest_bold.nii.gz").write_text("fake BOLD")
    (sub / "sub-001_task-rest_bold.json").write_text('{"RepetitionTime":2.0}')
    return cb


def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_spm_execution.mock_store", store)
    return store


_ALL = {"MEDIMAGE_MATLAB_ENABLED": "1", "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_SPM_PREPROCESSING": "1"}


def _make_dry_run(tmp_path, run_id="pp-test", dry_id="dr-test"):
    d = tmp_path / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id
    d.mkdir(parents=True)
    (d / "dry_run_manifest.json").write_text('{"status":"dry_run_preview"}')
    return d


def test_batch_script_no_rawdata_reference(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); cb = _make_bold_input(tmp_path)
    _make_dry_run(tmp_path)
    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", lambda *a, **kw: type("R",(),{"returncode":0,"stdout":"ok","stderr":""})())
    from src.backend.app.schemas.preprocessing_spm_execution import SpmSandboxExecutionRequest
    from src.backend.app.services.preprocessing_spm_execution import run_sandbox_spm_execution
    req = SpmSandboxExecutionRequest(dry_run_id="dr-test", preprocessing_input_dir=str(cb), confirm_sandbox_copy=True)
    result = run_sandbox_spm_execution("brain-tumor-study", "pp-test", req, env=_ALL, project_dir=str(tmp_path))
    batch = Path(result.batch_script_path).read_text()
    # Check batch does not reference original input path (sandbox copies only)
    assert str(cb) not in batch, f"Original converted path leaked into batch: {batch[:200]}"


def test_batch_script_sandbox_paths_only(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); cb = _make_bold_input(tmp_path)
    _make_dry_run(tmp_path)
    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", lambda *a, **kw: type("R",(),{"returncode":0,"stdout":"ok","stderr":""})())
    from src.backend.app.schemas.preprocessing_spm_execution import SpmSandboxExecutionRequest
    from src.backend.app.services.preprocessing_spm_execution import run_sandbox_spm_execution
    req = SpmSandboxExecutionRequest(dry_run_id="dr-test", preprocessing_input_dir=str(cb), confirm_sandbox_copy=True)
    result = run_sandbox_spm_execution("brain-tumor-study", "pp-test", req, env=_ALL, project_dir=str(tmp_path))
    batch = Path(result.batch_script_path).read_text()
    assert "sandbox_input" in batch


def test_command_template_no_shell(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); cb = _make_bold_input(tmp_path)
    _make_dry_run(tmp_path)
    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", lambda *a, **kw: type("R",(),{"returncode":0,"stdout":"ok","stderr":""})())
    from src.backend.app.schemas.preprocessing_spm_execution import SpmSandboxExecutionRequest
    from src.backend.app.services.preprocessing_spm_execution import run_sandbox_spm_execution
    req = SpmSandboxExecutionRequest(dry_run_id="dr-test", preprocessing_input_dir=str(cb), confirm_sandbox_copy=True)
    result = run_sandbox_spm_execution("brain-tumor-study", "pp-test", req, env=_ALL, project_dir=str(tmp_path))
    import json
    tmpl = json.loads(Path(result.command_template_path).read_text())
    assert tmpl["shell"] is False
    assert "shell=True" not in str(tmpl)


def test_disabled_no_copy(tmp_path, monkeypatch):
    """When env flags missing, no files should be copied."""
    _setup(tmp_path, monkeypatch); cb = _make_bold_input(tmp_path)
    from src.backend.app.schemas.preprocessing_spm_execution import SpmSandboxExecutionRequest
    from src.backend.app.services.preprocessing_spm_execution import run_sandbox_spm_execution
    req = SpmSandboxExecutionRequest(dry_run_id="dr-test", preprocessing_input_dir=str(cb))
    result = run_sandbox_spm_execution("brain-tumor-study", "pp-test", req, env={}, project_dir=str(tmp_path))
    assert result.status == "disabled"
    assert result.execution_dir == ""  # No directory created
