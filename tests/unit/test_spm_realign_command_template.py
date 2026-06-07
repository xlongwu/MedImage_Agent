"""Tests for build_spm_realign_batch_preview — pure function tests.

Verifies the MATLAB batch preview is deterministic, safe, and
contains no shell commands, eval/system calls, or user code.
"""

from __future__ import annotations

from src.backend.app.services.spm_realign_params import default_spm_realign_params
from src.backend.app.services.spm_realign_wrapper_skeleton import (
    build_spm_realign_batch_preview,
    build_spm_realign_batch_preview_result,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _dummy_inputs() -> list[dict]:
    return [
        {"bold_path": "/data/sub-01/func/sub-01_task-rest_bold.nii.gz"},
        {"bold_path": "/data/sub-02/func/sub-02_task-rest_bold.nii.gz"},
    ]


def _dummy_outputs() -> list[dict]:
    return [
        {"kind": "realigned_bold", "path": "/out/sub-01/func/rsub-01_bold.nii.gz"},
        {"kind": "motion_params", "path": "/out/sub-01/func/rp_sub-01_bold.txt"},
    ]


# ── Safety content tests ─────────────────────────────────────────────────────

def test_template_includes_preview_only():
    batch = build_spm_realign_batch_preview()
    assert "PREVIEW ONLY" in batch


def test_template_includes_command_template_id():
    batch = build_spm_realign_batch_preview(command_template_id="spm12_realign_estwrite_v1")
    assert "spm12_realign_estwrite_v1" in batch


def test_template_includes_validated_params():
    params = {
        "quality": 0.95, "separation_mm": 3, "fwhm_mm": 4,
        "register_to_mean": False, "interpolation": 4, "wrap": [1, 0, 1],
    }
    batch = build_spm_realign_batch_preview(params=params)
    assert "quality = 0.95" in batch
    assert "sep = 3.0" in batch
    assert "fwhm = 4.0" in batch
    assert "rtm = 0" in batch
    assert "interp = 4" in batch
    assert "wrap = [1, 0, 1]" in batch


def test_template_includes_bold_inputs():
    inputs = _dummy_inputs()
    batch = build_spm_realign_batch_preview(inputs=inputs)
    assert "sub-01_task-rest_bold" in batch
    assert "sub-02_task-rest_bold" in batch
    assert "matlabbatch{1}.spm.spatial.realign.estwrite.data" in batch


def test_template_no_matlab_batch():
    batch = build_spm_realign_batch_preview()
    assert "matlab -batch" not in batch.lower()
    assert "-batch" not in batch


def test_template_no_system_call():
    batch = build_spm_realign_batch_preview()
    assert "system(" not in batch


def test_template_no_eval():
    batch = build_spm_realign_batch_preview()
    assert "eval(" not in batch


def test_template_no_shell_command():
    batch = build_spm_realign_batch_preview()
    assert "shell_command" not in batch
    assert "matlab_script" not in batch


def test_unknown_unsafe_params_ignored():
    """Unsafe param names appear in error comments, but their values do not render as code."""
    batch = build_spm_realign_batch_preview(params={"matlab_script": "evil()", "shell_command": "rm"})
    # Values are never rendered
    assert "evil()" not in batch
    # Param names appear only in ERROR comments (not as executable code)
    lines = batch.splitlines()
    error_lines = [l for l in lines if "ERROR" in l and "matlab_script" in l]
    assert len(error_lines) >= 1, "matlab_script should appear in error comment"
    non_comment_lines = [l for l in lines if not l.strip().startswith("%")]
    assert not any("matlab_script" in l for l in non_comment_lines)


def test_invalid_params_still_produce_safe_template():
    """Default params used when invalid, no dangerous content."""
    batch = build_spm_realign_batch_preview(params={"quality": 99, "wrap": [9, 9, 9]})
    assert "PREVIEW ONLY" in batch
    assert "quality = 0.9" in batch  # default used
    assert "system(" not in batch


def test_deterministic_output():
    batch1 = build_spm_realign_batch_preview(
        inputs=_dummy_inputs(), params=default_spm_realign_params(),
        predicted_outputs=_dummy_outputs(),
    )
    batch2 = build_spm_realign_batch_preview(
        inputs=_dummy_inputs(), params=default_spm_realign_params(),
        predicted_outputs=_dummy_outputs(),
    )
    assert batch1 == batch2


def test_no_file_writes(tmp_path):
    """Pure function must not write files."""
    before = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()
    build_spm_realign_batch_preview(
        inputs=_dummy_inputs(), params=default_spm_realign_params(),
    )
    after = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()
    assert after == before


# ── Invalid param visibility tests ───────────────────────────────────────────


def test_invalid_params_produce_visible_warnings():
    result = build_spm_realign_batch_preview_result(
        params={"quality": 1.5, "matlab_script": "evil()"},
    )
    assert len(result["param_errors"]) >= 1
    preview = result["preview"]
    assert "PARAMETER VALIDATION ERRORS" in preview
    assert "PREVIEW USES CANONICAL DEFAULTS" in preview
    assert "quality" in " ".join(result["param_errors"])
    assert "matlab_script" in " ".join(result["param_errors"])


def test_unsafe_param_not_rendered_as_code():
    result = build_spm_realign_batch_preview_result(
        params={"matlab_script": "evil()", "shell_command": "rm -rf /"},
    )
    preview = result["preview"]
    assert "evil()" not in preview
    assert "rm -rf" not in preview
    assert "PARAMETER VALIDATION ERRORS" in preview


def test_result_includes_cleaned_params():
    result = build_spm_realign_batch_preview_result(
        params={"quality": 0.95, "separation_mm": 3},
    )
    assert result["cleaned_params"]["quality"] == 0.95
    assert result["cleaned_params"]["separation_mm"] == 3.0


def test_valid_params_have_no_errors():
    result = build_spm_realign_batch_preview_result(
        params=default_spm_realign_params(),
    )
    assert len(result["param_errors"]) == 0
    assert "PARAMETER VALIDATION ERRORS" not in result["preview"]


def test_deterministic_output_stills_holds():
    result1 = build_spm_realign_batch_preview_result(
        inputs=_dummy_inputs(), params={"quality": 0.8},
        predicted_outputs=_dummy_outputs(),
    )
    result2 = build_spm_realign_batch_preview_result(
        inputs=_dummy_inputs(), params={"quality": 0.8},
        predicted_outputs=_dummy_outputs(),
    )
    assert result1["preview"] == result2["preview"]
    assert result1["param_warnings"] == result2["param_warnings"]
    assert result1["param_errors"] == result2["param_errors"]


def test_backward_compatible_string_function_still_works():
    batch = build_spm_realign_batch_preview(
        inputs=_dummy_inputs(), params=default_spm_realign_params(),
    )
    assert "PREVIEW ONLY" in batch
    assert isinstance(batch, str)
