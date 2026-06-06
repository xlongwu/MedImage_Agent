from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.app.api import (
    dashboard_routes,
    project_history_routes,
    project_routes,
)
from src.backend.app.main import app
from src.backend.app.planner import project_context, reviewed_plan_store
from src.backend.app.runtime import desktop_config
from src.backend.app.services.mock_store import SQLiteDesktopStore


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


def test_reviewed_plan_is_stable_listed_and_snapshotted(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    plan = _reviewed_plan(created)

    first = _save_plan(client, created, plan)
    second = _save_plan(client, created, plan)

    assert first["reviewed_plan_id"] == second["reviewed_plan_id"]
    assert first["plan_hash"] == second["plan_hash"]
    assert first["plan_hash"]
    assert len(store.list_reviewed_plans(created["project_id"])) == 1
    assert Path(first["plan_path"]).is_file()
    snapshot = json.loads(Path(first["plan_path"]).read_text(encoding="utf-8"))
    assert snapshot["payload"]["plan"] == plan

    listed = client.get(f"/api/projects/{created['project_id']}/plans")
    assert listed.status_code == 200
    assert [item["reviewed_plan_id"] for item in listed.json()["reviewed_plans"]] == [
        first["reviewed_plan_id"]
    ]

    detail = client.get(
        f"/api/projects/{created['project_id']}/plans/{first['reviewed_plan_id']}"
    )
    assert detail.status_code == 200
    assert detail.json()["reviewed_plan"]["payload"]["plan"] == plan


def test_reviewed_plan_id_is_project_scoped(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    first_project = _create_project(client, tmp_path, "First History Project")
    second_project = _create_project(client, tmp_path, "Second History Project")

    first = _save_plan(client, first_project, _reviewed_plan(first_project))
    second = _save_plan(client, second_project, _reviewed_plan(second_project))

    assert first["reviewed_plan_id"] != second["reviewed_plan_id"]
    wrong_project = client.get(
        f"/api/projects/{second_project['project_id']}/plans/{first['reviewed_plan_id']}"
    )
    assert wrong_project.status_code == 404


def test_missing_snapshot_is_reported_without_losing_sqlite_plan(tmp_path, monkeypatch):
    _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    record = _save_plan(client, created, _reviewed_plan(created))
    Path(record["plan_path"]).unlink()

    detail = client.get(
        f"/api/projects/{created['project_id']}/plans/{record['reviewed_plan_id']}"
    )

    assert detail.status_code == 200
    assert "PLAN_SNAPSHOT_MISSING" in detail.json()["reviewed_plan"]["warnings"]
    assert detail.json()["reviewed_plan"]["payload"]["plan"]
