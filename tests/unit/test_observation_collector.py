from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.backend.app.api.dependencies import get_project_store
from src.backend.app.core.exceptions import SafetyError
from src.backend.app.main import app
from src.backend.app.runtime.execution_gateway import (
    ExecutionGateway,
    current_safe_allowlist_fingerprint,
)
from src.backend.app.runtime.node_contract_registry import get_node_contract
from src.backend.app.schemas.desktop import ProjectDetail, ReviewedPlanRecord, RunLinkRecord
from src.backend.app.services.agent_orchestrator import AgentOrchestrator
from src.backend.app.services.execution_ticket_service import ExecutionTicketService
from src.backend.app.services.mock_store import SQLiteDesktopStore
from src.backend.app.services.preprocessing_artifact_registry import REGISTRY_FILENAME
from src.backend.app.services.observation_collector import (
    ObservationCollector,
    calculate_observation_hash,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _prepared_run(
    tmp_path: Path,
    *,
    node_id: str = "data_inspection",
    numerical_artifact: bool = False,
):
    project_dir = tmp_path / "project"
    rawdata = project_dir / "rawdata"
    inputs = project_dir / "inputs"
    outputs = project_dir / "derivatives"
    for path in (project_dir, rawdata, inputs, outputs):
        path.mkdir(parents=True, exist_ok=True)
    project_config = project_dir / "project.yaml"
    pipeline_path = project_dir / "pipeline.yaml"
    project_config.write_text("runtime: {}\n", encoding="utf-8")
    pipeline_path.write_text("nodes: []\n", encoding="utf-8")

    store = SQLiteDesktopStore(tmp_path / "observation.sqlite")
    store.add_project(
        ProjectDetail(
            id="project-1",
            name="project-1",
            study_id="study-1",
            modality="rs-fMRI",
            created_date="test",
            subjects_count=1,
            current_pipeline_id="pipeline-1",
            sequences=[],
            scans_count=1,
            total_size="0 B",
            current_model_id="none",
            metadata={
                "project_dir": str(project_dir),
                "rawdata_dir": str(rawdata),
            },
        ),
        health_status="Ready",
        rawdata_dir=str(rawdata),
        overwrite=True,
    )
    reviewed = ReviewedPlanRecord(
        reviewed_plan_id="reviewed-1",
        project_id="project-1",
        project_config_path=str(project_config),
        rawdata_dir=str(rawdata),
        plan_hash="plan-hash",
        plan_path=str(project_dir / "plans" / "reviewed-1.json"),
        created_at="2020-01-01T00:00:00Z",
        updated_at="2020-01-01T00:00:00Z",
        approval_status="APPROVED",
        payload={"plan": {"pipeline_id": "pipeline-1"}, "goal": "test"},
    )
    store.add_reviewed_plan(reviewed)

    contract = get_node_contract(node_id)
    ticket_service = ExecutionTicketService(store)
    ticket = ticket_service.issue(
        project_id="project-1",
        reviewed_plan_id=reviewed.reviewed_plan_id,
        plan_hash=reviewed.plan_hash,
        approval_context_id="approval-1",
        approved_actor="reviewer",
        approved_node_ids=[node_id],
        approved_backend_ids=[contract.backend],
        input_roots=[str(inputs)],
        output_roots=[str(outputs)],
        readonly_roots=[str(rawdata)],
        project_config_path=str(project_config),
        pipeline_path=str(pipeline_path),
        safe_allowlist_fingerprint=current_safe_allowlist_fingerprint(),
        normalized_params_hash="normalized-params-hash",
        contract_versions={node_id: contract.contract_version},
        audit_id="audit-1",
    )
    orchestrator = AgentOrchestrator(store)
    lifecycle = orchestrator.prepare_reviewed_execution(
        project_id="project-1",
        reviewed_plan_id=reviewed.reviewed_plan_id,
        execution_ticket_id=ticket.execution_ticket_id,
        audit_id=ticket.audit_id,
        actor="reviewer",
    )
    _, _, lifecycle = orchestrator.dispatch_execution(
        lifecycle=lifecycle,
        actor="reviewer",
        dispatch=lambda: ExecutionGateway(ticket_service).dispatch(
            execution_ticket_id=ticket.execution_ticket_id,
            project_id=ticket.project_id,
            reviewed_plan_id=ticket.reviewed_plan_id,
            plan_hash=ticket.plan_hash,
            approval_context_id=ticket.approval_context_id,
            normalized_params_hash=ticket.normalized_params_hash,
            contract_versions=ticket.contract_versions,
            project_config_path=ticket.project_config_path,
            pipeline_path=ticket.pipeline_path,
            executor=lambda **_: {"status": "SUCCESS", "run_id": "run-1"},
        ),
    )

    report = outputs / "run-1" / "report.json"
    _write_json(report, {"ok": True})
    state_path = project_dir / "work" / "states" / "run-1" / f"{node_id}.json"
    _write_json(
        state_path,
        {
            "run_id": "run-1",
            "subject": "project",
            "node": node_id,
            "status": "SUCCESS",
            "backend": contract.backend,
            "contract_version": contract.contract_version,
            "outputs": [str(report)],
            "errors": [],
            "warnings": [],
        },
    )
    summary_path = project_dir / "work" / "pipeline_runs" / "run-1" / "summary.json"
    _write_json(
        summary_path,
        {
            "run_id": "run-1",
            "pipeline_id": "pipeline-1",
            "status": "SUCCESS",
            "started_at": "2026-07-14T00:00:00Z",
            "ended_at": "2026-07-14T00:01:00Z",
            "nodes_total": 1,
            "nodes_success": 1,
            "nodes_failed": 0,
            "node_states": [str(state_path)],
        },
    )
    if numerical_artifact:
        artifact_path = project_dir / "preprocessing_runs" / "run-1" / "fc.npy"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(artifact_path, np.eye(4, dtype=np.float32))
        _write_json(
            artifact_path.parent / REGISTRY_FILENAME,
            {
                "artifacts": [
                    {
                        "artifact_id": "artifact-fc",
                        "artifact_type": "fc_matrix",
                        "path": "preprocessing_runs/run-1/fc.npy",
                        "path_kind": "project_relative",
                        "stage_id": node_id,
                        "shape": [4, 4],
                        "dtype": "float32",
                        "provenance_id": "provenance-fc",
                    }
                ]
            },
        )
    store.add_run_link(
        RunLinkRecord(
            run_link_id="run-link-1",
            project_id="project-1",
            reviewed_plan_id=reviewed.reviewed_plan_id,
            run_id="run-1",
            pipeline_path=str(pipeline_path),
            summary_path=str(summary_path),
            project_config_path=str(project_config),
            audit_id=ticket.audit_id,
            status="SUCCESS",
            created_at="2020-01-01T00:00:00Z",
            updated_at="2026-07-14T00:01:00Z",
        )
    )
    return store, orchestrator, lifecycle, summary_path


def test_collector_persists_immutable_traceable_snapshot_and_reloads(tmp_path):
    store, _, lifecycle, _ = _prepared_run(tmp_path)
    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    assert observation.pipeline.status == "SUCCESS"
    assert observation.pipeline.summary_consistent is True
    assert observation.nodes[0].node_id == "data_inspection"
    assert observation.capability.defensible_level == "metadata_only"
    assert observation.completeness.status == "partial"
    assert {"validation", "logs"}.issubset(observation.completeness.missing_sources)
    assert calculate_observation_hash(observation) == observation.observation_hash
    assert all("project\\" not in (source.relative_path or "") for source in observation.sources)

    reopened = SQLiteDesktopStore(store.db_path)
    reloaded = reopened.get_observation(observation.observation_id)
    assert reloaded == observation
    assert reopened.list_observations(
        "project-1", lifecycle_id=lifecycle.lifecycle_id, run_id="run-1"
    ) == [observation]
    with pytest.raises(Exception):
        observation.pipeline.status = "FAILED"


def test_registered_reloadable_fc_artifact_is_computed_and_checksum_bound(tmp_path):
    store, _, lifecycle, _ = _prepared_run(
        tmp_path,
        node_id="functional_connectivity_subject",
        numerical_artifact=True,
    )
    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    fc = next(item for item in observation.artifacts if item.artifact_type == "fc_matrix")
    assert fc.exists is True
    assert fc.reload_status == "passed"
    assert fc.shape == (4, 4)
    assert fc.dtype == "float32"
    assert fc.registration_status == "registered"
    assert fc.provenance_id == "provenance-fc"
    assert len(fc.checksum_sha256 or "") == 64
    assert observation.capability.defensible_level == "computed"


def test_missing_summary_is_reported_as_structured_partial_evidence(tmp_path):
    store, _, lifecycle, summary_path = _prepared_run(tmp_path)
    summary_path.unlink()

    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    summary_source = next(
        source for source in observation.sources if source.source_type == "pipeline_summary"
    )
    assert summary_source.read_status == "missing"
    assert "pipeline_summary" in observation.completeness.missing_sources
    assert observation.completeness.status == "partial"


def test_corrupt_node_state_is_reported_as_invalid_blocking_evidence(tmp_path):
    store, _, lifecycle, summary_path = _prepared_run(tmp_path)
    state_path = summary_path.parents[2] / "states" / "run-1" / "data_inspection.json"
    state_path.write_text("{not-json", encoding="utf-8")

    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    state_source = next(
        source for source in observation.sources if source.source_type == "node_state"
    )
    assert state_source.read_status == "invalid"
    assert "NODE_STATE_INVALID:data_inspection.json" in observation.completeness.blocking_facts
    assert observation.completeness.status == "invalid"


def test_registered_missing_artifact_is_reported_as_structured_evidence(tmp_path):
    store, _, lifecycle, summary_path = _prepared_run(
        tmp_path,
        node_id="functional_connectivity_subject",
        numerical_artifact=True,
    )
    artifact_path = summary_path.parents[3] / "preprocessing_runs" / "run-1" / "fc.npy"
    artifact_path.unlink()

    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    artifact = next(item for item in observation.artifacts if item.artifact_type == "fc_matrix")
    assert artifact.exists is False
    assert artifact.reload_status == "failed"
    assert artifact.reload_message == "artifact_missing"
    assert observation.capability.defensible_level == "metadata_only"


def test_reload_failure_is_reported_without_promoting_computed_capability(tmp_path):
    store, _, lifecycle, summary_path = _prepared_run(
        tmp_path,
        node_id="functional_connectivity_subject",
        numerical_artifact=True,
    )
    artifact_path = summary_path.parents[3] / "preprocessing_runs" / "run-1" / "fc.npy"
    artifact_path.write_bytes(b"not-a-valid-npy")

    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    artifact = next(item for item in observation.artifacts if item.artifact_type == "fc_matrix")
    assert artifact.exists is True
    assert artifact.reload_status == "failed"
    assert artifact.reload_message and artifact.reload_message.startswith("reload_failed:")
    assert observation.capability.defensible_level == "metadata_only"


def test_pipeline_success_with_failed_validation_is_a_structured_conflict(tmp_path):
    store, _, lifecycle, summary_path = _prepared_run(
        tmp_path,
        node_id="functional_connectivity_subject",
        numerical_artifact=True,
    )
    run_dir = summary_path.parents[3] / "preprocessing_runs" / "run-1"
    registry_path = run_dir / REGISTRY_FILENAME
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["artifacts"][0]["stage_id"] = "functional_connectivity"
    _write_json(registry_path, registry)
    (run_dir / "fc.npy").write_bytes(b"not-a-valid-npy")

    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    assert observation.pipeline.status == "SUCCESS"
    assert observation.validations[0].status == "failed"
    assert "PIPELINE_VALIDATION_CONFLICT" in observation.completeness.conflicts
    assert observation.completeness.status == "invalid"


def test_stale_source_is_reported_as_a_structured_conflict(tmp_path):
    store, _, lifecycle, summary_path = _prepared_run(tmp_path)
    os.utime(summary_path, (1, 1))

    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )

    summary_source = next(
        source for source in observation.sources if source.source_type == "pipeline_summary"
    )
    assert summary_source.freshness == "stale"
    assert "STALE_SOURCES:pipeline_summary" in observation.completeness.conflicts
    assert observation.completeness.status == "invalid"


