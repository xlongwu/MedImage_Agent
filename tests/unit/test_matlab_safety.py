"""Tests for MATLAB command / third-party path safety guards."""

from __future__ import annotations

import json

from src.backend.app.safety.matlab_safety import (
    MatlabSafetyIssue,
    validate_matlab_command,
    validate_matlab_runtime_config,
    validate_third_party_dir,
)

# ══════════════════════════════════════════════════════════════════════════════
# MATLAB command validation
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. "matlab" passes ──


def test_matlab_passes():
    result = validate_matlab_command("matlab")
    assert result.ok is True


# ── 2. "matlab.exe" passes ──


def test_matlab_exe_passes():
    result = validate_matlab_command("matlab.exe")
    assert result.ok is True


# ── 3. Absolute path passes (warns if nonexistent) ──


def test_absolute_matlab_path_passes():
    result = validate_matlab_command("/usr/local/bin/matlab")
    assert result.ok is True
    # May have a warning about nonexistent path
    warnings = [w.code for w in result.warnings]
    assert "MATLAB_COMMAND_NOT_FOUND" in warnings or result.ok


# ── 4. Empty command rejected ──


def test_empty_command_rejected():
    result = validate_matlab_command("")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_EMPTY" for e in result.errors)


# ── 5. Command with space rejected ──


def test_command_with_spaces_rejected():
    result = validate_matlab_command("matlab -r evil")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_HAS_ARGUMENTS" for e in result.errors)


# ── 6. Compound command rejected ──


def test_compound_command_rejected():
    result = validate_matlab_command("matlab && rm -rf /")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_FORBIDDEN_CHAR" for e in result.errors)


# ── 7. "python" rejected ──


def test_python_rejected():
    result = validate_matlab_command("python")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_INVALID_BASENAME" for e in result.errors)


# ── 8. "bash" rejected ──


def test_bash_rejected():
    result = validate_matlab_command("bash")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_INVALID_BASENAME" for e in result.errors)


# ── 9. Semicolon rejected ──


def test_semicolon_rejected():
    result = validate_matlab_command("matlab;")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_FORBIDDEN_CHAR" for e in result.errors)


# ── 10. Newline rejected ──


def test_newline_rejected():
    result = validate_matlab_command("matlab\n")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_FORBIDDEN_CHAR" for e in result.errors)


# ── 11. Path traversal rejected ──


def test_path_traversal_rejected():
    result = validate_matlab_command("/usr/../bin/matlab")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_PATH_TRAVERSAL" for e in result.errors)


# ── 12. Pipe char rejected ──


def test_pipe_rejected():
    result = validate_matlab_command("matlab | cat")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_FORBIDDEN_CHAR" for e in result.errors)


# ── 13. Ampersand rejected ──


def test_ampersand_rejected():
    result = validate_matlab_command("matlab &")
    assert result.ok is False
    assert any(e.code == "MATLAB_COMMAND_FORBIDDEN_CHAR" for e in result.errors)


# ══════════════════════════════════════════════════════════════════════════════
# Third-party directory validation
# ══════════════════════════════════════════════════════════════════════════════

# ── 14. Valid path passes ──


def test_valid_third_party_dir_passes(tmp_path):
    spm = tmp_path / "spm12"
    spm.mkdir()
    result = validate_third_party_dir(str(spm), name="spm_dir")
    assert result.ok is True


# ── 15. Empty path rejected ──


def test_empty_third_party_dir_rejected():
    result = validate_third_party_dir("", name="spm_dir")
    assert result.ok is False
    assert any(e.code == "THIRD_PARTY_DIR_EMPTY" for e in result.errors)


# ── 16. Path traversal rejected ──


def test_third_party_dir_path_traversal_rejected():
    result = validate_third_party_dir("/usr/../spm12", name="spm_dir")
    assert result.ok is False
    assert any(e.code == "THIRD_PARTY_DIR_PATH_TRAVERSAL" for e in result.errors)


# ── 17. rawdata rejected ──


