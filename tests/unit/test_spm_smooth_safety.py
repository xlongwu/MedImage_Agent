"""Tests for spm_smooth_subject safety preflight (M6-T010b)."""

from __future__ import annotations

import json
import subprocess

from src.backend.app.tools.spm_smooth_runner import run_spm_smooth_subject


def _make_env(tmp_path, create_func=True):
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    if create_func:
        deriv.mkdir(parents=True, exist_ok=True)
        (deriv / "wrasub-001_bold.nii").write_bytes(b"\x00" * 100)


# ── safety ──


def test_matlab_with_args_blocked(tmp_path):
    _make_env(tmp_path)
    result = run_spm_smooth_subject(
        matlab_command="matlab -r evil",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("stage") == "matlab_safety_preflight"


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    _make_env(tmp_path)
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_smooth_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0


# ── FWHM ──


def test_valid_fwhm_passes(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[8, 8, 8],
    )
    assert result.get("stage") != "fwhm_preflight"  # FWHM check passed


def test_fwhm_wrong_length_blocked(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[6, 6],
    )
    assert result["ok"] is False
    assert result.get("stage") == "fwhm_preflight"


def test_fwhm_zero_blocked(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[0, 6, 6],
    )
    assert result["ok"] is False
    assert result.get("stage") == "fwhm_preflight"


def test_fwhm_negative_blocked(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[-1, 6, 6],
    )
    assert result["ok"] is False


def test_fwhm_too_large_blocked(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[100, 6, 6],
    )
    assert result["ok"] is False


# ── func input ──


def test_missing_func_blocked(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "functional" in str(result["errors"]).lower()


def test_approved_false_blocks(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
    )
    assert result["ok"] is False


# ── misc ──


def test_json_serializable(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


def test_no_real_matlab(tmp_path):
    result = run_spm_smooth_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("matlab_called") is False
