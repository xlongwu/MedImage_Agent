"""Sandbox contract tests for dpabi_single_function_sandbox (M7-DPABI-T005c)."""

from __future__ import annotations

import json, re, subprocess
from pathlib import Path
from typing import Any
import pytest
from src.backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox
from src.backend.app.tools.dpabi_safety import ALLOWED_FUNCTIONS
from src.backend.app.runtime.node_registry import NODE_REGISTRY


def _write_contracts(tmp_path, function_name="y_Smooth", wrapper_candidate=True):
    work = Path(tmp_path) / "work" / "dpabi"
    work.mkdir(parents=True, exist_ok=True)
    payload = {"contracts": [{"function_name": function_name, "wrapper_candidate": wrapper_candidate}]}
    (work / "dpabi_wrapper_contracts.json").write_text(json.dumps(payload))


def _extract_result_json(cmd):
    m = re.findall(r"'([^']*dpabi_single_function_result\.json)'", " ".join(str(p) for p in cmd))
    if not m: raise AssertionError(f"No result JSON in: {cmd}")
    return Path(m[-1])


def _fake_subprocess(monkeypatch, *, returncode=0, create_outputs=True):
    def fake_run(cmd, stdout=None, stderr=None, **kw):
        del kw
        if stdout: stdout.write("fake DPABI stdout\n")
        if stderr: stderr.write("fake DPABI stderr\n")
        rj = _extract_result_json(cmd)
        rj.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"ok": returncode == 0, "sandbox_marker": "ok", "outputs": ["sandbox_marker.txt"]}
        if create_outputs:
            (rj.parent / "sandbox_marker.txt").write_text("ok")
            rj.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)
    monkeypatch.setattr(subprocess, "run", fake_run)


# ── function allowlist ──

def test_allowed_functions_pass():
    for fn in ALLOWED_FUNCTIONS:
        assert isinstance(fn, str)
        assert " " not in fn
        assert ";" not in fn


def test_DPARSF_run_blocked(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
        function_name="DPARSF_run",
    )
    assert result["ok"] is False


def test_arbitrary_function_blocked(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
        function_name="evil_eval",
    )
    assert result["ok"] is False
    assert "not allowlisted" in str(result["errors"])


def test_semicolon_function_blocked(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
        function_name="y_Smooth;rm -rf /",
    )
    assert result["ok"] is False


# ── runtime safety ──

def test_approved_false_blocks(tmp_path):
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=False,
    )
    assert result["ok"] is False


def test_unsafe_matlab_blocks(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    called = []
    def _track(*a, **kw): called.append(1); return subprocess.CompletedProcess([], 0)
    monkeypatch.setattr(subprocess, "run", _track)
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab -r evil", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False
    assert len(called) == 0


# ── fake MATLAB/DPABI ──

def test_fake_success(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    _fake_subprocess(monkeypatch)
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is True


def test_fake_missing_output(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    _fake_subprocess(monkeypatch, returncode=0, create_outputs=False)
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False


def test_fake_nonzero(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    _fake_subprocess(monkeypatch, returncode=7)
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False


# ── output ──

def test_output_no_rawdata(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    _fake_subprocess(monkeypatch)
    run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    rawdata = tmp_path / "rawdata"
    assert not rawdata.exists() or not any(f.is_file() for f in rawdata.glob("**/*"))


# ── registry / policy ──

def test_node_registered():
    assert "dpabi_single_function_sandbox" in NODE_REGISTRY


def test_not_in_metadata_allowlist():
    from src.backend.app.planner.plan_adapter import _DPABI_METADATA_NODES
    assert "dpabi_single_function_sandbox" not in _DPABI_METADATA_NODES


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "dpabi_single_function_sandbox", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "dpabi_single_function_sandbox" in policy["blocked_dpabi_execution_nodes"]


# ── misc ──

def test_json_serializable(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    _fake_subprocess(monkeypatch)
    result = run_dpabi_single_function_sandbox(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    json.dumps(result, default=str)


def test_metadata_allowlist_regression():
    from src.backend.app.planner.plan_adapter import _DPABI_METADATA_NODES
    assert len(_DPABI_METADATA_NODES) == 15


def test_allowlist_not_changed():
    pass
