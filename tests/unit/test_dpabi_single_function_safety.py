"""Tests for dpabi_single_function_sandbox safety preflight (M7-DPABI-T005b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox


def _write_contracts(tmp_path):
    work = Path(tmp_path) / "work" / "dpabi"
    work.mkdir(parents=True, exist_ok=True)
    (work / "dpabi_wrapper_contracts.json").write_text(
        '{"contracts":[{"function_name":"y_Smooth","wrapper_candidate":true}]}'
    )


# ── safety preflight ──


def test_matlab_with_args_blocked(tmp_path):
    _write_contracts(tmp_path)
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab -r evil",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("stage") == "dpabi_runtime_preflight"


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_dpabi_single_function_sandbox(
        matlab_command="python",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0


def test_approved_false_blocks(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
    )
    assert result["ok"] is False


# ── function allowlist ──


def test_allowed_function_y_smooth(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        function_name="y_Smooth",
    )
    assert result["ok"] is False  # missing contracts, but not "function not allowlisted"
    assert "not allowlisted" not in str(result.get("errors", ""))


def test_forbidden_DPARSF_run_blocked(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        function_name="DPARSF_run",
    )
    assert result["ok"] is False
    assert "not allowlisted" in str(result["errors"])


def test_arbitrary_function_blocked(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        function_name="evil_eval",
    )
    assert result["ok"] is False
    assert "not allowlisted" in str(result["errors"])


def test_semicolon_function_blocked(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        function_name="y_Smooth;rm -rf /",
    )
    assert result["ok"] is False


# ── misc ──


def test_json_serializable(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="python",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


def test_no_real_matlab(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_dpabi_single_function_sandbox(
        matlab_command="python",
        dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0
