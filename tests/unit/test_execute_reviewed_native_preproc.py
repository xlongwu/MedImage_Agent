from __future__ import annotations

import json

import yaml
from fastapi.testclient import TestClient

from src.backend.app.main import app


client = TestClient(app)


def _write_project_config(path) -> None:
    config = {
        "project": {"name": "native-preproc-test", "description": "test project"},
        "runtime": {
            "work_dir": str(path.parent / "work"),
            "log_dir": str(path.parent / "logs"),
        },
        "third_party": {
            "spm_dir": str(path.parent / "spm"),
            "dpabi_dir": str(path.parent / "dpabi"),
        },
        "safety": {"rawdata_readonly": True},
    }
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def _native_execute_plan() -> dict[str, object]:
    return {
        "pipeline_id": "native_full_preprocessing",
        "nodes": [
            {
                "id": "native_preproc_full_execute",
                "backend": "native_python",
                "depends_on": [],
                "params": {
                    "input_bold": (
                        "examples/synthetic_bids/sub-001/func/"
                        "sub-001_task-rest_bold.nii.gz"
                    ),
                    "sidecar_json": (
                        "examples/synthetic_bids/sub-001/func/"
                        "sub-001_task-rest_bold.json"
                    ),
                    "output_dir": "derivatives/native-full",
                    "confirmations": {
                        "confirm_reviewed_native_execution": True,
                        "confirm_rawdata_readonly": True,
                        "confirm_no_external_tools": True,
                        "confirm_research_use_only": True,
                        "confirm_no_clinical_use": True,
                    },
                },
            }
        ],
        "metadata": {
            "capability_level": "computed",
            "native_preprocessing": True,
            "execution_requires_approval_gate": True,
        },
    }


def _native_execute_plan_missing_template_and_atlas(tmp_path) -> dict[str, object]:
    input_dir = tmp_path / "inputs" / "sub-001" / "func"
    input_dir.mkdir(parents=True)
    bold = input_dir / "sub-001_task-rest_bold.nii.gz"
    sidecar = input_dir / "sub-001_task-rest_bold.json"
    t1w = tmp_path / "inputs" / "sub-001" / "anat" / "sub-001_T1w.nii.gz"
    t1w.parent.mkdir(parents=True)
    bold.write_bytes(b"placeholder")
    t1w.write_bytes(b"placeholder")
    sidecar.write_text(
        json.dumps({"RepetitionTime": 2.0, "SliceTiming": [0.0, 1.0]}),
        encoding="utf-8",
    )

    plan = _native_execute_plan()
    params = plan["nodes"][0]["params"]  # type: ignore[index]
    params.update(  # type: ignore[union-attr]
        {
            "input_bold": str(bold),
            "sidecar_json": str(sidecar),
            "t1w": str(t1w),
            "output_dir": str(tmp_path / "native-out"),
        }
    )
    return plan


def test_native_full_preprocessing_allows_reviewed_execution(monkeypatch, tmp_path) -> None:
    cfg = tmp_path / "project_config.yaml"
    _write_project_config(cfg)
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes._check_native_preproc_readiness",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.pipeline_writer.REVIEWED_PIPELINE_DIR",
        tmp_path / "reviewed_pipelines",
    )
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.run_pipeline",
        lambda **kw: {"status": "SUCCESS", "run_id": "native-run-001"},
    )

    response = client.post(
        "/api/plans/execute-reviewed",
        json={
            "plan": _native_execute_plan(),
            "approval": {
                "approved": True,
                "approved_by": "reviewer",
                "approved_nodes": ["native_preproc_full_execute"],
                "rejected_nodes": [],
                "native_preprocessing_acknowledgement": True,
                "no_external_tools_confirmed": True,
                "rawdata_read_only_confirmed": True,
                "risk_acknowledgement": True,
                "subject_scope_confirmed": True,
            },
            "dry_run": False,
            "confirm_execution": True,
            "persist_audit": True,
            "write_pipeline_yaml": True,
            "project_config_path": str(cfg),
        },
    )

    payload = response.json()
    assert payload["status"] == "EXECUTION_SUBMITTED"
    assert payload["adapter"]["policy"]["allowed_native_preproc_nodes"] == [
        "native_preproc_full_execute"
    ]
    assert payload["adapter"]["policy"]["blocked_native_preproc_nodes"] == []
    assert payload["execution"]["executor_called"] is True
    assert payload["execution"]["run_id"] == "native-run-001"


