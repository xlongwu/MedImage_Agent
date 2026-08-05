"""Tests for spm_segment_subject safety preflight (M6-T008b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.backend.app.tools.spm_segment_runner import run_spm_segment_subject


def _make_segment_env(tmp_path: Path, create_tpm: bool = True):
    """Set up coreg T1w + optional TPM for segment tests."""
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "anat"
    deriv.mkdir(parents=True, exist_ok=True)
    t1w = deriv / "coreg_sub-001_T1w.nii"
    t1w.write_bytes(b"\x00" * 100)
    if create_tpm:
        tpm_dir = tmp_path / "spm12" / "tpm"
        tpm_dir.mkdir(parents=True, exist_ok=True)
        (tpm_dir / "TPM.nii").write_bytes(b"\x00" * 100)
    return tmp_path


# ── safety preflight ──


def test_matlab_with_args_blocked(tmp_path):
    _make_segment_env(tmp_path)
    result = run_spm_segment_subject(
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
    _make_segment_env(tmp_path)
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_segment_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0


# ── TPM preflight ──


def test_missing_tpm_blocked(tmp_path):
    _make_segment_env(tmp_path, create_tpm=False)
    result = run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("stage") == "tpm_preflight"


def test_tpm_present_passes(tmp_path):
    _make_segment_env(tmp_path, create_tpm=True)
    result = run_spm_segment_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    # Fails at safety (python), not TPM — meaning TPM check passed
    assert result.get("stage") != "tpm_preflight"


# ── T1w + approval ──


def test_missing_t1w_blocked(tmp_path):
    # TPM check runs before T1w check — need TPM present first
    _make_segment_env(tmp_path, create_tpm=True)
    # Delete the T1w after TPM is created
    t1w = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "anat" / "coreg_sub-001_T1w.nii"
    t1w.unlink()
    result = run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "coregistered T1w" in str(result["errors"])


def test_approved_false_blocks(tmp_path):
    result = run_spm_segment_subject(
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


def test_result_json_serializable(tmp_path):
    result = run_spm_segment_subject(
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
    result = run_spm_segment_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("matlab_called") is False
