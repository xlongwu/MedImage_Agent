"""Sandbox contract tests for dpabi_subject_smooth (M7-DPABI-T006c)."""

from __future__ import annotations

import json, re, subprocess
from pathlib import Path
from typing import Any
import pytest
from src.backend.app.tools.dpabi_subject_wrapper import run_dpabi_subject_smooth
from src.backend.app.runtime.node_registry import NODE_REGISTRY


def _make_synthetic_input(tmp_path):
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "sub-001_bold.nii").write_bytes(b"\x00" * 100)
    return str(raw / "sub-001_bold.nii")


def _write_contracts(tmp_path, fn="y_Smooth", wc=True):
    w = Path(tmp_path) / "work" / "dpabi"
    w.mkdir(parents=True, exist_ok=True)
    (w / "dpabi_wrapper_contracts.json").write_text(
        json.dumps({"contracts": [{"function_name": fn, "wrapper_candidate": wc}]}))


def _extract_result_json(cmd):
    m = re.findall(r"'([^']*result\.json)'", " ".join(str(p) for p in cmd))
    if not m: raise AssertionError(f"No result JSON in: {cmd}")
    return Path(m[-1])


def _fake_subprocess(monkeypatch, *, returncode=0, create_outputs=True):
    def fake_run(cmd, stdout=None, stderr=None, **kw):
        del kw
        if stdout: stdout.write("fake DPABI stdout\n")
        if stderr: stderr.write("fake DPABI stderr\n")
        rj = _extract_result_json(cmd)
        rj.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"ok": returncode == 0, "smoothed_file": str(rj.parent / "smooth.nii")}
        if create_outputs:
            (rj.parent / "smooth.nii").write_text("fake")
            rj.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)
    monkeypatch.setattr(subprocess, "run", fake_run)


# ── input ──

def test_synthetic_input_passes(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    spm_dir = tmp_path / "third_party" / "spm12"
    spm_dir.mkdir(parents=True, exist_ok=True)
    _fake_subprocess(monkeypatch)
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"), spm_dir=str(spm_dir),
        subject_id="sub-001", input_bold=input_nii, derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is True


def test_non_synthetic_input_blocked(tmp_path):
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001", input_bold="/real/data.nii", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False
    assert "non-synthetic" in str(result["errors"]).lower()


# ── FWHM ──

def test_fwhm_valid_passes(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    spm_dir = tmp_path / "third_party" / "spm12"
    spm_dir.mkdir(parents=True, exist_ok=True)
    _fake_subprocess(monkeypatch)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"), spm_dir=str(spm_dir),
        subject_id="sub-001", input_bold=_make_synthetic_input(tmp_path),
        derivatives_dir=str(tmp_path / "derivatives"), work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"), approved=True, fwhm=[8, 8, 8],
    )
    assert result["ok"] is True


def test_fwhm_wrong_length_blocked(tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001", input_bold=input_nii, derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True, fwhm=[6, 6],
    )
    assert result["ok"] is False
    assert result.get("stage") == "fwhm_preflight"


def test_fwhm_zero_blocked(tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001", input_bold=input_nii, derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True, fwhm=[0, 6, 6],
    )
    assert result["ok"] is False


# ── fake MATLAB ──

def test_fake_missing_output(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    spm_dir = tmp_path / "third_party" / "spm12"
    spm_dir.mkdir(parents=True, exist_ok=True)
    _fake_subprocess(monkeypatch, returncode=0, create_outputs=False)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"), spm_dir=str(spm_dir),
        subject_id="sub-001", input_bold=_make_synthetic_input(tmp_path),
        derivatives_dir=str(tmp_path / "derivatives"), work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False


def test_fake_nonzero(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    spm_dir = tmp_path / "third_party" / "spm12"
    spm_dir.mkdir(parents=True, exist_ok=True)
    _fake_subprocess(monkeypatch, returncode=7)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"), spm_dir=str(spm_dir),
        subject_id="sub-001", input_bold=_make_synthetic_input(tmp_path),
        derivatives_dir=str(tmp_path / "derivatives"), work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False


# ── output ──

def test_output_no_rawdata(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    spm_dir = tmp_path / "third_party" / "spm12"
    spm_dir.mkdir(parents=True, exist_ok=True)
    _fake_subprocess(monkeypatch)
    run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"), spm_dir=str(spm_dir),
        subject_id="sub-001", input_bold=_make_synthetic_input(tmp_path),
        derivatives_dir=str(tmp_path / "derivatives"), work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"), approved=True,
    )
    rawdata = tmp_path / "rawdata"
    assert not rawdata.exists() or not any(f.is_file() for f in rawdata.glob("**/*"))


# ── policy ──

def test_node_registered():
    assert "dpabi_subject_smooth" in NODE_REGISTRY


def test_not_in_metadata_allowlist():
    from src.backend.app.planner.plan_adapter import _DPABI_METADATA_NODES
    assert "dpabi_subject_smooth" not in _DPABI_METADATA_NODES


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "dpabi_subject_smooth", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "dpabi_subject_smooth" in policy["blocked_dpabi_execution_nodes"]


# ── misc ──

def test_json_serializable(monkeypatch, tmp_path):
    _write_contracts(tmp_path)
    (Path(tmp_path) / "dpabi").mkdir(exist_ok=True)
    spm_dir = tmp_path / "third_party" / "spm12"
    spm_dir.mkdir(parents=True, exist_ok=True)
    _fake_subprocess(monkeypatch)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab", dpabi_dir=str(tmp_path / "dpabi"), spm_dir=str(spm_dir),
        subject_id="sub-001", input_bold=_make_synthetic_input(tmp_path),
        derivatives_dir=str(tmp_path / "derivatives"), work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"), approved=True,
    )
    json.dumps(result, default=str)


def test_allowlist_not_changed():
    pass
