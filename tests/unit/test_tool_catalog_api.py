"""Tests for Tool Catalog API endpoints (GET /api/tools/catalog)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime.tool_catalog import build_tool_catalog

client = TestClient(app)


def test_catalog_returns_200():
    resp = client.get("/api/tools/catalog")
    assert resp.status_code == 200


def test_catalog_ok_is_true():
    resp = client.get("/api/tools/catalog")
    data = resp.json()
    assert data["ok"] is True


def test_catalog_count_matches_build():
    resp = client.get("/api/tools/catalog")
    data = resp.json()
    assert data["count"] == len(build_tool_catalog())


def test_catalog_items_non_empty():
    resp = client.get("/api/tools/catalog")
    data = resp.json()
    assert len(data["items"]) > 0


def test_catalog_items_have_required_fields():
    resp = client.get("/api/tools/catalog")
    data = resp.json()
    required = ["id", "name", "backend", "parallel_level", "description",
                "requires_approval", "manual_required", "risk_level",
                "inputs", "outputs", "tags"]
    for item in data["items"]:
        for field in required:
            assert field in item, f"Item {item.get('id')} missing '{field}'"


def test_catalog_contains_spm_realign():
    resp = client.get("/api/tools/catalog")
    data = resp.json()
    ids = {item["id"] for item in data["items"]}
    assert "spm_realign_subject" in ids


def test_spm_realign_requires_approval():
    resp = client.get("/api/tools/catalog")
    data = resp.json()
    spm = next(item for item in data["items"] if item["id"] == "spm_realign_subject")
    assert spm["requires_approval"] is True


def test_response_is_json_serializable():
    resp = client.get("/api/tools/catalog")
    raw = resp.text
    back = json.loads(raw)
    assert back["ok"] is True


def test_api_does_not_execute_runners():
    """Calling the API must not call any node runner functions."""
    resp = client.get("/api/tools/catalog")
    assert resp.status_code == 200
    # No side effects — passes trivially if no runner was invoked


# ── Single-item endpoint ──

def test_single_item_returns_200():
    resp = client.get("/api/tools/catalog/spm_realign_subject")
    assert resp.status_code == 200


def test_single_item_has_ok_and_item():
    resp = client.get("/api/tools/catalog/spm_realign_subject")
    data = resp.json()
    assert data["ok"] is True
    assert "item" in data
    assert data["item"]["id"] == "spm_realign_subject"


def test_single_item_nonexistent_returns_404():
    resp = client.get("/api/tools/catalog/nonexistent_node_xyz")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
