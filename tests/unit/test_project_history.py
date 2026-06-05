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
    status: str = "SUCCESS",
) -> RunLinkRecord:
    now = utc_now_iso()
    record = RunLinkRecord(
        run_link_id=f"link-{run_id}",
        project_id=created["project_id"],
        reviewed_plan_id=f"reviewed-{run_id}",
        run_id=run_id,
        pipeline_path=str(Path(created["project_dir"]) / "work" / f"{run_id}.yaml"),
        summary_path=str(summary_path) if summary_path is not None else None,
        project_config_path=created["project_config_path"],
        status=status,
        created_at=now,
        updated_at=now,
    )
    return store.add_run_link(record)


def _artifact_by_name(payload: dict, name: str) -> dict:
    for artifact in payload["artifacts"]:
        if artifact["name"] == name:
            return artifact
    raise AssertionError(f"Artifact not found: {name}; got {payload['artifacts']}")


def _write_run_artifact_fixture(
    store: SQLiteDesktopStore,
    created: dict,
    *,
    run_id: str = "run_artifacts",
) -> dict[str, Path]:
    project_dir = Path(created["project_dir"])
    work_dir = project_dir / "work"
    reports_dir = project_dir / "reports"
    logs_dir = project_dir / "logs"
    derivatives_dir = project_dir / "derivatives"
    for path in (work_dir, reports_dir, logs_dir, derivatives_dir):
        path.mkdir(parents=True, exist_ok=True)

    pipeline_path = work_dir / f"{run_id}.yaml"
    pipeline_path.write_text("pipeline_id: artifact-fixture\n", encoding="utf-8")
    report_path = reports_dir / "qc_report.md"
    report_path.write_text("# QC Report\n\nAll clear.\n", encoding="utf-8")
    qc_json_path = reports_dir / "qc_metrics.json"
    qc_json_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "ok": True,
                "mean_fd": 0.12,
                "warnings": ["minor motion note"],
                "errors": [],
                "subjects": [{"subject_id": "sub-01", "mean_fd": 0.12}],
                "thresholds": {"mean_fd": 0.2},
            }
        ),
        encoding="utf-8",
    )
    csv_path = reports_dir / "qc_table.csv"
    csv_path.write_text(
        "subject_id,mean_fd,status\nsub-01,0.12,PASS\nsub-02,0.32,WARN\n",
        encoding="utf-8",
    )
    log_path = logs_dir / "node.log"
    log_path.write_text(
        "node log line\nERROR motion_qc_subject failed\nTraceback line\n",
        encoding="utf-8",
    )
    binary_path = derivatives_dir / "bold.nii"
    binary_path.write_bytes(b"NIFTI")
    mat_path = derivatives_dir / "motion_params.mat"
    mat_path.write_bytes(b"MATLAB")
    missing_path = reports_dir / "missing_report.md"
    state_path = work_dir / "states" / run_id / "data_inspection.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "node": "data_inspection",
                "status": "SUCCESS",
                "outputs": [str(report_path), str(qc_json_path)],
                "stdout_log": str(log_path),
                "result_json": str(qc_json_path),
            }
        ),
        encoding="utf-8",
    )
    summary_path = work_dir / "pipeline_runs" / run_id / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "SUCCESS",
                "nodes_total": 1,
                "nodes_success": 1,
                "nodes_failed": 0,
                "node_states": [str(state_path)],
                "outputs": {
                    "report": str(report_path),
                    "binary": str(binary_path),
                    "csv": str(csv_path),
                    "mat": str(mat_path),
                },
                "artifacts": {
                    "qc_json": str(qc_json_path),
                    "missing": str(missing_path),
                },
            }
        ),
        encoding="utf-8",
    )
    record = _add_run_link(store, created, run_id=run_id, summary_path=summary_path)
    store.update_run_link(record.run_link_id, pipeline_path=str(pipeline_path))
    return {
        "summary": summary_path,
        "pipeline": pipeline_path,
        "report": report_path,
        "qc_json": qc_json_path,
        "csv": csv_path,
        "log": log_path,
        "binary": binary_path,
        "mat": mat_path,
        "missing": missing_path,
        "state": state_path,
    }


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


