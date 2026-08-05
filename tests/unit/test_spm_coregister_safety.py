"""Tests for spm_coregister_subject safety preflight (M6-T007b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.backend.app.tools.spm_coregister_runner import run_spm_coregister_subject


def _make_t1w(tmp_path: Path) -> Path:
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "anat"
    raw.mkdir(parents=True, exist_ok=True)
    t1w = raw / "sub-001_T1w.nii"
    t1w.write_bytes(b"\x00" * 100)
    return t1w


def _make_mean_func(tmp_path: Path) -> Path:
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    deriv.mkdir(parents=True, exist_ok=True)
    mean = deriv / "mean_sub-001_bold.nii"
    mean.write_bytes(b"\x00" * 100)
    return mean


# ── 1. unsafe matlab_command blocked ──


def test_matlab_with_args_blocked(tmp_path):
    _make_t1w(tmp_path)
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab -r evil",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("stage") == "matlab_safety_preflight"


# ── 2. approved=false blocked ──


def test_approved_false_blocks(tmp_path):
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": []},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
    )
    assert result["ok"] is False
    assert "requires approved=true" in str(result["errors"])


# ── 3. missing T1w blocked ──


def test_missing_t1w_blocked(tmp_path):
    result = run_spm_coregister_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": []},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 4. safety error no subprocess ──


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_coregister_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0


# ── 5. safety errors in result ──


def test_safety_errors_in_result(tmp_path):
    result = run_spm_coregister_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert "safety" in result
    assert len(result["safety"]["errors"]) >= 1


# ── 6. spm_dir rawdata blocked ──


def test_spm_dir_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(raw),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 7. JSON serializable ──


def test_result_json_serializable(tmp_path):
    result = run_spm_coregister_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


# ── 8. no real MATLAB ──


def test_no_real_matlab(tmp_path):
    result = run_spm_coregister_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("matlab_called") is False
