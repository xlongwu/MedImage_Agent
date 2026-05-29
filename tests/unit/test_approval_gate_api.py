"""Tests for Approval Gate API (POST /api/approval/check)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


def _body(validation_overrides=None, approval=None):
    v = {
        "ok": True,
        "approval_required_nodes": [],
        "high_risk_nodes": [],
        "manual_required_nodes": [],
        "risk_summary": {"requires_approval": False},
    }
    if validation_overrides:
        v.update(validation_overrides)
    body: dict = {"plan": {"pipeline_id": "test", "nodes": []}, "validation": v}
    if approval is not None:
        body["approval"] = approval
    return body


# ── 1. No approval needed → 200, allowed ──

def test_no_approval_returns_200():
    resp = client.post("/api/approval/check", json=_body())
    assert resp.status_code == 200
    assert resp.json()["execution_allowed"] is True


# ── 2. Approval needed but missing → 200, not allowed ──

def test_approval_missing():
    resp = client.post("/api/approval/check", json=_body({
        "approval_required_nodes": ["spm_realign_subject"],
    }))
    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_allowed"] is False


# ── 3. approved=false → false ──

def test_approved_false():
    resp = client.post("/api/approval/check", json=_body(
        {"approval_required_nodes": ["spm_realign_subject"]},
        {"approved": False},
    ))
    assert resp.json()["execution_allowed"] is False


# ── 4. approved_nodes cover → true ──

def test_approved_nodes_cover():
    resp = client.post("/api/approval/check", json=_body(
        {"approval_required_nodes": ["spm_realign_subject"]},
        {"approved": True, "approved_nodes": ["spm_realign_subject"], "rejected_nodes": []},
    ))
    assert resp.json()["execution_allowed"] is True


# ── 5. approved_nodes missing required → false ──

def test_approved_nodes_missing():
    resp = client.post("/api/approval/check", json=_body(
        {"approval_required_nodes": ["spm_realign_subject"]},
        {"approved": True, "approved_nodes": ["data_inspection"], "rejected_nodes": []},
    ))
    assert resp.json()["execution_allowed"] is False


# ── 6. Wildcard → true ──

def test_wildcard():
    resp = client.post("/api/approval/check", json=_body(
        {"approval_required_nodes": ["spm_realign_subject", "spm_smooth_subject"]},
        {"approved": True, "approved_nodes": ["*"], "rejected_nodes": []},
    ))
    assert resp.json()["execution_allowed"] is True


# ── 7. Rejected → false ──

def test_rejected():
    resp = client.post("/api/approval/check", json=_body(
        {"approval_required_nodes": ["spm_realign_subject"]},
        {"approved": True, "approved_nodes": ["spm_realign_subject"], "rejected_nodes": ["spm_smooth_subject"]},
    ))
    assert resp.json()["execution_allowed"] is False


# ── 8. Manual required → false ──

def test_manual_required():
    resp = client.post("/api/approval/check", json=_body(
        {"manual_required_nodes": ["gui_node"]},
        {"approved": True, "approved_nodes": ["*"], "rejected_nodes": []},
    ))
    assert resp.json()["execution_allowed"] is False


# ── 9. High risk → warning ──

def test_high_risk_warning():
    resp = client.post("/api/approval/check", json=_body(
        {"approval_required_nodes": ["spm_realign_subject"], "high_risk_nodes": ["spm_realign_subject"]},
        {"approved": True, "approved_nodes": ["spm_realign_subject"], "rejected_nodes": []},
    ))
    data = resp.json()
    assert data["execution_allowed"] is True
    assert any(w["code"] == "HIGH_RISK_APPROVED" for w in data["warnings"])


# ── 10. Validation not ok → false ──

def test_validation_not_ok():
    resp = client.post("/api/approval/check", json=_body({"ok": False}))
    assert resp.json()["execution_allowed"] is False


# ── 11. Missing plan → 422 ──

def test_missing_validation_422():
    resp = client.post("/api/approval/check", json={"plan": {"nodes": []}})
    assert resp.status_code == 422


# ── 12. No executor call ──

def test_no_executor():
    client.post("/api/approval/check", json=_body())


# ── 13. No runner ──

def test_no_runner():
    client.post("/api/approval/check", json=_body())


# ── 14. JSON serializable ──

def test_json_serializable():
    resp = client.post("/api/approval/check", json=_body())
    json.loads(resp.text)
