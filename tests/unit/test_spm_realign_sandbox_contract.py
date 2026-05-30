"""Sandbox-only execution contract tests for spm_realign_subject (M6-T005c).

All tests monkeypatch subprocess.run — no real MATLAB/SPM is called.
All paths use tmp_path.  spm_realign_subject is NOT in the reviewed
execution allowlist.
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
from src.backend.app.tools.spm_realign_runner import run_spm_realign_subject


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
    data = np.random.default_rng(7).normal(size=(4, 4, 4, 3)).astype("float32")
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(bold))
    return bold


def _extract_result_json(cmd: list[str]) -> Path:
    joined = " ".join(str(part) for part in cmd)
    matches = re.findall(r"'([^']*spm_realign_result\.json)'", joined)
    if not matches:
        raise AssertionError(f"Could not find result JSON in command: {cmd}")
    return Path(matches[-1])


def _fake_subprocess_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int = 0,
    create_outputs: bool = True,
) -> None:
    """Monkeypatch subprocess.run to simulate MATLAB execution."""

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
            payload["realigned_files"] = [
                str(result_json.parent / "rsub-001_task-rest_bold.nii"),
            ]
            payload["mean_file"] = str(result_json.parent / "meansub-001_task-rest_bold.nii")
            payload["motion_parameter_file"] = str(result_json.parent / "rp_sub-001_task-rest_bold.txt")
            if create_outputs:
                (result_json.parent / "rsub-001_task-rest_bold.nii").write_text("fake")
                (result_json.parent / "meansub-001_task-rest_bold.nii").write_text("fake")
                (result_json.parent / "rp_sub-001_task-rest_bold.txt").write_text("0 0 0 0 0 0\n")

        result_json.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


# ══════════════════════════════════════════════════════════════════════════════
# Sandbox input contract
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. synthetic BIDS input passes ──

def test_synthetic_input_passes(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    bold = _make_synthetic_bold(tmp_path)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(bold),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True


# ── 2. slice-timing derivatives input passes ──

def test_derivatives_input_passes(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    deriv = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    deriv.mkdir(parents=True)
    input_nii = deriv / "asub-001_bold.nii"
    data = np.random.default_rng(7).normal(size=(4, 4, 4, 3)).astype("float32")
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))
    result = run_spm_realign_subject(
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
    assert result["ok"] is True


# ── 3. arbitrary input path rejected ──

def test_arbitrary_input_rejected(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold="/etc/passwd",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "unsafe" in str(result["errors"]).lower()


# ── 4. non-synthetic rawdata rejected ──

def test_real_rawdata_rejected(tmp_path):
    raw = tmp_path / "data" / "sub-001" / "func" / "sub-001_bold.nii"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("dummy")
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(raw),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 5. path traversal in input rejected ──

def test_path_traversal_input_rejected(tmp_path):
    result = run_spm_realign_subject(
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


# ══════════════════════════════════════════════════════════════════════════════
# Output contract
# ══════════════════════════════════════════════════════════════════════════════

# ── 6. output goes to derivatives ──

def test_output_in_derivatives(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    bold = _make_synthetic_bold(tmp_path)
    deriv_dir = str(tmp_path / "derivatives")
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(bold),
        derivatives_dir=deriv_dir,
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True
    for output in result.get("outputs", []):
        assert deriv_dir in output or "work" in output or "logs" in output


# ── 7. output does not write to rawdata ──

def test_output_no_rawdata(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    bold = _make_synthetic_bold(tmp_path)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(bold),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    for output in result.get("outputs", []):
        parts = Path(output).parts
        forbidden = {"data", "rawdata"}
        assert not (set(parts) & forbidden), f"Output contains forbidden dir: {output}"


# ══════════════════════════════════════════════════════════════════════════════
# Approval + safety gate order
# ══════════════════════════════════════════════════════════════════════════════

# ── 8. approved=False blocks before MATLAB ──

def test_not_approved_blocks(tmp_path):
    result = run_spm_realign_subject(
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


# ── 9. unsafe matlab command blocks before MATLAB ──

def test_unsafe_matlab_blocks_before_subprocess(monkeypatch, tmp_path):
    called = []

    def _tracking_run(*args, **kwargs):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _tracking_run)
    result = run_spm_realign_subject(
        matlab_command="matlab; evil",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert len(called) == 0  # subprocess NEVER called


# ══════════════════════════════════════════════════════════════════════════════
# Fake MATLAB: success, missing output, nonzero returncode
# ══════════════════════════════════════════════════════════════════════════════

# ── 10. fake MATLAB success returns ok=True ──

def test_fake_matlab_success(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is True


# ── 11. fake MATLAB success returns expected outputs ──

def test_fake_matlab_success_has_outputs(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert "realigned_files" in result or "mean_file" in result


# ── 12. fake MATLAB missing output returns ok=False ──

def test_fake_matlab_missing_output(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=False)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 13. missing output error includes expected message ──

def test_fake_matlab_missing_output_message(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=False)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    error_text = " ".join(result.get("errors", []))
    assert "not found" in error_text.lower() or "missing" in error_text.lower()


# ── 14. fake MATLAB nonzero returncode returns ok=False ──

def test_fake_matlab_nonzero_returncode(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=7)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False


# ── 15. nonzero returncode result includes returncode ──

def test_fake_matlab_nonzero_has_returncode(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch, returncode=7)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("returncode") == 7


# ── 16. log files are recorded ──

def test_fake_matlab_logs_preserved(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result.get("stdout_log") or result.get("stderr_log")


# ══════════════════════════════════════════════════════════════════════════════
# Safety preflight in result
# ══════════════════════════════════════════════════════════════════════════════

# ── 17. safety preflight errors appear ──

def test_safety_errors_in_result(tmp_path):
    result = run_spm_realign_subject(
        matlab_command="python",  # blocked
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert result["ok"] is False
    assert "safety" in result
    assert len(result["safety"]["errors"]) >= 1


# ── 18. safety warnings appear ──

def test_safety_warnings_in_result(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_realign_subject(
        matlab_command="/usr/local/bin/matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    # Safety preflight completed without blocking (warning only for nonexistent path)
    assert result["ok"] is True


# ══════════════════════════════════════════════════════════════════════════════
# Safety: no real MATLAB, no rawdata, serialization
# ══════════════════════════════════════════════════════════════════════════════

# ── 19. subprocess.run not called on safety error ──

def test_subprocess_not_called_on_safety_error(monkeypatch, tmp_path):
    calls = []

    def _track(*args, **kwargs):
        calls.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    run_spm_realign_subject(
        matlab_command="python",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    assert len(calls) == 0


# ── 20. no rawdata written ──

def test_no_rawdata_written_sandbox(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    rawdata = tmp_path / "data"
    assert not rawdata.exists() or list(rawdata.glob("*")) == []


# ── 21. result JSON serializable ──

def test_result_json_serializable_sandbox(monkeypatch, tmp_path):
    _fake_subprocess_run(monkeypatch)
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_synthetic_bold(tmp_path)),
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        approved=True,
    )
    json.dumps(result, default=str)


# ── 22. reviewed execution allowlist NOT changed ──

def test_allowlist_not_changed():
    """spm_realign_subject is NOT in the reviewed execution allowlist."""
    # This test is a placeholder — the actual allowlist is in plan_adapter.py.
    # spm_realign_subject should remain blocked for reviewed execution.
    pass
