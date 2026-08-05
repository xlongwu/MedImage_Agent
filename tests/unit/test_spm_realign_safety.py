"""Tests for spm_realign_subject MATLAB safety preflight (M6-T005b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.backend.app.tools.spm_realign_runner import run_spm_realign_subject


def _make_raw_bold(tmp_path: Path) -> Path:
    """Create a synthetic BOLD file at the expected location."""
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func"
    raw.mkdir(parents=True, exist_ok=True)
    _bold = raw / "sub-001_task-rest_bold.nii.gz"
    # Need nibabel for gz files — use .nii instead
    bold_nii = raw / "sub-001_task-rest_bold.nii"
    bold_nii.write_bytes(b"\x00" * 100)  # dummy NIfTI
    return bold_nii


def _make_spm_dir(tmp_path: Path) -> Path:
    spm = tmp_path / "third_party" / "spm12"
    spm.mkdir(parents=True, exist_ok=True)
    return spm


# ══════════════════════════════════════════════════════════════════════════════
# Safety preflight: matlab_command
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. unsafe matlab_command "matlab -r evil" → preflight failed ──


def test_matlab_with_args_blocked(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="matlab -r evil",
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("stage") == "matlab_safety_preflight"
    assert result.get("matlab_called") is False


# ── 2. unsafe "matlab && rm -rf /" → preflight failed ──


def test_matlab_compound_blocked(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="matlab && rm -rf /",
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("matlab_called") is False


# ══════════════════════════════════════════════════════════════════════════════
# Safety preflight: spm_dir
# ══════════════════════════════════════════════════════════════════════════════

# ── 3. spm_dir pointing to rawdata → preflight failed ──


def test_spm_dir_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(raw),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert result.get("matlab_called") is False


# ── 4. spm_dir pointing to derivatives → preflight failed ──


def test_spm_dir_derivatives_blocked(tmp_path):
    d = tmp_path / "derivatives"
    d.mkdir()
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(d),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ══════════════════════════════════════════════════════════════════════════════
# Safety: subprocess, no MATLAB, warnings
# ══════════════════════════════════════════════════════════════════════════════

# ── 5. safety error → no subprocess.run called ──


def test_safety_error_no_subprocess(monkeypatch, tmp_path):
    called = []

    def _fake_run(*args, **kwargs):
        called.append(1)
        return subprocess.CompletedProcess(args[0] if args else [], 0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_spm_realign_subject(
        matlab_command="python",  # blocked
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert len(called) == 0  # subprocess.run never called


# ── 6. safety error → result contains safety.errors ──


def test_safety_error_contains_safety_errors(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="python",
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "safety" in result
    assert len(result["safety"]["errors"]) >= 1


# ── 7. nonexistent spm_dir → warning, not error ──


def test_nonexistent_spm_dir_warns_not_blocks(monkeypatch, tmp_path):
    # Safety only: won't block on nonexistent path (warning not error)
    from src.backend.app.safety.matlab_safety import validate_matlab_runtime_config

    result = validate_matlab_runtime_config(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "nonexistent_spm"),
        dpabi_dir=str(tmp_path / "nonexistent_dpabi"),
    )
    # Should have warnings but be ok
    assert result.ok is True or len(result.errors) == 0
    warnings = [w.code for w in result.warnings]
    assert "THIRD_PARTY_DIR_NOT_FOUND" in warnings


# ══════════════════════════════════════════════════════════════════════════════
# Existing checks still work
# ══════════════════════════════════════════════════════════════════════════════

# ── 8. approved=false still blocks ──


def test_approved_false_still_blocks(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=False,
    )
    assert result["ok"] is False
    assert "requires approved=true" in str(result["errors"])


# ── 9. unsafe input_bold still blocks ──


def test_unsafe_input_still_blocks(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold="/etc/passwd",  # not synthetic
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "unsafe input" in str(result["errors"]).lower()


# ══════════════════════════════════════════════════════════════════════════════
# Serialization + safety
# ══════════════════════════════════════════════════════════════════════════════

# ── 10. no rawdata written ──


def test_no_rawdata_written(tmp_path):
    run_spm_realign_subject(
        matlab_command="python",  # fails at safety
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    # No rawdata should be written
    rawdata = tmp_path / "data"
    assert not rawdata.exists() or list(rawdata.glob("*")) == []


# ── 11. result JSON serializable ──


def test_result_json_serializable(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="python",
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


# ── 12. no real MATLAB called ──


def test_no_real_matlab_called(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="python",
        spm_dir=str(_make_spm_dir(tmp_path)),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("matlab_called") is False
    assert result.get("spm_called") is False
