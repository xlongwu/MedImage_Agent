"""Tests for spm_slice_timing_subject safety preflight (M6-T006b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.backend.app.tools.spm_slice_timing_runner import run_spm_slice_timing_subject


def _make_synthetic_bold(tmp_path: Path) -> Path:
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func"
    raw.mkdir(parents=True, exist_ok=True)
    bold = raw / "sub-001_task-rest_bold.nii"
    bold.write_bytes(b"\x00" * 100)
    return bold


# ── 1. unsafe matlab_command blocked ──


def test_matlab_with_args_blocked(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="matlab -r evil",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("stage") == "matlab_safety_preflight"


# ── 2. compound command blocked ──


def test_compound_command_blocked(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="matlab && rm -rf /",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 3. spm_dir rawdata blocked ──


def test_spm_dir_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(raw),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 4. spm_dir derivatives blocked ──


def test_spm_dir_derivatives_blocked(tmp_path):
    d = tmp_path / "derivatives"
    d.mkdir()
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(d),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 5. safety error → no subprocess ──


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    called = []

    def _track(*a, **kw):
        called.append(1)
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
    )
    assert len(called) == 0


# ── 6. safety errors in result ──


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
    )
    assert "safety" in result
    assert len(result["safety"]["errors"]) >= 1


# ── 7. approved=false still blocks ──


def test_approved_false_blocks(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
    )
    assert result["ok"] is False
    assert "requires approved=true" in str(result["errors"])


# ── 8. synthetic input passes safety ──


def test_synthetic_input_passes(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    # Should fail at safety, not at input check
    assert result.get("stage") == "matlab_safety_preflight"


# ── 9. arbitrary input rejected ──


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
    )
    assert (
        "unsafe" in str(result["errors"]).lower()
        or "non-synthetic" in str(result["errors"]).lower()
    )


# ── 10. path traversal rejected ──


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
    )
    assert result["ok"] is False


# ── 11. JSON serializable ──


def test_result_json_serializable(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


# ── 12. no real MATLAB ──


def test_no_real_matlab(tmp_path):
    result = run_spm_slice_timing_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("matlab_called") is False
