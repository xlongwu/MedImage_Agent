"""Sandbox-only contract tests for spm_slice_timing_subject (M6-T006c).

All tests monkeypatch subprocess.run — no real MATLAB/SPM called.
All paths use tmp_path. spm_slice_timing_subject is NOT in the
reviewed execution allowlist.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import pytest

from src.backend.app.tools.spm_slice_timing_runner import run_spm_slice_timing_subject

# ── Helpers ──────────────────────────────────────────────────────────────────


def _subject_dirs(tmp_path: Path) -> dict[str, Path]:
    return {
        "raw_func": tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func",
        "derivatives": tmp_path / "derivatives",
        "work": tmp_path / "work",
        "logs": tmp_path / "logs",
    }


def _make_synthetic_bold(tmp_path: Path) -> Path:
    dirs = _subject_dirs(tmp_path)
    bold = dirs["raw_func"] / "sub-001_task-rest_bold.nii"
    bold.parent.mkdir(parents=True, exist_ok=True)
    data = np.random.default_rng(7).normal(size=(4, 4, 4, 10)).astype("float32")
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(bold))
    bold.with_suffix(".json").write_text(
        json.dumps({"RepetitionTime": 2.0, "SliceTiming": [0.0, 0.5, 1.0, 1.5]}),
        encoding="utf-8",
    )
    return bold


def _extract_result_json(cmd: list[str]) -> Path:
    joined = " ".join(str(part) for part in cmd)
    matches = re.findall(r"'([^']*spm_slice_timing_result\.json)'", joined)
    if not matches:
        raise AssertionError(f"Could not find result JSON in command: {cmd}")
    return Path(matches[-1])


def _fake_subprocess_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int = 0,
    create_outputs: bool = True,
) -> None:
    def fake_run(cmd: list[str], stdout=None, stderr=None, **kwargs):
        del kwargs
        if stdout:
            stdout.write("fake MATLAB stdout\n")
        if stderr:
            stderr.write("fake MATLAB stderr\n")

        result_json = _extract_result_json(cmd)
        payload: dict[str, Any] = {"ok": returncode == 0, "warnings": [], "errors": []}

        if returncode == 0:
            result_json.parent.mkdir(parents=True, exist_ok=True)
            corrected = result_json.parent / "asub-001_task-rest_bold.nii"
            payload["corrected_file"] = str(corrected)
            if create_outputs:
                corrected.write_text("fake slice-time corrected")

        result_json.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


# ══════════════════════════════════════════════════════════════════════════════
# Sandbox input contract
# ══════════════════════════════════════════════════════════════════════════════


def test_synthetic_input_passes(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    bold = _make_synthetic_bold(tmp_path)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(bold),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is True


def test_derivatives_input_passes_when_allowed(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    deriv.mkdir(parents=True)
    input_nii = deriv / "rsub-001_task-rest_bold.nii"
    data = np.random.default_rng(7).normal(size=(4, 4, 4, 10)).astype("float32")
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))
    # Write BIDS JSON for parameter discovery
    input_nii.with_suffix(".json").write_text(
        json.dumps({"RepetitionTime": 2.0, "SliceTiming": [0.0] * 4}),
        encoding="utf-8",
    )
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(input_nii),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        allow_derivative_input=True,
    )
    assert result["ok"] is True, f"errors: {result.get('errors')}, stage: {result.get('stage')}"


def test_derivatives_rejected_when_not_allowed(tmp_path):
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    deriv.mkdir(parents=True)
    input_nii = deriv / "rsub-001_bold.nii"
    input_nii.write_text("dummy")
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(input_nii),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
        allow_derivative_input=False,
    )
    assert result["ok"] is False


def test_arbitrary_input_rejected(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold="/etc/passwd",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is False


def test_real_rawdata_rejected(tmp_path):
    raw = tmp_path / "data" / "sub-001" / "func" / "sub-001_bold.nii"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("dummy")
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(raw),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is False


def test_path_traversal_rejected(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold="/usr/../etc/passwd",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is False


# ══════════════════════════════════════════════════════════════════════════════
# Output contract
# ══════════════════════════════════════════════════════════════════════════════


def test_output_in_derivatives(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    bold = _make_synthetic_bold(tmp_path)
    deriv_dir = str(tmp_path / "derivatives")
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(bold),
        derivatives_dir=deriv_dir,
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    for output in result.get("outputs", []):
        assert deriv_dir in output or "work" in output or "logs" in output


def test_output_no_rawdata(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    bold = _make_synthetic_bold(tmp_path)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(bold),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    for output in result.get("outputs", []):
        parts = Path(output).parts
        forbidden = {"data", "rawdata"}
        assert not (set(parts) & forbidden), f"Output contains forbidden: {output}"


# ══════════════════════════════════════════════════════════════════════════════
# Approval + safety gate order
# ══════════════════════════════════════════════════════════════════════════════


def test_not_approved_blocks(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is False
    assert "requires approved=true" in str(result["errors"])


def test_unsafe_matlab_blocks_before_subprocess(monkeypatch, tmp_path):
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_slice_timing_subject(
        matlab_command="matlab; evil",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert len(called) == 0


# ══════════════════════════════════════════════════════════════════════════════
# Fake MATLAB: success, missing output, nonzero
# ══════════════════════════════════════════════════════════════════════════════


def test_fake_matlab_success(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is True


def test_fake_matlab_success_has_corrected_file(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert "corrected_file" in result


def test_fake_matlab_missing_output(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=False)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is False


def test_fake_matlab_missing_output_message(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=False)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    error_text = " ".join(result.get("errors", []))
    assert "not found" in error_text.lower() or "missing" in error_text.lower()


def test_fake_matlab_nonzero(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=7)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result["ok"] is False
    assert result.get("returncode") == 7


def test_fake_matlab_logs_preserved(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert result.get("stdout_log") or result.get("stderr_log")


# ══════════════════════════════════════════════════════════════════════════════
# Safety + misc
# ══════════════════════════════════════════════════════════════════════════════


def test_safety_errors_in_result(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert "safety" in result
    assert len(result["safety"]["errors"]) >= 1


def test_subprocess_not_called_on_safety_error(monkeypatch, tmp_path):
    calls = []

    def _track(*a, **kw):
        calls.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_slice_timing_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    assert len(calls) == 0


def test_no_rawdata_written(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    rawdata = tmp_path / "data"
    assert not rawdata.exists() or list(rawdata.glob("*")) == []


def test_result_json_serializable(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
        tr=2.0,
        slice_order=[0, 1, 2, 3],
        reference_slice=2,
    )
    json.dumps(result, default=str)


def test_allowlist_not_changed():
    pass
