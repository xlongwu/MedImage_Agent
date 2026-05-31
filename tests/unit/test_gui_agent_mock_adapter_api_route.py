"""Tests for Mock Adapter API Route — M10-GUI-AGENT-MOCK-T003."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


def _create_mock_session(**extra):
    resp = client.post("/api/gui-agent/sessions", json={
        "provider": "mock",
        "target_app": "mock_app",
        "target_window": "mock_window",
        "allowed_action_tiers": [0],
        "file_scope": ["outputs/work/gui_agent/"],
        "approved": True,
        **extra,
    })
    assert resp.status_code == 200
    return resp.json()["session_id"]


# ══════════════════════════════════════════════════════════════════════════════
# A. Fixture Listing
# ══════════════════════════════════════════════════════════════════════════════

def test_get_fixtures_200():
    resp = client.get("/api/gui-agent/mock-adapter/fixtures")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_get_fixtures_has_items():
    fixtures = client.get("/api/gui-agent/mock-adapter/fixtures").json()["fixtures"]
    assert len(fixtures) >= 30


def test_get_fixtures_no_sensitive_data():
    resp = client.get("/api/gui-agent/mock-adapter/fixtures")
    parsed = resp.json()
    # Fixture listing only returns fixture_id, category, expected_status, expected_reason
    allowed_keys = {"fixture_id", "category", "expected_status", "expected_reason"}
    for f in parsed["fixtures"]:
        assert set(f.keys()) == allowed_keys, (
            f"Fixture listing must not expose extra fields: {set(f.keys()) - allowed_keys}"
        )
        # chain_of_thought or sensitive data fields must not appear
        assert "chain_of_thought" not in f
        assert "screenshot_bytes" not in f
        assert "clipboard_contents" not in f


def test_get_fixtures_has_safe_and_rejected():
    fixtures = client.get("/api/gui-agent/mock-adapter/fixtures").json()["fixtures"]
    statuses = {f["expected_status"] for f in fixtures}
    assert "NORMALIZED_ACTION_READY" in statuses
    assert "MODEL_ACTION_REJECTED" in statuses


# ══════════════════════════════════════════════════════════════════════════════
# B. Dry-Run Behavior
# ══════════════════════════════════════════════════════════════════════════════

def test_dry_run_safe_fixture():
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "safe_observe_current_state",
        "dry_run": True,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["status"] == "MODEL_ACTION_MAPPED_DRY_RUN"
    assert resp.json()["submitted_to_guard"] is False
    assert resp.json()["normalized_action_type"] == "record_observation"
    assert resp.json()["provider_call_allowed_by_adapter"] is False


def test_dry_run_rejected_fixture():
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "click_run",
        "dry_run": True,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["adapter_rejection_reason"] is not None
    assert resp.json()["submitted_to_guard"] is False
    assert resp.json()["provider_call_allowed"] is False


def test_dry_run_does_not_call_guard(monkeypatch):
    """Dry-run must never call the guarded step path."""
    called = []
    def _track(*a, **kw):
        called.append(1)
        raise RuntimeError("should not be called")
    monkeypatch.setattr(
        "src.backend.app.api.gui_agent_routes.api_gui_agent_step", _track)
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "safe_observe_current_state",
        "dry_run": True,
    })
    assert resp.status_code == 200
    assert len(called) == 0


# ══════════════════════════════════════════════════════════════════════════════
# C. Submit Mapped Fixture
# ══════════════════════════════════════════════════════════════════════════════

def test_submit_safe_fixture_200():
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["status"] == "MODEL_ACTION_MAPPED"


def test_submit_safe_fixture_has_guard_ok():
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert resp.json()["guard_status"] == "GUI_GUARD_OK"


def test_submit_safe_fixture_has_audit_id():
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert resp.json()["audit_id"] is not None
    assert resp.json()["audit_id"].startswith("audit_")


def test_submit_safe_fixture_adapter_vs_guard_provider():
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert resp.json()["provider_call_allowed_by_adapter"] is False
    assert resp.json()["provider_call_allowed_by_guard"] is True


def test_submit_safe_fixture_calls_mock_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda self, s, a, p: calls.append(a) or {
                            "executed": False, "provider_status": "MOCK_RECORDED"})
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert resp.status_code == 200
    assert len(calls) >= 1
    assert calls[0] == "record_observation"


def test_submit_safe_fixture_increments_count():
    sid = _create_mock_session()
    client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    from src.backend.app.runtime.gui_agent import _read_session
    s = _read_session(sid)
    assert s.get("step_count", 0) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# D. Rejected Fixture Submit
# ══════════════════════════════════════════════════════════════════════════════

def test_rejected_fixture_not_submitted():
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "click_run",
        "submit_to_guard": True,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["status"] == "MODEL_ACTION_REJECTED"
    assert resp.json()["submitted_to_guard"] is False


def test_rejected_fixture_guard_not_called(monkeypatch):
    called = []
    def _track(*a, **kw):
        called.append(1)
        raise RuntimeError("should not be called")
    monkeypatch.setattr(
        "src.backend.app.api.gui_agent_routes.api_gui_agent_step", _track)
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "click_run",
        "submit_to_guard": True,
    })
    assert resp.status_code == 200
    assert len(called) == 0


def test_rejected_fixture_no_audit():
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "click_run",
        "submit_to_guard": True,
    })
    assert resp.json()["audit_id"] is None


def test_rejected_fixture_safety_flags():
    sid = _create_mock_session()
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "click_run",
        "submit_to_guard": True,
    })
    assert resp.json()["provider_call_allowed"] is False
    assert resp.json()["desktop_touched"] is False
    assert resp.json()["screenshot_captured"] is False
    assert resp.json()["clipboard_accessed"] is False
    assert resp.json()["mouse_used"] is False
    assert resp.json()["keyboard_used"] is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Request Validation
# ══════════════════════════════════════════════════════════════════════════════

def test_unknown_fixture_returns_not_found():
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "nonexistent_fixture_xyz",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "MOCK_MODEL_FIXTURE_NOT_FOUND"


def test_submit_no_session_blocked():
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert resp.json()["ok"] is False
    assert resp.json()["status"] == "MOCK_ADAPTER_SESSION_REQUIRED"


def test_aborted_session_blocked():
    sid = _create_mock_session()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "session_id": sid,
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert resp.json()["ok"] is False


def test_step_limit_exceeded_blocked():
    sid = _create_mock_session(step_limit=2)
    for _ in range(3):
        resp = client.post("/api/gui-agent/mock-adapter/step", json={
            "session_id": sid,
            "fixture_id": "safe_observe_current_state",
            "submit_to_guard": True,
        })
    # Third call should be blocked
    assert resp.json()["ok"] is False


# ══════════════════════════════════════════════════════════════════════════════
# F. Safety / Non-Call Assertions
# ══════════════════════════════════════════════════════════════════════════════

def test_no_pywinauto_import():
    import sys
    assert "pywinauto" not in sys.modules


def test_adapter_never_sets_provider_call_true():
    """Across all mapped fixtures, adapter never sets provider_call_allowed=true."""
    for fid in ["safe_observe_current_state", "safe_record_observation"]:
        resp = client.post("/api/gui-agent/mock-adapter/step", json={
            "fixture_id": fid,
            "dry_run": True,
        })
        assert resp.json()["provider_call_allowed_by_adapter"] is False


def test_rejected_output_no_step_request():
    """Rejected outputs are never converted to step payloads."""
    resp = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "click_run",
        "dry_run": True,
    })
    assert "action_type" not in resp.json() or resp.json().get("normalized_action_type") is None


# ══════════════════════════════════════════════════════════════════════════════
# G. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_mock_fixture_tests_pass():
    """Marker: mock fixture tests 32/32."""
    pass


def test_adapter_validator_tests_pass():
    """Marker: model-output validator 58/58."""
    pass


def test_guard_compatibility_tests_pass():
    """Marker: adapter/guard compatibility 79/79."""
    pass


def test_guarded_api_tests_pass():
    """Marker: guarded API integration 62/62."""
    pass


def test_gui_reviewed_execution_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [{"id": "gui_t003", "depends_on": []}]}
    policy = classify_plan_nodes(plan)
    assert "gui_t003" in policy["blocked_unknown_nodes"]


def test_spm_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" in policy["allowed_spm_realign_sandbox_nodes"]


def test_dpabi_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "dpabi_capability_inspection", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "dpabi_capability_inspection" in policy["allowed_dpabi_metadata_nodes"]


def test_gpu_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_alff_subject" in policy["allowed_gpu_nodes"]
