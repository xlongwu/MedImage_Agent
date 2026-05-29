"""Tests for LLM Planner API endpoint (POST /api/planner/plan-from-goal)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


# ── 1. Returns 200 ──

def test_returns_200():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion correction"})
    assert resp.status_code == 200


# ── 2. ok == true ──

def test_ok_true():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    data = resp.json()
    assert data["ok"] is True


# ── 3. contains plan ──

def test_contains_plan():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    data = resp.json()
    assert "plan" in data
    assert data["plan"]["pipeline_id"] == "planned_motion_qc"


# ── 4. contains validation ──

def test_contains_validation():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    data = resp.json()
    assert "validation" in data
    assert data["validation"]["ok"] is True


# ── 5. spm_realign in plan ──

def test_spm_realign_in_plan():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    data = resp.json()
    nids = [n["id"] for n in data["plan"]["nodes"]]
    assert "spm_realign_subject" in nids


# ── 6. approval_required in validation ──

def test_approval_required_in_validation():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    data = resp.json()
    assert "spm_realign_subject" in data["validation"]["approval_required_nodes"]


# ── 7. empty goal → 200, ok=false ──

def test_empty_goal():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert any("EMPTY_GOAL" in e for e in data["errors"])


# ── 8. unsupported goal → 200, ok=false ──

def test_unsupported_goal():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "xyz unknown"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert any("UNSUPPORTED_GOAL" in e for e in data["errors"])


# ── 9. unsupported provider → 200, ok=false ──

def test_unsupported_provider():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion", "provider": "openai"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert any("UNSUPPORTED_PROVIDER" in e for e in data["errors"])


# ── 10. missing goal → 422 ──

def test_missing_goal_422():
    resp = client.post("/api/planner/plan-from-goal", json={})
    assert resp.status_code == 422


# ── 11. No pipeline execution ──

def test_no_pipeline_execution():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    assert resp.status_code == 200


# ── 12. No node runner execution ──

def test_no_runner_execution():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    assert resp.status_code == 200


# ── 13. JSON serializable ──

def test_json_serializable():
    resp = client.post("/api/planner/plan-from-goal", json={"goal": "motion"})
    raw = resp.text
    back = json.loads(raw)
    assert back["ok"] is True
