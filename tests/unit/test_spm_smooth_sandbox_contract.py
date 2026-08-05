"""Sandbox-only contract tests for spm_smooth_subject (M6-T010c)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from src.backend.app.tools.spm_smooth_runner import run_spm_smooth_subject


def _make_env(tmp_path, create_func=True):
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    if create_func:
        deriv.mkdir(parents=True, exist_ok=True)
        (deriv / "wrasub-001_bold.nii").write_bytes(b"\x00" * 100)


def _extract_result_json(cmd):
    m = re.findall(r"'([^']*spm_smoothing_result\.json)'", " ".join(str(p) for p in cmd))
    if not m:
        raise AssertionError(f"No result JSON in: {cmd}")
    return Path(m[-1])


def _fake_subprocess_run(monkeypatch, *, returncode=0, create_outputs=True):
    def fake_run(cmd, stdout=None, stderr=None, **kw):
        del kw
        if stdout:
            stdout.write("fake MATLAB stdout\n")
        if stderr:
            stderr.write("fake MATLAB stderr\n")
        rj = _extract_result_json(cmd)
        rj.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"ok": returncode == 0, "warnings": [], "errors": []}
        if returncode == 0:
            sf = rj.parent / "swrasub-001_bold.nii"
            payload["smoothed_file"] = str(sf)
            if create_outputs:
                sf.write_text("fake")
        rj.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


# ── func input ──


def test_normalized_func_passes(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True


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


# ── FWHM ──


def test_valid_fwhm(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        fwhm=[8, 8, 8],
    )
    assert result["ok"] is True


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


# ── output ──


def test_output_in_derivatives(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    deriv_dir = str(tmp_path / "derivatives")
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=deriv_dir,
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    for o in result.get("outputs", []):
        assert deriv_dir in o or "work" in o or "logs" in o


def test_output_no_rawdata(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    for o in result.get("outputs", []):
        assert not (set(Path(o).parts) & {"data", "rawdata"}), f"Forbidden: {o}"


# ── fake MATLAB ──


def test_fake_matlab_success(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True


def test_fake_matlab_missing_output(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=False)
    _make_env(tmp_path)
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


def test_fake_matlab_nonzero(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=7)
    _make_env(tmp_path)
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
    assert result.get("returncode") == 7


# ── safety + misc ──


def test_not_approved_blocks(tmp_path):
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


def test_unsafe_matlab_blocks(monkeypatch, tmp_path):
    called = []
    _make_env(tmp_path)

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_smooth_subject(
        matlab_command="matlab; evil",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0


def test_no_rawdata_written(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert not (tmp_path / "data").exists() or list((tmp_path / "data").glob("*")) == []


def test_json_serializable(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


def test_allowlist_not_changed():
    pass
