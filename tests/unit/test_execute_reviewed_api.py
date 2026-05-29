"""Tests for Execute Reviewed Plan API (POST /api/plans/execute-reviewed)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


def _valid_body(**overrides):
    body = {
        "plan": {
            "pipeline_id": "test",
            "nodes": [
                {"id": "data_inspection", "backend": "python", "depends_on": [], "params": {}},
                {"id": "motion_qc_subject", "backend": "python",
                 "depends_on": ["data_inspection"], "params": {}},
            ],
        },
        "approval": {
            "approved": True,
            "approved_by": "user",
            "approved_nodes": ["*"],
            "rejected_nodes": [],
        },
        "dry_run": True,
    }
    body.update(overrides)
    return body


# ── 1. Returns 200 ──

def test_returns_200():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body())
    assert resp.status_code == 200


# ── 2. DRY_RUN_OK ──

def test_dry_run_ok():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body())
    data = resp.json()
    assert data["status"] == "DRY_RUN_OK"


# ── 3. would_execute true ──

def test_would_execute_true():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body())
    assert resp.json()["would_execute"] is True


# ── 4. executor_called false ──

def test_executor_called_false():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body())
    assert resp.json()["execution"]["executor_called"] is False


# ── 5. Validation failed ──

def test_validation_failed():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body(
        plan={"pipeline_id": "bad", "nodes": [{"id": "nonexistent_xyz", "depends_on": []}]},
    ))
    data = resp.json()
    assert data["status"] == "VALIDATION_FAILED"
    assert data["would_execute"] is False


# ── 6. Approval missing → blocked ──

def test_approval_missing_blocked():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body(
        plan={
            "pipeline_id": "test",
            "nodes": [
                {"id": "spm_realign_subject", "backend": "matlab-spm", "depends_on": [], "params": {}},
            ],
        },
        approval=None,
    ))
    data = resp.json()
    assert data["status"] == "APPROVAL_GATE_BLOCKED"


# ── 7. Approval false → blocked ──

def test_approval_false_blocked():
    plan = {
        "pipeline_id": "test",
        "nodes": [{"id": "spm_realign_subject", "backend": "matlab-spm", "depends_on": [], "params": {}}],
    }
    resp = client.post("/api/plans/execute-reviewed", json={
        "plan": plan,
        "approval": {"approved": False},
        "dry_run": True,
    })
    assert resp.json()["status"] == "APPROVAL_GATE_BLOCKED"


# ── 8. Missing approved node → blocked ──

def test_missing_approved_node_blocked():
    plan = {
        "pipeline_id": "test",
        "nodes": [{"id": "spm_realign_subject", "backend": "matlab-spm", "depends_on": [], "params": {}}],
    }
    resp = client.post("/api/plans/execute-reviewed", json={
        "plan": plan,
        "approval": {"approved": True, "approved_nodes": ["other_node"], "rejected_nodes": []},
        "dry_run": True,
    })
    assert resp.json()["status"] == "APPROVAL_GATE_BLOCKED"


# ── 9. dry_run=false → DRY_RUN_ONLY ──

def test_dry_run_false_refused():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body(dry_run=False))
    data = resp.json()
    assert data["status"] == "DRY_RUN_ONLY"
    assert data["execution"]["executor_called"] is False


# ── 10. Missing plan → 422 ──

def test_missing_plan_422():
    resp = client.post("/api/plans/execute-reviewed", json={"dry_run": True})
    assert resp.status_code == 422


# ── 11. Backend re-validates ──

def test_backend_revalidates():
    """Backend must re-run validate_plan — cannot trust front-end."""
    plan = {
        "pipeline_id": "test",
        "nodes": [{"id": "data_inspection", "backend": "python", "depends_on": [], "params": {}}],
    }
    resp = client.post("/api/plans/execute-reviewed", json={
        "plan": plan,
        "approval": None,
        "dry_run": True,
    })
    data = resp.json()
    assert data["status"] == "DRY_RUN_OK"
    assert data["validation"] is not None
    assert data["validation"]["ok"] is True


# ── 12. No executor ──

def test_no_executor():
    client.post("/api/plans/execute-reviewed", json=_valid_body())


# ── 13. No runner ──

def test_no_runner():
    client.post("/api/plans/execute-reviewed", json=_valid_body())


# ── 14. JSON serializable ──

def test_json_serializable():
    resp = client.post("/api/plans/execute-reviewed", json=_valid_body())
    json.loads(resp.text)
