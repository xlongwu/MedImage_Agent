"""Tests for Filtering output registration — Phase 5L."""

from __future__ import annotations

import json


def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_stage_outputs.mock_store", store)
    return store


def _make_exec(tmp_path, exec_id="tf-ex-abc", metadata_only=True):
    ed = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / exec_id
    ed.mkdir(parents=True)
    (ed / "manifest.json").write_text(
        json.dumps({"status": "warning", "metadata_only": metadata_only})
    )
    (ed / "sandbox_output").mkdir()
    return ed


from src.backend.app.schemas.preprocessing_stage_outputs import (  # noqa: E402
    StageOutputRegistrationRequest,  # noqa: E402
)
from src.backend.app.services.preprocessing_stage_outputs import (  # noqa: E402
    register_filtering_outputs,  # noqa: E402
)


def test_registers_metadata_only_as_warning(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _make_exec(tmp_path)
    result = register_filtering_outputs(
        "brain-tumor-study",
        "pp-test",
        StageOutputRegistrationRequest(execution_id="tf-ex-abc", confirm_sandbox_outputs=True),
        project_dir=str(tmp_path),
    )
    assert result.status == "warning"


def test_blocks_missing_exec(tmp_path):
    result = register_filtering_outputs(
        "test", "pp-test", StageOutputRegistrationRequest(execution_id="")
    )
    assert result.status == "blocked"


def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient

    from src.backend.app.main import app

    _make_exec(tmp_path)
    client = TestClient(app)
    resp = client.post(
        "/api/projects/brain-tumor-study/preprocessing/runs/pp-test/stage-outputs/register-filtering",
        json={"execution_id": "tf-ex-abc", "confirm_sandbox_outputs": True},
    )
    assert resp.status_code == 200
