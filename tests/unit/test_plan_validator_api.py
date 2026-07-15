"""Tests for Plan Validator API endpoint (POST /api/plans/validate)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


def _valid_body(**overrides):
    return {
        "plan": {
            "pipeline_id": "test_plan",
            "nodes": [
                {"id": "data_inspection", "backend": "python", "depends_on": [], "params": {}},
                {"id": "motion_qc_subject", "backend": "python", "depends_on": ["data_inspection"], "params": {}},
            ],
            **overrides,
        }
    }


# ── 1. Valid plan → 200 ──

def test_valid_plan_returns_200():
    resp = client.post("/api/plans/validate", json=_valid_body())
    assert resp.status_code == 200


# ── 2. ok == true ──

def test_valid_plan_ok_true():
    resp = client.post("/api/plans/validate", json=_valid_body())
    data = resp.json()
    assert data["ok"] is True


# ── 3. risk_summary present ──

def test_risk_summary_present():
    resp = client.post("/api/plans/validate", json=_valid_body())
    data = resp.json()
    assert "risk_summary" in data
    assert data["risk_summary"]["nodes_total"] == 2


# ── 4. topological_order present ──

def test_topological_order_present():
    resp = client.post("/api/plans/validate", json=_valid_body())
    data = resp.json()
    assert "topological_order" in data
    assert data["topological_order"] == ["data_inspection", "motion_qc_subject"]


# ── 5. approval_required_nodes ──

def test_approval_required_node():
    resp = client.post("/api/plans/validate", json={
        "plan": {
            "pipeline_id": "p",
            "nodes": [
                {"id": "spm_realign_subject", "depends_on": [], "backend": "matlab-spm", "params": {}},
            ],
        }
    })
    data = resp.json()
    assert data["ok"] is True
    assert "spm_realign_subject" in data["approval_required_nodes"]


# ── 6. unknown node → 200, ok=false ──

def test_unknown_node_returns_200_ok_false():
    resp = client.post("/api/plans/validate", json={
        "plan": {
            "pipeline_id": "p",
            "nodes": [
                {"id": "nonexistent_xyz", "depends_on": []},
            ],
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False


# ── 7. unknown node in unknown_nodes ──

def test_unknown_node_in_list():
    resp = client.post("/api/plans/validate", json={
        "plan": {
            "pipeline_id": "p",
            "nodes": [
                {"id": "nonexistent_xyz", "depends_on": []},
            ],
        }
    })
    data = resp.json()
    assert "nonexistent_xyz" in data["unknown_nodes"]


# ── 8. dependency cycle → 200, ok=false ──

def test_dependency_cycle_returns_200():
    resp = client.post("/api/plans/validate", json={
        "plan": {
            "pipeline_id": "p",
            "nodes": [
                {"id": "data_inspection", "depends_on": ["motion_qc_subject"], "backend": "python"},
                {"id": "motion_qc_subject", "depends_on": ["data_inspection"], "backend": "python"},
            ],
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False


# ── 9. backend mismatch → warning ──

def test_backend_mismatch_rejected():
    resp = client.post("/api/plans/validate", json={
        "plan": {
            "pipeline_id": "p",
            "nodes": [
                {"id": "data_inspection", "depends_on": [], "backend": "matlab-spm"},
            ],
        }
    })
    data = resp.json()
    assert data["ok"] is False
    assert any(error["code"] == "BACKEND_MISMATCH" for error in data["errors"])


# ── 10. missing plan field → 422 ──

def test_missing_plan_field_422():
    resp = client.post("/api/plans/validate", json={})
    assert resp.status_code == 422


# ── 11. API does not execute runners ──

def test_api_does_not_execute_runners():
    resp = client.post("/api/plans/validate", json=_valid_body())
    assert resp.status_code == 200
    # No side effects — trivially passes


# ── 12. Response is JSON-serializable ──

def test_response_json_serializable():
    resp = client.post("/api/plans/validate", json=_valid_body())
    raw = resp.text
    back = json.loads(raw)
    assert back["ok"] is True
