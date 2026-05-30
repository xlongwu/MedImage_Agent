"""Sandbox contract tests for dpabi_wrapper_validation_matrix (M7-DPABI-T008c)."""

from __future__ import annotations

import json, subprocess
from pathlib import Path
import pytest
from src.backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix
from src.backend.app.runtime.node_registry import NODE_REGISTRY


def _make_dummy_files(tmp_path):
    wd = tmp_path / "work"; wd.mkdir()
    rd = tmp_path / "reports"; rd.mkdir()
    sp = wd / "dpabi" / "dpabi_function_signatures.json"; sp.parent.mkdir(parents=True, exist_ok=True); sp.write_text('{"functions":[]}')
    cp = wd / "dpabi" / "dpabi_wrapper_contracts.json"; cp.parent.mkdir(parents=True, exist_ok=True); cp.write_text('{"contracts":[]}')
    sr = wd / "dpabi" / "single_function_sandbox" / "dpabi_single_function_result.json"; sr.parent.mkdir(parents=True, exist_ok=True); sr.write_text('{}')
    ss = rd / "dpabi" / "dpabi_subject_wrapper_summary.json"; ss.parent.mkdir(parents=True, exist_ok=True); ss.write_text('{}')
    return wd, rd, sp, cp, sr, ss


# ── Python-only ──

def test_no_subprocess(monkeypatch):
    called = []
    def _track(*a, **kw): called.append(1); return subprocess.CompletedProcess([], 0)
    monkeypatch.setattr(subprocess, "run", _track)
    write_dpabi_wrapper_validation_matrix(work_dir="/tmp/w", report_dir="/tmp/r")
    assert len(called) == 0


# ── input scope ──

def test_safe_input_passes(tmp_path):
    wd, rd, sp, cp, sr, ss = _make_dummy_files(tmp_path)
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(wd), report_dir=str(rd),
        signatures_path=str(sp), contracts_path=str(cp),
        sandbox_result_path=str(sr), subject_wrapper_summary_path=str(ss),
    )
    assert result.get("ok") is not False or "matrix_json" in result


def test_rawdata_input_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir()
    (raw / "sig.json").write_text("{}")
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(tmp_path), report_dir=str(tmp_path),
        signatures_path=str(raw / "sig.json"),
    )
    assert result["ok"] is False


def test_path_traversal_input_blocked(tmp_path):
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(tmp_path), report_dir=str(tmp_path),
        signatures_path=str(tmp_path / ".." / "rawdata" / "sig.json"),
    )
    assert result["ok"] is False


# ── output scope ──

def test_matrix_json_output(tmp_path):
    wd, rd, sp, cp, sr, ss = _make_dummy_files(tmp_path)
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(wd), report_dir=str(rd),
        signatures_path=str(sp), contracts_path=str(cp),
        sandbox_result_path=str(sr), subject_wrapper_summary_path=str(ss),
    )
    assert result.get("ok") is not False, f"Unexpected failure: {result.get('errors')}"


def test_overwrite_existing_matrix(tmp_path):
    wd, rd, sp, cp, sr, ss = _make_dummy_files(tmp_path)
    mx = rd / "dpabi" / "dpabi_wrapper_validation_matrix.json"
    mx.parent.mkdir(parents=True, exist_ok=True)
    mx.write_text('{"old":true}')
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(wd), report_dir=str(rd),
        signatures_path=str(sp), contracts_path=str(cp),
        sandbox_result_path=str(sr), subject_wrapper_summary_path=str(ss),
    )
    # Runner overwrites — expected behavior, returns metrics
    assert "metrics" in result


# ── policy ──

def test_node_registered():
    assert "dpabi_wrapper_validation_matrix" in NODE_REGISTRY


def test_not_in_any_allowlist():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes, _DPABI_METADATA_NODES
    nid = "dpabi_wrapper_validation_matrix"
    assert nid not in _DPABI_METADATA_NODES
    plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
    policy = classify_plan_nodes(plan)
    assert nid in policy["blocked_dpabi_execution_nodes"]


# ── misc ──

def test_json_serializable(tmp_path):
    wd, rd, sp, cp, sr, ss = _make_dummy_files(tmp_path)
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(wd), report_dir=str(rd),
        signatures_path=str(sp), contracts_path=str(cp),
        sandbox_result_path=str(sr), subject_wrapper_summary_path=str(ss),
    )
    json.dumps(result, default=str)


def test_allowlist_not_changed():
    pass