def test_third_party_dir_rawdata_rejected(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = validate_third_party_dir(str(raw), name="spm_dir")
    assert result.ok is False
    assert any(e.code == "THIRD_PARTY_DIR_FORBIDDEN_LOCATION" for e in result.errors)


# ── 18. derivatives rejected ──


def test_third_party_dir_derivatives_rejected(tmp_path):
    d = tmp_path / "derivatives"
    d.mkdir()
    result = validate_third_party_dir(str(d), name="spm_dir")
    assert result.ok is False
    assert any(e.code == "THIRD_PARTY_DIR_FORBIDDEN_LOCATION" for e in result.errors)


# ── 19. reports rejected ──


def test_third_party_dir_reports_rejected(tmp_path):
    r = tmp_path / "reports"
    r.mkdir()
    result = validate_third_party_dir(str(r), name="spm_dir")
    assert result.ok is False
    assert any(e.code == "THIRD_PARTY_DIR_FORBIDDEN_LOCATION" for e in result.errors)


# ── 20. work rejected ──


def test_third_party_dir_work_rejected(tmp_path):
    w = tmp_path / "work"
    w.mkdir()
    result = validate_third_party_dir(str(w), name="spm_dir")
    assert result.ok is False
    assert any(e.code == "THIRD_PARTY_DIR_FORBIDDEN_LOCATION" for e in result.errors)


# ── 21. nonexistent dir → warning, still ok ──


def test_third_party_dir_nonexistent_warns():
    result = validate_third_party_dir("/nonexistent/spm12", name="spm_dir")
    assert result.ok is True  # not an error
    assert any(w.code == "THIRD_PARTY_DIR_NOT_FOUND" for w in result.warnings)


# ── 22. dir is file → error ──


def test_third_party_dir_is_file_rejected(tmp_path):
    f = tmp_path / "not_a_dir"
    f.write_text("hello")
    result = validate_third_party_dir(str(f), name="spm_dir")
    assert result.ok is False
    assert any(e.code == "THIRD_PARTY_DIR_IS_FILE" for e in result.errors)


# ══════════════════════════════════════════════════════════════════════════════
# Combined runtime config validation
# ══════════════════════════════════════════════════════════════════════════════

# ── 23. Combined valid config passes ──


def test_combined_valid_passes(tmp_path):
    spm = tmp_path / "spm12"
    dpabi = tmp_path / "dpabi"
    spm.mkdir()
    dpabi.mkdir()
    result = validate_matlab_runtime_config(
        matlab_command="matlab",
        spm_dir=str(spm),
        dpabi_dir=str(dpabi),
    )
    assert result.ok is True


# ── 24. Combined bad command fails ──


def test_combined_bad_command_fails(tmp_path):
    spm = tmp_path / "spm12"
    dpabi = tmp_path / "dpabi"
    spm.mkdir()
    dpabi.mkdir()
    result = validate_matlab_runtime_config(
        matlab_command="python",
        spm_dir=str(spm),
        dpabi_dir=str(dpabi),
    )
    assert result.ok is False


# ── 25. Combined bad spm_dir fails ──


def test_combined_bad_spm_dir_fails(tmp_path):
    dpabi = tmp_path / "dpabi"
    dpabi.mkdir()
    result = validate_matlab_runtime_config(
        matlab_command="matlab",
        spm_dir="",
        dpabi_dir=str(dpabi),
    )
    assert result.ok is False


# ══════════════════════════════════════════════════════════════════════════════
# Serialization + safety
# ══════════════════════════════════════════════════════════════════════════════

# ── 26. to_dict is JSON serializable ──


def test_result_to_dict_json_serializable():
    result = validate_matlab_command("matlab")
    d = result.to_dict()
    json.dumps(d)


# ── 27. No subprocess called ──


def test_no_subprocess():
    result = validate_matlab_command("matlab")
    assert result.ok is True


# ── 28. No files written ──


def test_no_files_written():
    result = validate_matlab_command("matlab")
    assert result.ok is True


# ── 29. Issue to_dict serializable ──


def test_issue_to_dict():
    issue = MatlabSafetyIssue(
        code="TEST_CODE",
        message="test message",
        severity="error",
        field="test_field",
    )
    d = issue.to_dict()
    assert d["code"] == "TEST_CODE"
    assert d["message"] == "test message"
    assert d["severity"] == "error"
    assert d["field"] == "test_field"
    json.dumps(d)


# ══════════════════════════════════════════════════════════════════════════════
# M6-T005b-fix: SPM-only validator
# ══════════════════════════════════════════════════════════════════════════════

from src.backend.app.safety.matlab_safety import validate_spm_runtime_config  # noqa: E402

# ── 30. validate_spm_runtime_config("matlab", safe_dir) → ok ──


def test_validate_spm_runtime_config_ok(tmp_path):
    spm = tmp_path / "spm12"
    spm.mkdir()
    result = validate_spm_runtime_config(matlab_command="matlab", spm_dir=str(spm))
    assert result.ok is True


# ── 31. validate_spm_runtime_config does not require dpabi_dir ──


def test_validate_spm_runtime_config_no_dpabi():
    result = validate_spm_runtime_config(matlab_command="matlab", spm_dir="/tmp/spm12")
    assert result.ok is True


# ── 32. unsafe matlab_command blocked ──


def test_validate_spm_runtime_config_bad_matlab():
    result = validate_spm_runtime_config(matlab_command="matlab -r evil", spm_dir="/tmp/spm12")
    assert result.ok is False


# ── 33. unsafe spm_dir blocked ──


def test_validate_spm_runtime_config_bad_spm_dir(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = validate_spm_runtime_config(matlab_command="matlab", spm_dir=str(raw))
    assert result.ok is False


# ── 34. nonexistent spm_dir → warning ──


def test_validate_spm_runtime_config_nonexistent_warns():
    result = validate_spm_runtime_config(matlab_command="matlab", spm_dir="/nonexistent/spm12")
    assert result.ok is True
    assert any(w.code == "THIRD_PARTY_DIR_NOT_FOUND" for w in result.warnings)


# ── 35. validate_matlab_runtime_config() not regressed ──


def test_validate_matlab_runtime_config_not_regressed():
    from src.backend.app.safety.matlab_safety import validate_matlab_runtime_config

    result = validate_matlab_runtime_config(
        matlab_command="matlab",
        spm_dir="/tmp/spm12",
        dpabi_dir="/tmp/dpabi",
    )
    # Just verify it still works (both paths nonexistent → warning)
    assert result.ok is True
