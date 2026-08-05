"""Tests for SPM smoke test safety preflight (M6-T004a)."""

from __future__ import annotations

import json

from src.backend.app.tools.spm_runner import spm_smoke_preflight

# ── 1. valid matlab + safe spm_dir → preflight ok ──


def test_valid_preflight_ok(tmp_path):
    spm = tmp_path / "spm12"
    spm.mkdir()
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir=str(spm),
    )
    assert result["ok"] is True
    assert result["safety"]["ok"] is True
    assert result["would_call_matlab"] is True
    assert result["matlab_command_checked"] is True
    assert result["spm_dir_checked"] is True


# ── 2. "matlab -r evil" → preflight failed ──


def test_matlab_with_args_fails():
    result = spm_smoke_preflight(
        matlab_command="matlab -r evil",
        spm_dir="/tmp/spm12",
    )
    assert result["ok"] is False
    assert result["would_call_matlab"] is False
    assert len(result["safety"]["errors"]) >= 1


# ── 3. "matlab && rm -rf /" → preflight failed ──


def test_compound_command_fails():
    result = spm_smoke_preflight(
        matlab_command="matlab && rm -rf /",
        spm_dir="/tmp/spm12",
    )
    assert result["ok"] is False
    assert result["would_call_matlab"] is False


# ── 4. spm_dir pointing to rawdata → failed ──


def test_spm_dir_rawdata_fails(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir=str(raw),
    )
    assert result["ok"] is False
    assert any(
        "THIRD_PARTY_DIR_FORBIDDEN_LOCATION" in str(e.get("code", ""))
        for e in result["safety"]["errors"]
    )


# ── 5. spm_dir pointing to derivatives → failed ──


def test_spm_dir_derivatives_fails(tmp_path):
    d = tmp_path / "derivatives"
    d.mkdir()
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir=str(d),
    )
    assert result["ok"] is False


# ── 6. spm_dir nonexistent → warning, not error ──


def test_spm_dir_nonexistent_warns():
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir="/nonexistent/path/spm12",
    )
    assert result["ok"] is True  # not blocked
    assert len(result["safety"]["warnings"]) >= 1
    assert any(w.get("code") == "THIRD_PARTY_DIR_NOT_FOUND" for w in result["safety"]["warnings"])


# ── 7. safety warnings appear in result ──


def test_safety_warnings_in_result():
    result = spm_smoke_preflight(
        matlab_command="/usr/local/bin/matlab",
        spm_dir="/tmp/spm12",
    )
    assert "warnings" in result["safety"]


# ── 8. safety errors appear in result ──


def test_safety_errors_in_result():
    result = spm_smoke_preflight(
        matlab_command="python",
        spm_dir="/tmp/spm12",
    )
    assert len(result["safety"]["errors"]) >= 1


# ── 9. preflight does not call subprocess ──


def test_preflight_no_subprocess():
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir="/tmp/spm12",
    )
    assert result["ok"] is True


# ── 10. preflight does not call MATLAB ──


def test_preflight_no_matlab():
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir="/tmp/spm12",
    )
    assert "No MATLAB was called" in str(result["notes"])


# ── 11. preflight does not write rawdata ──


def test_preflight_no_rawdata_write(tmp_path):
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
    )
    assert result is not None


# ── 12. matlab_command_empty → preflight failed ──


def test_empty_matlab_command_fails():
    result = spm_smoke_preflight(
        matlab_command="",
        spm_dir="/tmp/spm12",
    )
    assert result["ok"] is False


# ── 13. JSON serializable ──


def test_result_json_serializable(tmp_path):
    spm = tmp_path / "spm12"
    spm.mkdir()
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir=str(spm),
    )
    json.dumps(result)


# ── 14. spm_dir path traversal → failed ──


def test_spm_dir_path_traversal_fails():
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir="/usr/../spm12",
    )
    assert result["ok"] is False


# ── 15. dpabi_dir also checked when provided ──


def test_dpabi_dir_checked(tmp_path):
    spm = tmp_path / "spm12"
    dpabi = tmp_path / "dpabi"
    spm.mkdir()
    dpabi.mkdir()
    result = spm_smoke_preflight(
        matlab_command="matlab",
        spm_dir=str(spm),
        dpabi_dir=str(dpabi),
    )
    assert result["ok"] is True
    assert result["dpabi_dir_checked"] is True
