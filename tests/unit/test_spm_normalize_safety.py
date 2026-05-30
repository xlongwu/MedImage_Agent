"""Tests for spm_normalize_subject safety preflight (M6-T009b)."""

from __future__ import annotations

import json, subprocess
from pathlib import Path
import pytest
from src.backend.app.tools.spm_normalize_runner import run_spm_normalize_subject


def _make_env(tmp_path, *, create_def=True, create_func=True):
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001"
    if create_def:
        (deriv / "anat").mkdir(parents=True, exist_ok=True)
        (deriv / "anat" / "y_coreg_sub-001_T1w.nii").write_bytes(b"\x00" * 100)
    if create_func:
        (deriv / "func").mkdir(parents=True, exist_ok=True)
        (deriv / "func" / "rasub-001_bold.nii").write_bytes(b"\x00" * 100)


# ── safety preflight ──

def test_matlab_with_args_blocked(tmp_path):
    _make_env(tmp_path)
    result = run_spm_normalize_subject(
        matlab_command="matlab -r evil", spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False
    assert result.get("stage") == "matlab_safety_preflight"


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    _make_env(tmp_path)
    called = []
    def _track(*a, **kw): called.append(1); return subprocess.CompletedProcess([], 0)
    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_normalize_subject(
        matlab_command="python", spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert len(called) == 0


# ── def field + functional ──

def test_missing_def_field_blocked(tmp_path):
    _make_env(tmp_path, create_def=False)
    result = run_spm_normalize_subject(
        matlab_command="matlab", spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False
    assert "deformation field" in str(result["errors"])


def test_missing_func_blocked(tmp_path):
    _make_env(tmp_path, create_func=False)
    result = run_spm_normalize_subject(
        matlab_command="matlab", spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result["ok"] is False
    assert "functional" in str(result["errors"]).lower()


def test_approved_false_blocks(tmp_path):
    result = run_spm_normalize_subject(
        matlab_command="matlab", spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=False,
    )
    assert result["ok"] is False


# ── misc ──

def test_result_json_serializable(tmp_path):
    result = run_spm_normalize_subject(
        matlab_command="python", spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    json.dumps(result, default=str)


def test_no_real_matlab(tmp_path):
    result = run_spm_normalize_subject(
        matlab_command="python", spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001", derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), approved=True,
    )
    assert result.get("matlab_called") is False