def test_outside_summary_is_rejected_without_reading_and_marks_invalid(tmp_path):
    store, _, lifecycle, _ = _prepared_run(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text('{"status":"SUCCESS","secret":"do-not-read"}', encoding="utf-8")
    run_link = store.get_run_link_by_run_id("project-1", "run-1")
    assert run_link is not None
    store.update_run_link(run_link.run_link_id, summary_path=str(outside))

    observation = ObservationCollector(store).collect(
        project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
    )
    assert observation.completeness.status == "invalid"
    assert "pipeline_summary" in observation.completeness.missing_sources
    assert any(
        "SUMMARY_PATH_OUTSIDE_PROJECT_OUTPUTS" in warning
        for source in observation.sources
        for warning in source.warnings
    )
    assert "do-not-read" not in observation.model_dump_json()


def test_binding_drift_and_cross_project_access_fail_closed(tmp_path):
    store, _, lifecycle, _ = _prepared_run(tmp_path)
    run_link = store.get_run_link_by_run_id("project-1", "run-1")
    assert run_link is not None
    store.update_run_link(run_link.run_link_id, reviewed_plan_id="reviewed-other")
    with pytest.raises(SafetyError, match="OBSERVATION_PLAN_BINDING_DRIFT"):
        ObservationCollector(store).collect(
            project_id="project-1", lifecycle_id=lifecycle.lifecycle_id
        )
    with pytest.raises(SafetyError, match="OBSERVATION_PROJECT_NOT_FOUND"):
        ObservationCollector(store).collect(
            project_id="project-demo-1", lifecycle_id=lifecycle.lifecycle_id
        )


def test_observation_api_collects_server_facts_and_rejects_client_booleans(tmp_path):
    store, _, lifecycle, _ = _prepared_run(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    try:
        client = TestClient(app)
        forged = client.post(
            f"/api/projects/project-1/agent-lifecycles/{lifecycle.lifecycle_id}/observations",
            json={
                "command_id": "forged",
                "actor": "client",
                "observation": {
                    "summary_status": "SUCCESS",
                    "artifacts_reloadable": True,
                },
            },
        )
        assert forged.status_code == 422

        collected = client.post(
            f"/api/projects/project-1/agent-lifecycles/{lifecycle.lifecycle_id}/observations",
            json={"command_id": "collect-1", "actor": "observer"},
        )
        assert collected.status_code == 200
        payload = collected.json()
        assert payload["lifecycle"]["state"] == "OBSERVING"
        assert payload["lifecycle"]["observation"] is None
        observation_id = payload["observation"]["observation_id"]
        queried = client.get(
            f"/api/projects/project-1/agent-lifecycles/{lifecycle.lifecycle_id}/observations/{observation_id}"
        )
        assert queried.status_code == 200
        assert queried.json()["observation"]["observation_hash"] == payload["observation"]["observation_hash"]
    finally:
        app.dependency_overrides.pop(get_project_store, None)
