"""Tests for dpabi_subject_smooth safety preflight (M7-DPABI-T006b)."""

from __future__ import annotations

import json
import subprocess

from src.backend.app.tools.dpabi_subject_wrapper import run_dpabi_subject_smooth


def _make_synthetic_input(tmp_path):
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "sub-001_bold.nii").write_bytes(b"\x00" * 100)
    return str(raw / "sub-001_bold.nii")


# ── safety preflight ──


def test_matlab_with_args_blocked(tmp_path):
    result = run_dpabi_subject_smooth(
        matlab_command="matlab -r evil",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold="x",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_dpabi_subject_smooth(
        matlab_command="python",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold="x",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0


def test_approved_false_blocks(tmp_path):
    result = run_dpabi_subject_smooth(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold="x",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
    )
    assert result["ok"] is False


# ── FWHM ──


def test_valid_fwhm_passes(tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="python",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold=input_nii,
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[8, 8, 8],
    )
    # Should fail at contracts (not FWHM), confirming FWHM passed
    assert result.get("stage") != "fwhm_preflight"


def test_fwhm_zero_blocked(tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold=input_nii,
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[0, 6, 6],
    )
    assert result["ok"] is False
    assert result.get("stage") == "fwhm_preflight"


def test_fwhm_wrong_length_blocked(tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold=input_nii,
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[6, 6],
    )
    assert result["ok"] is False
    assert result.get("stage") == "fwhm_preflight"


def test_fwhm_negative_blocked(tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold=input_nii,
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[-1, 6, 6],
    )
    assert result["ok"] is False


def test_fwhm_too_large_blocked(tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    result = run_dpabi_subject_smooth(
        matlab_command="matlab",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold=input_nii,
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[100, 6, 6],
    )
    assert result["ok"] is False


# ── misc ──


def test_json_serializable(tmp_path):
    result = run_dpabi_subject_smooth(
        matlab_command="python",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold="x",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


def test_no_real_matlab(monkeypatch, tmp_path):
    input_nii = _make_synthetic_input(tmp_path)
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_dpabi_subject_smooth(
        matlab_command="python",
        dpabi_dir=str(tmp_path / "dpabi"),
        subject_id="sub-001",
        input_bold=input_nii,
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0