def test_reviewed_plan_is_stable_listed_and_snapshotted(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    plan = _reviewed_plan(created)

    first = _save_plan(client, created, plan)
    second = _save_plan(client, created, plan)

    assert first["reviewed_plan_id"] == second["reviewed_plan_id"]
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

    detail = client.get(f"/api/projects/{created['project_id']}/runs/{payload['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["run_link"]["reviewed_plan_id"] == reviewed["reviewed_plan_id"]
    assert detail.json()["run_link"]["status"] == "SUCCESS"

    saved_again = _save_plan(client, created, plan)
    assert saved_again["execution_status"] == "SUCCESS"
    assert saved_again["last_execution_id"] == payload["run_link_id"]


def test_run_detail_includes_safe_summary_preview(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    run_id = "run_summary_preview"
    summary_path = Path(created["project_dir"]) / "work" / "pipeline_runs" / run_id / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "SUCCESS",
                "started_at": "2026-06-05T01:00:00Z",
                "ended_at": "2026-06-05T01:01:00Z",
                "nodes_total": 2,
                "nodes_success": 1,
                "nodes_failed": 1,
                "warnings": ["top-level warning"],
                "node_results": [
                    {
                        "node_id": "data_inspection",
                        "ok": True,
                        "outputs": ["dataset_index.json"],
                    },
                    {
                        "node_id": "motion_qc_subject",
                        "ok": False,
                        "warnings": ["motion warning"],
                        "errors": ["motion failed"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    _add_run_link(store, created, run_id=run_id, summary_path=summary_path)

    response = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}")

    assert response.status_code == 200
    preview = response.json()["summary_preview"]
    assert preview["run_id"] == run_id
    assert preview["nodes_total"] == 2
    assert preview["nodes_succeeded"] == 1
    assert preview["nodes_failed"] == 1
    assert preview["finished_at"] == "2026-06-05T01:01:00Z"
    assert "top-level warning" in preview["warnings"]
    assert "motion_qc_subject: motion warning" in preview["warnings"]
    assert preview["failed_nodes"][0]["node_id"] == "motion_qc_subject"
    assert response.json()["summary_preview_error"] is None


def test_run_detail_reports_missing_summary_without_crashing(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    run_id = "run_missing_summary"
    summary_path = Path(created["project_dir"]) / "work" / "pipeline_runs" / run_id / "summary.json"
    _add_run_link(store, created, run_id=run_id, summary_path=summary_path)

    response = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary_preview"] is None
    assert payload["summary_preview_error"] is None
    assert any("SUMMARY_FILE_MISSING" in item for item in payload["warnings"])


def test_run_detail_reports_malformed_summary_json(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    run_id = "run_bad_summary"
    summary_path = Path(created["project_dir"]) / "work" / "pipeline_runs" / run_id / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("{not valid json", encoding="utf-8")
    _add_run_link(store, created, run_id=run_id, summary_path=summary_path)

    response = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary_preview"] is None
    assert "SUMMARY_JSON_INVALID" in payload["summary_preview_error"]
    assert any("SUMMARY_JSON_INVALID" in item for item in payload["warnings"])


def test_run_detail_rejects_summary_path_outside_project_outputs(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    run_id = "run_outside_summary"
    outside_summary = tmp_path / "outside-summary.json"
    outside_summary.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    _add_run_link(store, created, run_id=run_id, summary_path=outside_summary)

    response = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary_preview"] is None
    assert any("SUMMARY_PATH_OUTSIDE_PROJECT_OUTPUTS" in item for item in payload["warnings"])


def test_run_detail_rejects_summary_path_in_rawdata(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    run_id = "run_rawdata_summary"
    rawdata_summary = Path(created["rawdata_dir"]) / "dataset_description.json"
    _add_run_link(store, created, run_id=run_id, summary_path=rawdata_summary)

    response = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary_preview"] is None
    assert any("SUMMARY_PATH_IN_RAWDATA_REJECTED" in item for item in payload["warnings"])


def test_run_artifacts_list_discovers_summary_outputs_and_node_state_outputs(
    tmp_path,
    monkeypatch,
):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    paths = _write_run_artifact_fixture(store, created)

    response = client.get(f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts")

    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload["artifacts"]}
    assert paths["summary"].name in names
    assert paths["pipeline"].name in names
    assert paths["report"].name in names
    assert paths["qc_json"].name in names
    assert paths["csv"].name in names
    assert paths["log"].name in names
    assert paths["mat"].name in names
    missing = _artifact_by_name(payload, paths["missing"].name)
    assert missing["exists"] is False
    assert any("ARTIFACT_FILE_MISSING" in item for item in missing["warnings"])
    qc_json = _artifact_by_name(payload, paths["qc_json"].name)
    assert qc_json["json_summary"]["status"] == "PASS"
    assert qc_json["qc_summary"]["status"] == "PASS"
    assert qc_json["qc_summary"]["subject_id"] == "sub-01"
    assert {"label": "mean_fd", "value": "0.12"} in qc_json["qc_summary"]["metrics"]
    log = _artifact_by_name(payload, paths["log"].name)
    assert log["node_id"] == "data_inspection"
    assert "motion_qc_subject failed" in log["error_excerpt"]
    binary = _artifact_by_name(payload, paths["binary"].name)
    assert "qc_summary" not in binary
    assert "error_excerpt" not in binary


def test_run_artifact_detail_json_preview(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    paths = _write_run_artifact_fixture(store, created)
    listing = client.get(f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts").json()
    artifact = _artifact_by_name(listing, paths["qc_json"].name)

    response = client.get(
        f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts/{artifact['artifact_id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["preview_type"] == "json"
    assert payload["json"]["mean_fd"] == 0.12
    assert payload["json_summary"]["top_level_keys"][:3] == ["status", "ok", "mean_fd"]
    assert payload["json_summary"]["status"] == "PASS"
    assert payload["json_summary"]["warnings"]["count"] == 1
    assert payload["json_summary"]["errors"]["count"] == 0
    field_summaries = {
        item["key"]: item
        for item in payload["json_summary"]["field_summaries"]
    }
    assert field_summaries["subjects"]["type"] == "array"
    assert field_summaries["subjects"]["size"] == 1
    assert field_summaries["thresholds"]["type"] == "object"
    assert field_summaries["thresholds"]["size"] == 1
    assert payload["truncated"] is False


def test_run_artifact_detail_csv_preview(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    paths = _write_run_artifact_fixture(store, created)
    listing = client.get(f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts").json()
    artifact = _artifact_by_name(listing, paths["csv"].name)

    response = client.get(
        f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts/{artifact['artifact_id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["preview_type"] == "csv"
    assert payload["csv"]["columns"] == ["subject_id", "mean_fd", "status"]
    assert payload["csv"]["rows"] == [
        ["sub-01", "0.12", "PASS"],
        ["sub-02", "0.32", "WARN"],
    ]
    assert payload["csv"]["displayed_rows"] == 2
    assert payload["truncated"] is False


def test_run_artifact_detail_markdown_preview(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    paths = _write_run_artifact_fixture(store, created)
    listing = client.get(f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts").json()
    artifact = _artifact_by_name(listing, paths["report"].name)

    response = client.get(
        f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts/{artifact['artifact_id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["preview_type"] == "markdown"
    assert "# QC Report" in payload["content"]


def test_run_artifact_detail_reports_malformed_json(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    paths = _write_run_artifact_fixture(store, created)
    paths["qc_json"].write_text("{not-json", encoding="utf-8")
    listing = client.get(f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts").json()
    artifact = _artifact_by_name(listing, paths["qc_json"].name)

    response = client.get(
        f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts/{artifact['artifact_id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert any("ARTIFACT_JSON_INVALID" in item for item in payload["errors"])


def test_run_artifacts_reject_rawdata_and_outside_paths(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    run_id = "run_rejected_artifacts"
    project_dir = Path(created["project_dir"])
    summary_path = project_dir / "work" / "pipeline_runs" / run_id / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    outside_path = tmp_path / "outside_report.md"
    outside_path.write_text("# outside\n", encoding="utf-8")
    rawdata_path = Path(created["rawdata_dir"]) / "dataset_description.json"
    summary_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "SUCCESS",
                "outputs": [str(outside_path), str(rawdata_path)],
            }
        ),
        encoding="utf-8",
    )
    _add_run_link(store, created, run_id=run_id, summary_path=summary_path)

    response = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}/artifacts")

    assert response.status_code == 200
    payload = response.json()
    assert any("ARTIFACT_PATH_OUTSIDE_PROJECT_OUTPUTS" in item for item in payload["warnings"])
    assert any("ARTIFACT_PATH_IN_RAWDATA_REJECTED" in item for item in payload["warnings"])
    names = {item["name"] for item in payload["artifacts"]}
    assert outside_path.name not in names
    assert rawdata_path.name not in names


def test_run_artifact_binary_is_metadata_only(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    paths = _write_run_artifact_fixture(store, created)
    listing = client.get(f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts").json()
    artifact = _artifact_by_name(listing, paths["binary"].name)
    assert artifact["previewable"] is False

    response = client.get(
        f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts/{artifact['artifact_id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["preview_type"] == "metadata_only"
    assert payload["content"] is None
    assert any("ARTIFACT_NOT_PREVIEWABLE" in item for item in payload["warnings"])

    mat_artifact = _artifact_by_name(listing, paths["mat"].name)
    mat_response = client.get(
        f"/api/projects/{created['project_id']}/runs/run_artifacts/artifacts/{mat_artifact['artifact_id']}"
    )
    assert mat_response.status_code == 200
    mat_payload = mat_response.json()
    assert mat_payload["kind"] == "matlab"
    assert mat_payload["preview_type"] == "metadata_only"
    assert mat_payload["content"] is None


def test_run_artifact_large_text_and_json_are_truncated(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    created = _create_project(client, tmp_path)
    run_id = "run_large_artifacts"
    project_dir = Path(created["project_dir"])
    reports_dir = project_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    large_md = reports_dir / "large_report.md"
    large_json = reports_dir / "large_payload.json"
    large_md.write_text("# Large\n" + ("x" * 90_000), encoding="utf-8")
    large_json.write_text(json.dumps({"payload": "x" * 90_000}), encoding="utf-8")
    summary_path = project_dir / "work" / "pipeline_runs" / run_id / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps({"run_id": run_id, "status": "SUCCESS", "outputs": [str(large_md), str(large_json)]}),
        encoding="utf-8",
    )
    _add_run_link(store, created, run_id=run_id, summary_path=summary_path)
    listing = client.get(f"/api/projects/{created['project_id']}/runs/{run_id}/artifacts").json()

    for artifact_name in (large_md.name, large_json.name):
        artifact = _artifact_by_name(listing, artifact_name)
        response = client.get(
            f"/api/projects/{created['project_id']}/runs/{run_id}/artifacts/{artifact['artifact_id']}"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["truncated"] is True
        assert any("ARTIFACT_PREVIEW_TRUNCATED" in item for item in payload["warnings"])


def test_run_artifacts_wrong_project_returns_not_found(tmp_path, monkeypatch):
    store = _isolated_store(tmp_path, monkeypatch)
    client = TestClient(app)
    first = _create_project(client, tmp_path, "Artifact First Project")
    second = _create_project(client, tmp_path, "Artifact Second Project")
    _write_run_artifact_fixture(store, first, run_id="run_project_scoped_artifacts")

    response = client.get(
        f"/api/projects/{second['project_id']}/runs/run_project_scoped_artifacts/artifacts"
    )

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