def test_native_full_preprocessing_executor_failure_is_not_reported_as_submitted(
    monkeypatch,
    tmp_path,
) -> None:
    cfg = tmp_path / "project_config.yaml"
    _write_project_config(cfg)
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes._check_native_preproc_readiness",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.pipeline_writer.REVIEWED_PIPELINE_DIR",
        tmp_path / "reviewed_pipelines",
    )
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.run_pipeline",
        lambda **kw: {
            "status": "FAILED",
            "run_id": "native-run-002",
            "errors": ["native preprocessing returned partial/blocked stages"],
        },
    )

    response = client.post(
        "/api/plans/execute-reviewed",
        json={
            "plan": _native_execute_plan(),
            "approval": {
                "approved": True,
                "approved_by": "reviewer",
                "approved_nodes": ["native_preproc_full_execute"],
                "rejected_nodes": [],
                "native_preprocessing_acknowledgement": True,
                "no_external_tools_confirmed": True,
                "rawdata_read_only_confirmed": True,
                "risk_acknowledgement": True,
                "subject_scope_confirmed": True,
            },
            "dry_run": False,
            "confirm_execution": True,
            "persist_audit": True,
            "write_pipeline_yaml": True,
            "project_config_path": str(cfg),
        },
    )

    payload = response.json()
    assert payload["status"] == "EXECUTION_FAILED"
    assert payload["ok"] is False
    assert payload["executor_result"]["status"] == "FAILED"
    assert payload["execution"]["executor_called"] is True
    assert payload["execution"]["run_id"] == "native-run-002"
    assert payload["errors"] == ["native preprocessing returned partial/blocked stages"]


def test_native_full_preprocessing_dry_run_blocks_missing_template_and_atlas(
    tmp_path,
) -> None:
    cfg = tmp_path / "project_config.yaml"
    _write_project_config(cfg)

    response = client.post(
        "/api/plans/execute-reviewed",
        json={
            "plan": _native_execute_plan_missing_template_and_atlas(tmp_path),
            "approval": {
                "approved": True,
                "approved_by": "reviewer",
                "approved_nodes": ["native_preproc_full_execute"],
                "rejected_nodes": [],
                "native_preprocessing_acknowledgement": True,
                "no_external_tools_confirmed": True,
                "rawdata_read_only_confirmed": True,
                "risk_acknowledgement": True,
                "subject_scope_confirmed": True,
            },
            "dry_run": True,
            "project_config_path": str(cfg),
        },
    )

    payload = response.json()
    assert payload["status"] == "NATIVE_PREPROC_READINESS_BLOCKED"
    assert payload["ok"] is False
    assert payload["execution"]["executor_called"] is False
    errors = "\n".join(payload["errors"]).lower()
    assert "template" in errors
    assert "atlas" in errors


def test_native_full_preprocessing_execute_blocks_before_executor_when_readiness_fails(
    monkeypatch,
    tmp_path,
) -> None:
    cfg = tmp_path / "project_config.yaml"
    _write_project_config(cfg)
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.run_pipeline",
        lambda **kw: (_ for _ in ()).throw(AssertionError("executor should not run")),
    )

    response = client.post(
        "/api/plans/execute-reviewed",
        json={
            "plan": _native_execute_plan_missing_template_and_atlas(tmp_path),
            "approval": {
                "approved": True,
                "approved_by": "reviewer",
                "approved_nodes": ["native_preproc_full_execute"],
                "rejected_nodes": [],
                "native_preprocessing_acknowledgement": True,
                "no_external_tools_confirmed": True,
                "rawdata_read_only_confirmed": True,
                "risk_acknowledgement": True,
                "subject_scope_confirmed": True,
            },
            "dry_run": False,
            "confirm_execution": True,
            "persist_audit": True,
            "write_pipeline_yaml": True,
            "project_config_path": str(cfg),
        },
    )

    payload = response.json()
    assert payload["status"] == "NATIVE_PREPROC_READINESS_BLOCKED"
    assert payload["ok"] is False
    assert payload["execution"]["executor_called"] is False
    assert payload["pipeline_yaml"]["written"] is False
