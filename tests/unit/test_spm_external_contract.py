from __future__ import annotations

from src.backend.app.tools.spm_realign_runner import run_spm_realign_subject
from src.backend.app.tools.spm_smooth_runner import run_spm_smooth_subject


def test_spm_realign_unapproved_returns_external_contract():
    result = run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir="./third_party/spm12",
        subject_id="sub-001",
        input_bold="examples/synthetic_bids/rawdata/sub-001/func/sub-001_task-rest_bold.nii.gz",
        derivatives_dir="./derivatives",
        work_dir="./work",
        log_dir="./logs",
        approved=False,
    )

    assert result["ok"] is False
    assert result["external_tool_result"]["tool_name"] == "spm.realign"
    assert result["external_tool_result"]["approval"]["required"] is True


def test_spm_smooth_unapproved_returns_external_contract():
    result = run_spm_smooth_subject(
        matlab_command="matlab",
        spm_dir="./third_party/spm12",
        subject_id="sub-001",
        derivatives_dir="./derivatives",
        work_dir="./work",
        log_dir="./logs",
        approved=False,
    )

    assert result["ok"] is False
    assert result["external_tool_result"]["tool_name"] == "spm.smooth"
    assert result["external_tool_result"]["safety"]["rawdata_readonly"] is True
