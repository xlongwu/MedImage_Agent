"""Tests for dpabi_sandbox_smoke_run safety preflight (M7-DPABI-T004b)."""

from __future__ import annotations

import json, subprocess
from pathlib import Path
import pytest
from src.backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke


# ── safety ──

def test_matlab_with_args_blocked(tmp_path):
    result = run_dpabi_sandbox_smoke(
        matlab_command="matlab -r evil", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False; assert result.get("stage") == "dpabi_runtime_preflight"


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    called = []
    def _track(*a, **kw): called.append(1); return subprocess.CompletedProcess([], 0)
    monkeypatch.setattr(subprocess, "run", _track)
    run_dpabi_sandbox_smoke(
        matlab_command="python", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert len(called) == 0


def test_approved_false_blocks(tmp_path):
    result = run_dpabi_sandbox_smoke(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=False,
    )
    assert result["ok"] is False


def test_dpabi_dir_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir()
    result = run_dpabi_sandbox_smoke(
        matlab_command="matlab", dpabi_dir=str(raw),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False


def test_json_serializable(tmp_path):
    result = run_dpabi_sandbox_smoke(
        matlab_command="python", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    json.dumps(result, default=str)


def test_no_real_matlab(tmp_path):
    result = run_dpabi_sandbox_smoke(
        matlab_command="python", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result.get("matlab_called") is False
