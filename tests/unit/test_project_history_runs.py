from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.backend.app.api import (
    dashboard_routes,
    execute_reviewed_routes,
    project_history_routes,
    project_routes,
)
from src.backend.app.main import app
from src.backend.app.planner import project_context, reviewed_plan_store
from src.backend.app.runtime import desktop_config
from src.backend.app.schemas.desktop import RunLinkRecord
from src.backend.app.services.mock_store import SQLiteDesktopStore, utc_now_iso


def _isolated_store(tmp_path: Path, monkeypatch) -> SQLiteDesktopStore:
    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    monkeypatch.setattr(
        desktop_config,
        "DESKTOP_CONFIG_PATH",
        tmp_path / "desktop_config.json",
    )
    monkeypatch.setattr(project_routes, "DEFAULT_PROJECTS_ROOT", tmp_path / "projects")
    for module in (
        project_routes,
        dashboard_routes,
        project_context,
        reviewed_plan_store,
        project_history_routes,
        execute_reviewed_routes,
    ):
        monkeypatch.setattr(module, "mock_store", store)
    desktop_config.DESKTOP_CONFIG_PATH.write_text(
        json.dumps(desktop_config.DEFAULT_DESKTOP_CONFIG),
        encoding="utf-8",
    )
    return store


def _create_project(client: TestClient, tmp_path: Path, name: str = "History Project") -> dict:
    response = client.post(
        "/api/projects/create",
        json={
            "project_name": name,
            "rawdata_dir": str(Path("examples/synthetic_bids/rawdata").resolve()),
            "project_dir": str(tmp_path / name.replace(" ", "_")),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _reviewed_plan(created: dict) -> dict:
    rawdata_dir = created["rawdata_dir"]
    dataset_index_path = created["dataset_index_path"]
    return {
        "pipeline_id": "persisted-real-plan",
        "project_context": {
            "project_id": created["project_id"],
            "project_config_path": created["project_config_path"],
            "rawdata_dir": rawdata_dir,
            "dataset_index_path": dataset_index_path,
            "source": "created",
            "diagnostics": created["diagnostics"],
        },
        "nodes": [
            {
                "id": "data_inspection",
                "backend": "python",
                "depends_on": [],
                "params": {
                    "rawdata_dir": rawdata_dir,
                    "output_dir": str(Path(dataset_index_path).parent),
                },
            },
            {
                "id": "motion_qc_subject",
                "backend": "python",
                "depends_on": ["data_inspection"],
                "params": {"dataset_index": dataset_index_path},
            },
        ],
    }


def _save_plan(client: TestClient, created: dict, plan: dict) -> dict:
    response = client.post(
        f"/api/projects/{created['project_id']}/plans",
        json={
            "plan": plan,
            "project_config_path": created["project_config_path"],
            "validation": {"ok": True},
            "goal": "Inspect and run motion QC",
            "provider": "mock",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["reviewed_plan"]


def _add_run_link(
    store: SQLiteDesktopStore,
    created: dict,
    *,
    run_id: str,
    summary_path: Path | str | None,
    reviewed_plan_id: str | None = None,
    pipeline_path: Path | str | None = None,
    status: str = "SUCCESS",
) -> RunLinkRecord:
    now = utc_now_iso()
    record = RunLinkRecord(
        run_link_id=f"link-{run_id}",
        project_id=created["project_id"],
        reviewed_plan_id=reviewed_plan_id or f"reviewed-{run_id}",
        run_id=run_id,
        pipeline_path=str(pipeline_path or Path(created["project_dir"]) / "work" / f"{run_id}.yaml"),
        summary_path=str(summary_path) if summary_path is not None else None,
        project_config_path=created["project_config_path"],
        status=status,
        created_at=now,
        updated_at=now,
    )
    return store.add_run_link(record)


def _execute_body(created: dict, plan: dict, reviewed_plan_id: str) -> dict:
    return {
        "plan": plan,
        "approval": {
            "approved": True,
            "approved_by": "test-user",
            "approved_nodes": ["*"],
            "rejected_nodes": [],
        },
        "project_id": created["project_id"],
        "reviewed_plan_id": reviewed_plan_id,
        "project_config_path": created["project_config_path"],
        "dry_run": False,
        "persist_audit": True,
        "write_pipeline_yaml": True,
        "confirm_execution": True,
    }


def test_real_execution_persists_run_link_before_executor_and_exposes_history(
    tmp_path,
    monkeypatch,
):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    plan = _reviewed_plan(created)
    reviewed = _save_plan(client, created, plan)
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")
    monkeypatch.setattr(execute_reviewed_routes, "AUDIT_RECORD_DIR", tmp_path / "audit")
    monkeypatch.setattr(
        execute_reviewed_routes.pipeline_writer,
        "REVIEWED_PIPELINE_DIR",
        tmp_path / "pipelines",
    )

    def fake_executor(*, project_config_path: str, pipeline_path: str) -> dict:
        links = store.list_run_links(created["project_id"])
        assert len(links) == 1
        assert links[0].status == "RUNNING"
        pipeline = yaml.safe_load(Path(pipeline_path).read_text(encoding="utf-8"))
        run_id = pipeline["execution"]["run_id"]
        summary_path = tmp_path / f"{run_id}_summary.json"
        summary_path.write_text("{}", encoding="utf-8")
        return {"status": "SUCCESS", "run_id": run_id, "summary_path": str(summary_path)}

    monkeypatch.setattr(execute_reviewed_routes, "run_pipeline", fake_executor)
    response = client.post(
        "/api/plans/execute-reviewed",
        json=_execute_body(created, plan, reviewed["reviewed_plan_id"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "EXECUTION_SUBMITTED"
    assert payload["reviewed_plan_id"] == reviewed["reviewed_plan_id"]
    assert payload["run_link_id"]
    assert payload["run_id"].startswith("run_")
    assert Path(payload["pipeline_path"]).is_file()
    assert Path(payload["summary_path"]).is_file()

    runs = client.get(f"/api/projects/{created['project_id']}/runs")
    assert runs.status_code == 200
    assert [item["run_id"] for item in runs.json()["runs"]] == [payload["run_id"]]

    filtered = client.get(
        f"/api/projects/{created['project_id']}/runs",
        params={"reviewed_plan_id": reviewed["reviewed_plan_id"]},
    )
    assert filtered.status_code == 200
    assert [item["run_id"] for item in filtered.json()["runs"]] == [payload["run_id"]]

    detail = client.get(f"/api/projects/{created['project_id']}/runs/{payload['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["run_link"]["reviewed_plan_id"] == reviewed["reviewed_plan_id"]
    assert detail.json()["run_link"]["status"] == "SUCCESS"

    saved_again = _save_plan(client, created, plan)
    assert saved_again["execution_status"] == "SUCCESS"
    assert saved_again["last_execution_id"] == payload["run_link_id"]


def test_run_detail_reports_missing_pipeline_and_summary_warnings(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    reviewed = _save_plan(client, created, _reviewed_plan(created))
    run_id = "run_missing_pipeline_summary"
    summary_path = Path(created["project_dir"]) / "work" / "pipeline_runs" / run_id / "summary.json"
    _add_run_link(
        store,
        created,
        run_id=run_id,
        reviewed_plan_id=reviewed["reviewed_plan_id"],
        summary_path=summary_path,
    )

    response = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary_preview"] is None
    assert payload["summary_preview_error"] is None
    assert any("PIPELINE_YAML_MISSING" in item for item in payload["run_link"]["warnings"])
    assert any("SUMMARY_MISSING" in item for item in payload["run_link"]["warnings"])
    assert any("SUMMARY_FILE_MISSING" in item for item in payload["warnings"])


def test_run_detail_wrong_project_returns_not_found(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    first = _create_project(client, tmp_path, "Run First Project")
    second = _create_project(client, tmp_path, "Run Second Project")
    _add_run_link(store, first, run_id="run_project_scoped", summary_path=None)

    response = client.get(f"/api/projects/{second['project_id']}/runs/run_project_scoped")

    assert response.status_code == 404


def test_repeated_real_execution_gets_unique_run_ids(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    plan = _reviewed_plan(created)
    reviewed = _save_plan(client, created, plan)
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")
    monkeypatch.setattr(execute_reviewed_routes, "AUDIT_RECORD_DIR", tmp_path / "audit")
    monkeypatch.setattr(
        execute_reviewed_routes.pipeline_writer,
        "REVIEWED_PIPELINE_DIR",
        tmp_path / "pipelines",
    )

    def fake_executor(*, project_config_path: str, pipeline_path: str) -> dict:
        pipeline = yaml.safe_load(Path(pipeline_path).read_text(encoding="utf-8"))
        return {"status": "SUCCESS", "run_id": pipeline["execution"]["run_id"]}

    monkeypatch.setattr(execute_reviewed_routes, "run_pipeline", fake_executor)
    body = _execute_body(created, plan, reviewed["reviewed_plan_id"])
    first = client.post("/api/plans/execute-reviewed", json=body).json()
    second = client.post("/api/plans/execute-reviewed", json=body).json()

    assert first["run_id"] != second["run_id"]
    assert first["run_link_id"] != second["run_link_id"]
    assert len(store.list_run_links(created["project_id"])) == 2


def test_run_link_write_failure_blocks_executor(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    plan = _reviewed_plan(created)
    reviewed = _save_plan(client, created, plan)
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")
    monkeypatch.setattr(execute_reviewed_routes, "AUDIT_RECORD_DIR", tmp_path / "audit")
    monkeypatch.setattr(
        execute_reviewed_routes.pipeline_writer,
        "REVIEWED_PIPELINE_DIR",
        tmp_path / "pipelines",
    )
    executor_called = False

    def fail_add_run_link(*args, **kwargs):
        raise RuntimeError("simulated run link failure")

    def fake_executor(**kwargs):
        nonlocal executor_called
        executor_called = True
        return {"status": "SUCCESS"}

    monkeypatch.setattr(store, "add_run_link", fail_add_run_link)
    monkeypatch.setattr(execute_reviewed_routes, "run_pipeline", fake_executor)
    response = client.post(
        "/api/plans/execute-reviewed",
        json=_execute_body(created, plan, reviewed["reviewed_plan_id"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "RUN_LINK_WRITE_FAILED"
    assert executor_called is False


def test_real_execution_requires_matching_persisted_reviewed_plan(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    plan = _reviewed_plan(created)
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")

    response = client.post(
        "/api/plans/execute-reviewed",
        json=_execute_body(created, plan, "reviewed_missing"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REVIEWED_PLAN_MISMATCH"
    assert response.json()["execution"]["executor_called"] is False
