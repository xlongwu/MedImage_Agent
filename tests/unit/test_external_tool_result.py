from __future__ import annotations

import json
from pathlib import Path

from src.backend.app.runtime.external_tool_result import (
    ExternalToolRunResult,
    from_subprocess_result,
)


def test_external_tool_run_result_serializes_contract(tmp_path: Path):
    result = ExternalToolRunResult(
        tool_name="spm.realign",
        backend="matlab-spm",
        command=["matlab", "-batch", "disp('ok')"],
        inputs=["input.nii"],
        outputs=["output.nii"],
        logs={"stdout": "stdout.log"},
        returncode=0,
        approval={"approved": True},
        safety={"rawdata_modified": False},
    ).finish(returncode=0, duration_seconds=1.2)

    out = result.write_json(tmp_path / "external_tool.json")
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["ok"] is True
    assert payload["tool_name"] == "spm.realign"
    assert payload["approval"]["approved"] is True
    assert payload["safety"]["rawdata_modified"] is False


def test_from_subprocess_result_marks_errors():
    payload = from_subprocess_result(
        tool_name="dpabi.y_Smooth",
        backend="matlab-dpabi",
        command=["matlab"],
        returncode=1,
        errors=["MATLAB failed"],
    )

    assert payload["ok"] is False
    assert payload["returncode"] == 1
    assert payload["errors"] == ["MATLAB failed"]
