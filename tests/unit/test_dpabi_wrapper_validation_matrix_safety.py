"""Tests for dpabi_wrapper_validation_matrix safety (M7-DPABI-T008b)."""

from __future__ import annotations

import json, subprocess
from pathlib import Path
import pytest
from src.backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix


def _make_dummy_file(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"functions":[]}')


# ── Python-only ──

def test_no_subprocess(monkeypatch):
    called = []
    def _track(*a, **kw): called.append(1); return subprocess.CompletedProcess([], 0)
    monkeypatch.setattr(subprocess, "run", _track)
    write_dpabi_wrapper_validation_matrix(work_dir="/tmp/w", report_dir="/tmp/r")
    assert len(called) == 0


# ── input scope ──

def test_safe_input_passes(tmp_path):
    wd = tmp_path / "work"; rd = tmp_path / "reports"; wd.mkdir(); rd.mkdir()
    sp = wd / "dpabi" / "dpabi_function_signatures.json"
    cp = wd / "dpabi" / "dpabi_wrapper_contracts.json"
    sr = wd / "dpabi" / "single_function_sandbox" / "dpabi_single_function_result.json"
    ss = rd / "dpabi" / "dpabi_subject_wrapper_summary.json"
    for p in [sp, cp, sr, ss]:
        _make_dummy_file(p)
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(wd), report_dir=str(rd),
        signatures_path=str(sp), contracts_path=str(cp),
        sandbox_result_path=str(sr), subject_wrapper_summary_path=str(ss),
    )
    assert result.get("ok") is not False or "matrix_json" in result


def test_path_traversal_input_blocked(tmp_path):
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(tmp_path), report_dir=str(tmp_path),
        signatures_path=str(tmp_path / ".." / "rawdata" / "sig.json"),
    )
    assert result["ok"] is False


def test_rawdata_input_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir()
    (raw / "sig.json").write_text("{}")
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(tmp_path), report_dir=str(tmp_path),
        signatures_path=str(raw / "sig.json"),
    )
    assert result["ok"] is False


# ── misc ──

def test_json_serializable(tmp_path):
    wd = tmp_path / "work"; wd.mkdir(); rd = tmp_path / "reports"; rd.mkdir()
    sp = wd / "dpabi" / "dpabi_function_signatures.json"; _make_dummy_file(sp)
    cp = wd / "dpabi" / "dpabi_wrapper_contracts.json"; _make_dummy_file(cp)
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(wd), report_dir=str(rd),
        signatures_path=str(sp), contracts_path=str(cp),
    )
    json.dumps(result, default=str)
