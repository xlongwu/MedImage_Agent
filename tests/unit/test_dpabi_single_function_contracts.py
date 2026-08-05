from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from src.backend.app.tools.dpabi_function_contracts import get_dpabi_single_function_contract
from src.backend.app.tools.dpabi_wrapper import run_dpabi_single_function


def test_dpabi_allowlisted_contracts_exist():
    for function_name in [
        "y_Smooth",
        "y_Filter",
        "y_RegressOutImgCovariates",
        "y_alff_falff",
        "y_Reho",
        "y_ROItseries",
        "y_FC",
    ]:
        assert get_dpabi_single_function_contract(function_name)


def test_dpabi_contract_only_includes_output_manifest_and_external_result(tmp_path: Path):
    result = run_dpabi_single_function(
        function_name="y_FC",
        input_bold=str(tmp_path / "input.nii"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        dpabi_dir="./third_party/DPABI_V8.2_240510",
        matlab_command="matlab",
        mode="contract_only",
        approved=False,
        params={},
    )

    assert result["ok"] is True
    assert result["contract"]["description"]
    assert result["expected_outputs"]
    assert result["external_tool_result"]["tool_name"] == "dpabi.y_FC"


def _fake_dpabi_subprocess(
    monkeypatch: pytest.MonkeyPatch, *, returncode: int = 0, create_outputs: bool = True
) -> None:
    def fake_run(cmd: list[str], stdout=None, stderr=None, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        if stdout:
            stdout.write("fake DPABI stdout\n")
        if stderr:
            stderr.write("fake DPABI stderr\n")

        joined = " ".join(str(part) for part in cmd)
        script_match = re.search(r"run\('([^']+matlab_script\.m)'\)", joined)
        if create_outputs and returncode == 0 and script_match:
            script = Path(script_match.group(1))
            content = script.read_text(encoding="utf-8")
            for output_path in re.findall(r"_path = '([^']+)';", content):
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix.lower() == ".tsv":
                    path.write_text("roi_1\troi_2\n0.1\t0.2\n", encoding="utf-8")
                else:
                    path.write_bytes(b"fake nifti payload")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


@pytest.mark.parametrize(
    "function_name",
    [
        "y_Smooth",
        "y_Filter",
        "y_RegressOutImgCovariates",
        "y_alff_falff",
        "y_Reho",
        "y_ROItseries",
        "y_FC",
    ],
)
def test_dpabi_fake_matlab_success_for_allowlist(
    function_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _fake_dpabi_subprocess(monkeypatch, returncode=0, create_outputs=True)

    result = run_dpabi_single_function(
        function_name=function_name,
        input_bold=str(tmp_path / "input.nii"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        dpabi_dir="./third_party/DPABI_V8.2_240510",
        matlab_command="fake-matlab",
        mode="synthetic_execute",
        approved=True,
        params={},
    )

    assert result["ok"] is True
    assert result["external_tool_result"]["returncode"] == 0
    assert result["output_mapping"]["expected_outputs"]
    assert not result["qc"]["missing_outputs"]


def test_dpabi_fake_matlab_missing_outputs_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_dpabi_subprocess(monkeypatch, returncode=0, create_outputs=False)

    result = run_dpabi_single_function(
        function_name="y_Filter",
        input_bold=str(tmp_path / "input.nii"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        dpabi_dir="./third_party/DPABI_V8.2_240510",
        matlab_command="fake-matlab",
        mode="synthetic_execute",
        approved=True,
        params={},
    )

    assert result["ok"] is False
    assert "Expected DPABI outputs were not found" in " ".join(result["errors"])


def test_dpabi_fake_matlab_nonzero_returncode_has_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _fake_dpabi_subprocess(monkeypatch, returncode=9, create_outputs=False)

    result = run_dpabi_single_function(
        function_name="y_Reho",
        input_bold=str(tmp_path / "input.nii"),
        subject_id="sub-001",
        derivatives_dir=str(tmp_path / "derivatives"),
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        dpabi_dir="./third_party/DPABI_V8.2_240510",
        matlab_command="fake-matlab",
        mode="synthetic_execute",
        approved=True,
        params={},
    )

    assert result["ok"] is False
    assert result["returncode"] == 9
    assert Path(result["external_tool_result"]["logs"]["stdout"]).exists()
