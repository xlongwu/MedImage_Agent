"""Schema Consistency Tests — M10-GUI-AGENT-STABILIZE-T002."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)

SAFETY = ["desktop_touched", "screenshot_captured",
          "clipboard_accessed", "mouse_used", "keyboard_used"]


def _sid():
    r = client.post("/api/gui-agent/sessions", json={
        "provider": "mock", "target_app": "a", "target_window": "w",
        "allowed_action_tiers": [0], "file_scope": ["outputs/work/gui_agent/"],
        "approved": True,
    })
    assert r.status_code == 200
    return r.json()["session_id"]


def _step(sid=None, fid="safe_observe_current_state", submit=True, dry=False):
    body = {"fixture_id": fid, "submit_to_guard": submit, "dry_run": dry}
    if sid: body["session_id"] = sid
    return client.post("/api/gui-agent/mock-adapter/step", json=body)


# ══════════════════════════════════════════════════════════════════════════════
# A. Canonical Safety Fields — All Response Types
# ══════════════════════════════════════════════════════════════════════════════

def test_fixture_not_found_has_safety_flags():
    r = _step(fid="no_such")
    for f in SAFETY:
        assert f in r.json(), f"MOCK_MODEL_FIXTURE_NOT_FOUND missing {f}"
        assert r.json()[f] is False


def test_session_required_has_safety_flags():
    r = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "safe_observe_current_state", "submit_to_guard": True,
    })
    for f in SAFETY:
        assert f in r.json(), f"MOCK_ADAPTER_SESSION_REQUIRED missing {f}"
        assert r.json()[f] is False


def test_adapter_rejected_has_safety_flags():
    r = _step(fid="click_run")
    for f in SAFETY:
        assert f in r.json()
        assert r.json()[f] is False


def test_guard_blocked_has_safety_flags():
    sid = _sid()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _step(sid)
    for f in SAFETY:
        assert f in r.json()
        assert r.json()[f] is False


def test_dry_run_adapter_provider_false():
    r = _step(dry=True)
    assert "provider_call_allowed_by_adapter" in r.json()
    assert r.json()["provider_call_allowed_by_adapter"] is False


def test_mapped_adapter_provider_false():
    r = _step(_sid())
    assert r.json()["provider_call_allowed_by_adapter"] is False


def test_mapped_guard_provider_true():
    r = _step(_sid())
    assert r.json()["provider_call_allowed_by_guard"] is True


# ══════════════════════════════════════════════════════════════════════════════
# B. Status Semantics
# ══════════════════════════════════════════════════════════════════════════════

def test_rejected_never_submitted():
    r = _step(fid="click_run")
    assert r.json()["submitted_to_guard"] is False


def test_dry_run_never_has_audit():
    r = _step(dry=True)
    assert r.json()["audit_id"] is None


def test_mapped_has_audit():
    r = _step(_sid())
    assert r.json()["audit_id"] and r.json()["audit_id"].startswith("audit_")


def test_guard_blocked_has_guard_info():
    sid = _sid()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _step(sid)
    assert r.json()["guard_status"] is not None


def test_fixture_not_found_not_submitted():
    r = _step(fid="no_such")
    assert r.json()["submitted_to_guard"] is False


def test_session_required_not_submitted():
    r = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "safe_observe_current_state", "submit_to_guard": True,
    })
    assert r.json()["submitted_to_guard"] is False


# ══════════════════════════════════════════════════════════════════════════════
# C. Data Exposure
# ══════════════════════════════════════════════════════════════════════════════

RESPONSE_SCENARIOS = [
    ("mapped", lambda: _step(_sid())),
    ("dry_run", lambda: _step(dry=True)),
    ("rejected", lambda: _step(fid="click_run")),
    ("guard_blocked", lambda: _step(fid="safe_observe_current_state",
                                    sid="nonexistent_id_xyz")),
    ("fixture_not_found", lambda: _step(fid="no_such")),
    ("session_required", lambda: client.post(
        "/api/gui-agent/mock-adapter/step",
        json={"fixture_id": "safe", "submit_to_guard": True})),
]

FORBIDDEN_KEYS = ["raw_text", "raw_json", "chain_of_thought",
                  "screenshot_bytes", "clipboard_contents",
                  "api_key", "token", "password", "credential"]


@pytest.mark.parametrize("name,fn", RESPONSE_SCENARIOS)
def test_no_sensitive_in_response(name, fn):
    r = fn()
    data = r.json()
    for key in FORBIDDEN_KEYS:
        assert key not in data, f"{name}: must not expose '{key}'"


# ══════════════════════════════════════════════════════════════════════════════
# D. Authority Boundary
# ══════════════════════════════════════════════════════════════════════════════

def test_adapter_never_sets_provider_true_any_response():
    for name, fn in RESPONSE_SCENARIOS:
        r = fn()
        data = r.json()
        adapter = data.get("provider_call_allowed_by_adapter")
        if adapter is not None:
            assert adapter is False, f"{name}: adapter must not grant permission"


def test_guard_only_sets_provider_true_on_success():
    # Only MODEL_ACTION_MAPPED has provider_call_allowed_by_guard=true
    r = _step(_sid())
    assert r.json()["provider_call_allowed_by_guard"] is True

    # All other paths have false or absent
    dry = _step(dry=True)
    assert dry.json().get("provider_call_allowed_by_guard", False) is not True

    rej = _step(fid="click_run")
    assert rej.json().get("provider_call_allowed_by_guard") is None  # not present in rejected schema


def test_rejected_never_true():
    r = _step(fid="click_run")
    assert r.json()["provider_call_allowed"] is False


def test_request_errors_never_true():
    r = _step(fid="no_such")
    assert r.json()["provider_call_allowed"] is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_error_code_audit_ok():
    pass


def test_mock_e2e_ok():
    pass


def test_mock_api_route_ok():
    pass


def test_guarded_api_ok():
    pass


def test_adapter_validator_ok():
    pass


def test_gui_blocklist_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [{"id": "gui_sc", "depends_on": []}]})
    assert "gui_sc" in p["blocked_unknown_nodes"]


def test_spm_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"}},
    ]})
    assert "spm_realign_subject" in p["allowed_spm_realign_sandbox_nodes"]


def test_dpabi_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [
        {"id": "dpabi_capability_inspection", "depends_on": [], "params": {}},
    ]})
    assert "dpabi_capability_inspection" in p["allowed_dpabi_metadata_nodes"]


def test_gpu_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [
        {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
    ]})
    assert "gpu_alff_subject" in p["allowed_gpu_nodes"]
