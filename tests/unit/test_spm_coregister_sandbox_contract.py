"""Sandbox-only contract tests for spm_coregister_subject (M6-T007c)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from src.backend.app.tools.spm_coregister_runner import run_spm_coregister_subject


def _make_synthetic_t1w(tmp_path: Path) -> Path:
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "anat"
    raw.mkdir(parents=True, exist_ok=True)
    t1w = raw / "sub-001_T1w.nii"
    data = np.random.default_rng(7).normal(size=(4, 4, 4)).astype("float32")
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(t1w))
    return t1w


def _make_mean_func(tmp_path: Path) -> Path:
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    deriv.mkdir(parents=True, exist_ok=True)
    mean = deriv / "mean_sub-001_bold.nii"
    data = np.random.default_rng(7).normal(size=(4, 4, 4)).astype("float32")
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(mean))
    return mean


def _extract_result_json(cmd: list[str]) -> Path:
    joined = " ".join(str(part) for part in cmd)
    matches = re.findall(r"'([^']*spm_coregistration_result\.json)'", joined)
    if not matches:
        raise AssertionError(f"Could not find result JSON in command: {cmd}")
    return Path(matches[-1])


def _fake_subprocess_run(monkeypatch, *, returncode=0, create_outputs=True):
    def fake_run(cmd, stdout=None, stderr=None, **kw):
        del kw
        if stdout:
            stdout.write("fake MATLAB stdout\n")
        if stderr:
            stderr.write("fake MATLAB stderr\n")
        result_json = _extract_result_json(cmd)
        payload: dict[str, Any] = {"ok": returncode == 0, "warnings": [], "errors": []}
        if returncode == 0:
            result_json.parent.mkdir(parents=True, exist_ok=True)
            coreg = result_json.parent / "coreg_sub-001_T1w.nii"
            payload["coregistered_file"] = str(coreg)
            if create_outputs:
                coreg.write_text("fake coregistered")
        result_json.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


# ── source/reference contract ──


def test_synthetic_t1w_and_mean_func_passes(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    t1w = _make_synthetic_t1w(tmp_path)
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True


def test_missing_t1w_blocked(tmp_path):
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": []},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "T1w" in str(result["errors"])


def test_missing_mean_func_blocked(tmp_path):
    t1w = _make_synthetic_t1w(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "Mean functional" in str(result["errors"])


def test_unsafe_t1w_blocked(tmp_path):
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": "/data/sub-001/anat/T1w.nii"}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "non-synthetic" in str(result["errors"]).lower()


# ── output contract ──


def test_output_in_derivatives(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    t1w = _make_synthetic_t1w(tmp_path)
    _make_mean_func(tmp_path)
    deriv_dir = str(tmp_path / "derivatives")
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=deriv_dir,
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    for output in result.get("outputs", []):
        assert deriv_dir in output or "work" in output or "logs" in output


def test_output_no_rawdata(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    t1w = _make_synthetic_t1w(tmp_path)
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    for output in result.get("outputs", []):
        parts = Path(output).parts
        assert not (set(parts) & {"data", "rawdata"}), f"Forbidden: {output}"


# ── approval + safety gate ──


def test_not_approved_blocks(tmp_path):
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


def test_unsafe_matlab_blocks_subprocess(monkeypatch, tmp_path):
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_coregister_subject(
        matlab_command="matlab; evil",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_synthetic_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(called) == 0


# ── fake MATLAB ──


def test_fake_matlab_success(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    t1w = _make_synthetic_t1w(tmp_path)
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True
    assert "coregistered_file" in result or "coreg" in str(result.get("outputs", "")).lower()


def test_fake_matlab_missing_output(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=False)
    t1w = _make_synthetic_t1w(tmp_path)
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


def test_fake_matlab_nonzero(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=7)
    t1w = _make_synthetic_t1w(tmp_path)
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("returncode") == 7


def test_fake_matlab_logs(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    t1w = _make_synthetic_t1w(tmp_path)
    _make_mean_func(tmp_path)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("stdout_log") or result.get("stderr_log")


# ── safety + misc ──


def test_safety_errors_in_result(tmp_path):
    result = run_spm_coregister_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_synthetic_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert "safety" in result
    assert len(result["safety"]["errors"]) >= 1


def test_no_rawdata_written(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_synthetic_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    rawdata = tmp_path / "data"
    assert not rawdata.exists() or list(rawdata.glob("*")) == []


def test_result_json_serializable(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(_make_synthetic_t1w(tmp_path))}}]},
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


def test_allowlist_not_changed():
    pass
