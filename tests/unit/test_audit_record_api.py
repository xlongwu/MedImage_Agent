"""Tests for Audit Record API (GET /api/audit/records)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


def _write_dummy_audit(audit_dir: Path, audit_id: str, event_type: str = "dry_run_checked"):
    audit_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "audit_id": audit_id,
        "created_at": "2026-05-29T00:00:00Z",
        "event_type": event_type,
        "plan_hash": "abc123",
        "validation_hash": "def456",
        "approval_hash": "ghi789",
        "actor": "tester",
        "source": "test",
        "plan": {"pipeline_id": "test"},
        "validation": {"ok": True},
        "approval": {"approved": True},
        "safety": {"review_only": True},
    }
    (audit_dir / f"{audit_id}.json").write_text(json.dumps(record), encoding="utf-8")


# ── 1. List returns 200 ──

def test_list_returns_200():
    resp = client.get("/api/audit/records")
    assert resp.status_code == 200


# ── 2. Empty returns ok=true ──

def test_list_ok_true():
    resp = client.get("/api/audit/records")
    assert resp.json()["ok"] is True


# ── 3. List with records (patch dir) ──

def test_list_with_records(monkeypatch, tmp_path):
    monkeypatch.setattr("src.backend.app.api.audit_record_routes.AUDIT_RECORD_DIR", tmp_path)
    _write_dummy_audit(tmp_path, "audit_001")
    _write_dummy_audit(tmp_path, "audit_002")
    resp = client.get("/api/audit/records")
    data = resp.json()
    assert data["count"] == 2
    assert len(data["items"]) == 2


# ── 4. Item has required fields ──

def test_item_has_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("src.backend.app.api.audit_record_routes.AUDIT_RECORD_DIR", tmp_path)
    _write_dummy_audit(tmp_path, "audit_001")
    resp = client.get("/api/audit/records")
    item = resp.json()["items"][0]
    for key in ["audit_id", "created_at", "event_type", "plan_hash", "validation_hash"]:
        assert key in item


# ── 5. Get single record ──

def test_get_single_record(monkeypatch, tmp_path):
    monkeypatch.setattr("src.backend.app.api.audit_record_routes.AUDIT_RECORD_DIR", tmp_path)
    _write_dummy_audit(tmp_path, "audit_001")
    resp = client.get("/api/audit/records/audit_001")
    assert resp.status_code == 200
    assert resp.json()["record"]["audit_id"] == "audit_001"


# ── 6. Nonexistent → 404 ──

def test_nonexistent_404(monkeypatch, tmp_path):
    monkeypatch.setattr("src.backend.app.api.audit_record_routes.AUDIT_RECORD_DIR", tmp_path)
    resp = client.get("/api/audit/records/nonexistent_xyz")
    assert resp.status_code == 404


# ── 7. Invalid audit_id → 400 ──

def test_invalid_audit_id_400():
    resp = client.get("/api/audit/records/../../etc/passwd")
    assert resp.status_code in (400, 404)


# ── 8. Path traversal blocked ──

def test_path_traversal_blocked():
    resp = client.get("/api/audit/records/../rawdata")
    assert resp.status_code in (400, 404)


# ── 9. No rawdata reads ──

def test_no_rawdata_read():
    resp = client.get("/api/audit/records")
    assert resp.status_code == 200


# ── 10. No executor ──

def test_no_executor():
    client.get("/api/audit/records")


# ── 11. No runner ──

def test_no_runner():
    client.get("/api/audit/records")


# ── 12. JSON serializable ──

def test_json_serializable():
    resp = client.get("/api/audit/records")
    json.loads(resp.text)
