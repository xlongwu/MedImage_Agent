"""Tests for ALFF/ReHo output registration — Phase 5M."""

from __future__ import annotations


def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_stage_outputs.mock_store", store)
    return store


def _make_exec(tmp_path, exec_id="ar-ex-abc"):
    ed = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / exec_id
    ed.mkdir(parents=True)
    (ed / "sandbox_output").mkdir()
    return ed


def _make_metric_exec(tmp_path, exec_id="ar-ex-maps"):
    ed = _make_exec(tmp_path, exec_id)
    out = ed / "sandbox_output" / "sub-001_task-rest"
    out.mkdir(parents=True)
    (ed / "manifest.json").write_text(
        '{"status":"succeeded","alff":{"computed":true},"reho":{"computed":true}}'
    )
    (ed / "metric_plan.json").write_text('{"metadata_only":false}')
    (ed / "subject_status.json").write_text('{"total":1,"complete":1}')
    (out / "sub-001_desc-alff_map.nii.gz").write_text("alff")
    (out / "sub-001_desc-falff_map.nii.gz").write_text("falff")
    (out / "sub-001_desc-reho_map.nii.gz").write_text("reho")
    (out / "sub-001_desc-alff_provenance.json").write_text("{}")
    (out / "sub-001_desc-reho_provenance.json").write_text("{}")
    return ed


from src.backend.app.schemas.preprocessing_stage_outputs import (  # noqa: E402
    StageOutputRegistrationRequest,  # noqa: E402
)
from src.backend.app.services.preprocessing_stage_outputs import (  # noqa: E402
    register_alff_reho_outputs,  # noqa: E402
)


def test_registers_metadata_only_warning(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _make_exec(tmp_path)
    result = register_alff_reho_outputs(
        "brain-tumor-study",
        "pp-test",
        StageOutputRegistrationRequest(execution_id="ar-ex-abc", confirm_sandbox_outputs=True),
        project_dir=str(tmp_path),
    )
    assert result.status == "warning"


def test_registers_bids_like_metric_maps_in_artifact_registry(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _make_metric_exec(tmp_path)
    result = register_alff_reho_outputs(
        "brain-tumor-study",
        "pp-test",
        StageOutputRegistrationRequest(execution_id="ar-ex-maps", confirm_sandbox_outputs=True),
        project_dir=str(tmp_path),
    )
    assert result.ok
    assert result.status == "registered"

    from src.backend.app.services.preprocessing_artifact_registry import (
        REGISTRY_FILENAME,
        load_artifact_registry,
    )

    registry = load_artifact_registry(
        tmp_path / "preprocessing_runs" / "pp-test" / REGISTRY_FILENAME
    )
    by_stage = {}
    for item in registry["artifacts"]:
        by_stage.setdefault(item["stage_id"], set()).add(item["artifact_type"])

    assert {"alff_map", "falff_map"} <= by_stage["alff_falff"]
    assert "reho_map" in by_stage["reho"]


def test_blocks_missing_exec(tmp_path):
    result = register_alff_reho_outputs(
        "test", "pp-test", StageOutputRegistrationRequest(execution_id="")
    )
    assert result.status == "blocked"


def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient

    from src.backend.app.main import app

    _make_exec(tmp_path)
    client = TestClient(app)
    resp = client.post(
        "/api/projects/brain-tumor-study/preprocessing/runs/pp-test/stage-outputs/register-alff-reho",
        json={"execution_id": "ar-ex-abc", "confirm_sandbox_outputs": True},
    )
    assert resp.status_code == 200
