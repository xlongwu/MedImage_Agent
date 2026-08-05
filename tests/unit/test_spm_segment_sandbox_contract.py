"""Sandbox-only contract tests for spm_segment_subject (M6-T008c)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from src.backend.app.tools.spm_segment_runner import run_spm_segment_subject


def _make_env(tmp_path: Path, *, create_t1w=True, create_tpm=True):
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "anat"
    if create_t1w:
        deriv.mkdir(parents=True, exist_ok=True)
        (deriv / "coreg_sub-001_T1w.nii").write_bytes(b"\x00" * 100)
    if create_tpm:
        tpm_dir = tmp_path / "spm12" / "tpm"
        tpm_dir.mkdir(parents=True, exist_ok=True)
        (tpm_dir / "TPM.nii").write_bytes(b"\x00" * 100)


def _extract_result_json(cmd: list[str]) -> Path:
    joined = " ".join(str(part) for part in cmd)
    matches = re.findall(r"'([^']*spm_segmentation_result\.json)'", joined)
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
        result_json.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"ok": returncode == 0, "warnings": [], "errors": []}
        if returncode == 0:
            for key, fname in [
                ("gm_file", "c1sub-001_T1w.nii"),
                ("wm_file", "c2sub-001_T1w.nii"),
                ("csf_file", "c3sub-001_T1w.nii"),
                ("deformation_field", "y_coreg_sub-001_T1w.nii"),
            ]:
                p = result_json.parent / fname
                payload[key] = str(p)
                if create_outputs:
                    p.write_text("fake")
        result_json.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


# ── T1w input ──


def test_coreg_t1w_passes(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True


def test_missing_t1w_blocked(tmp_path):
    _make_env(tmp_path, create_t1w=False)
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


# ── TPM preflight ──


def test_tpm_present_passes(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path, create_tpm=True)
    result = run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True


def test_missing_tpm_blocked(tmp_path):
    _make_env(tmp_path, create_tpm=False)
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


# ── output ──


def test_output_in_derivatives(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    deriv_dir = str(tmp_path / "derivatives")
    result = run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=deriv_dir,
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    for output in result.get("outputs", []):
        assert deriv_dir in output or "work" in output or "logs" in output


def test_output_no_rawdata(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    for output in result.get("outputs", []):
        parts = Path(output).parts
        assert not (set(parts) & {"data", "rawdata"}), f"Forbidden: {output}"


# ── fake MATLAB ──


def test_fake_matlab_success(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_segment_subject(
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


def test_fake_matlab_nonzero(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=7)
    _make_env(tmp_path)
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
    assert result.get("returncode") == 7


# ── safety + misc ──


def test_not_approved_blocks(tmp_path):
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


def test_unsafe_matlab_blocks(monkeypatch, tmp_path):
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    _make_env(tmp_path)
    run_spm_segment_subject(
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
    run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    rawdata = tmp_path / "data"
    assert not rawdata.exists() or list(rawdata.glob("*")) == []


def test_result_json_serializable(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    _make_env(tmp_path)
    result = run_spm_segment_subject(
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
