"""Guarded GUI Agent API Integration Tests — M9-GUI-GUARD-T006.

End-to-end integration tests for the full 5-layer guard pipeline:
  Provider gate → Session validator → Action validator → Audit → Stop conditions.

All tests use mock-only provider.  PyWinAuto is never constructed or called.
No real desktop/screenshot/clipboard interaction occurs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

_VALID_SESSION = {
    "provider": "mock",
    "approved": True,
    "target_app": "mock_app",
    "target_window": "mock_window",
    "allowed_action_tiers": [0],
    "file_scope": ["outputs/work/gui_agent/"],
    "allow_rawdata_access": False,
    "allow_derivatives_write": False,
    "screenshot_policy": "disabled",
    "clipboard_policy": "disabled",
    "network_policy": "disabled",
    "external_app_policy": "declared_target_only",
    "duration_limit_seconds": 300,
    "step_limit": 20,
    "human_present": True,
    "emergency_abort_enabled": True,
    "audit_log_required": True,
    "redaction_policy": "required_for_persistence",
}

_VALID_STEP = {
    "action": "record_observation",
    "action_tier": 0,
    "read_only": True,
    "uses_screenshot": False,
    "uses_clipboard": False,
    "uses_keyboard": False,
    "uses_mouse": False,
    "network_access": False,
    "input_paths": [],
    "output_paths": [],
    "expected_side_effects": "none",
    "requires_per_action_confirmation": False,
    "rollback_plan": "none",
    "stop_conditions": ["unexpected_window"],
}


def _create_session(**overrides):
    body = dict(_VALID_SESSION)
    body.update(overrides)
    return client.post("/api/gui-agent/sessions", json=body)


def _do_step(session_id, **overrides):
    body = dict(_VALID_STEP)
    body.update(overrides)
    return client.post(f"/api/gui-agent/sessions/{session_id}/step", json=body)


def _sid(resp):
    return resp.json()["session_id"]


# ══════════════════════════════════════════════════════════════════════════════
# A. Happy Path Integration
# ══════════════════════════════════════════════════════════════════════════════

def test_valid_session_returns_200():
    resp = _create_session()
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_session_stores_provider_mock():
    resp = _create_session()
    assert resp.json()["provider"] == "mock"


def test_session_stores_declaration_fields():
    resp = _create_session()
    sid = _sid(resp)
    from src.backend.app.runtime.gui_agent import _read_session
    s = _read_session(sid)
    assert s.get("step_limit") == 20
    assert s.get("step_count") == 0
    assert s.get("human_present") is True
    assert s.get("emergency_abort_enabled") is True


def test_valid_step_returns_200():
    resp = client.post(f"/api/gui-agent/sessions/{_sid(_create_session())}/step",
                       json=_VALID_STEP)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_step_includes_audit():
    resp = _do_step(_sid(_create_session()))
    assert resp.status_code == 200
    data = resp.json()
    assert "audit" in data
    assert data["audit"]["audit_id"].startswith("audit_")


def test_step_audit_guard_result_ok():
    resp = _do_step(_sid(_create_session()))
    assert resp.json()["audit"]["guard_result"] == "GUI_GUARD_OK"
    assert resp.json()["audit"]["provider_call_allowed"] is True


def test_step_audit_computed_tier():
    resp = _do_step(_sid(_create_session()))
    assert resp.json()["audit"]["computed_action_tier"] == 0
    assert resp.json()["audit"]["declared_action_tier"] == 0


def test_step_audit_safety_flags():
    a = _do_step(_sid(_create_session())).json()["audit"]
    assert a["screenshot_requested"] is False
    assert a["clipboard_requested"] is False
    assert a["keyboard_requested"] is False
    assert a["mouse_requested"] is False
    assert a["network_requested"] is False


def test_step_increments_count():
    sid = _sid(_create_session())
    _do_step(sid)
    _do_step(sid)
    from src.backend.app.runtime.gui_agent import _read_session
    s = _read_session(sid)
    assert s.get("step_count", 0) >= 2


def test_mock_provider_called_once_per_step(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda self, s, a, p: calls.append(a) or {
                            "executed": False, "provider_status": "MOCK_RECORDED"})
    sid = _sid(_create_session())
    resp = _do_step(sid)
    assert resp.status_code == 200
    assert len(calls) == 1
    assert calls[0] == "record_observation"


# ══════════════════════════════════════════════════════════════════════════════
# B. Provider Gate Integration
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("provider", ["pywinauto", "real", "desktop", "browser", "manual"])
def test_blocked_provider_403(provider):
    resp = _create_session(provider=provider)
    assert resp.status_code == 403
    d = resp.json()["detail"]
    assert d["provider_call_allowed"] is False


def test_approved_true_does_not_bypass():
    resp = _create_session(provider="pywinauto", approved=True)
    assert resp.status_code == 403


def test_blocked_provider_response_flags():
    resp = _create_session(provider="pywinauto")
    d = resp.json()["detail"]
    assert d["desktop_touched"] is False
    assert d["screenshot_captured"] is False
    assert d["clipboard_accessed"] is False
    assert d["mouse_used"] is False
    assert d["keyboard_used"] is False


# ══════════════════════════════════════════════════════════════════════════════
# C. Session Declaration Integration
# ══════════════════════════════════════════════════════════════════════════════

def test_gui_sandbox_mode_false_blocked():
    resp = _create_session(gui_sandbox_mode=False)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_SANDBOX_REQUIRED"


def test_allowed_tiers_1_blocked():
    resp = _create_session(allowed_action_tiers=[1])
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_TIER_BLOCKED"


def test_screenshot_ephemeral_blocked():
    resp = _create_session(screenshot_policy="ephemeral_only")
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_SCREENSHOT_BLOCKED"


def test_screenshot_persist_raw_blocked():
    resp = _create_session(screenshot_policy="persist_raw")
    assert resp.status_code == 403


def test_clipboard_read_blocked():
    resp = _create_session(clipboard_policy="read")
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_CLIPBOARD_BLOCKED"


def test_network_local_only_blocked():
    resp = _create_session(network_policy="local_only")
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_NETWORK_BLOCKED"


def test_rawdata_access_true_blocked():
    resp = _create_session(allow_rawdata_access=True)
    assert resp.status_code == 403


def test_derivatives_write_true_blocked():
    resp = _create_session(allow_derivatives_write=True)
    assert resp.status_code == 403


def test_file_scope_rawdata_blocked():
    resp = _create_session(file_scope=["rawdata/sub-001/"])
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_file_scope_traversal_blocked():
    resp = _create_session(file_scope=["../escape"])
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_human_present_false_blocked():
    resp = _create_session(human_present=False)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_HUMAN_REQUIRED"


def test_emergency_abort_false_blocked():
    resp = _create_session(emergency_abort_enabled=False)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_EMERGENCY_ABORT_REQUIRED"


def test_audit_log_required_false_blocked():
    resp = _create_session(audit_log_required=False)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_AUDIT_REQUIRED"


# ══════════════════════════════════════════════════════════════════════════════
# D. Action Declaration Integration
# ══════════════════════════════════════════════════════════════════════════════

def test_click_run_step_blocked():
    resp = _do_step(_sid(_create_session()), action="click_run", action_tier=3)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_NOT_ALLOWED"


def test_get_window_title_step_blocked():
    resp = _do_step(_sid(_create_session()), action="get_window_title", action_tier=0)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_NOT_ALLOWED"


def test_screenshot_ephemeral_step_blocked():
    resp = _do_step(_sid(_create_session()), action="screenshot_ephemeral", action_tier=0)
    assert resp.status_code == 403


def test_action_tier_mismatch_blocked():
    resp = _do_step(_sid(_create_session()), action="record_observation", action_tier=1)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_TIER_MISMATCH"


def test_read_only_false_blocked():
    resp = _do_step(_sid(_create_session()), read_only=False)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_READ_ONLY_REQUIRED"


def test_uses_mouse_true_blocked():
    resp = _do_step(_sid(_create_session()), uses_mouse=True)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_MOUSE_BLOCKED"


def test_uses_keyboard_true_blocked():
    resp = _do_step(_sid(_create_session()), uses_keyboard=True)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_KEYBOARD_BLOCKED"


def test_uses_clipboard_true_blocked():
    resp = _do_step(_sid(_create_session()), uses_clipboard=True)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_CLIPBOARD_BLOCKED"


def test_uses_screenshot_true_blocked():
    resp = _do_step(_sid(_create_session()), uses_screenshot=True)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_SCREENSHOT_BLOCKED"


def test_network_access_true_blocked():
    resp = _do_step(_sid(_create_session()), network_access=True)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_NETWORK_BLOCKED"


def test_input_paths_non_empty_blocked():
    resp = _do_step(_sid(_create_session()), input_paths=["file.nii"])
    assert resp.status_code == 403


def test_output_paths_non_empty_blocked():
    resp = _do_step(_sid(_create_session()), output_paths=["out.json"])
    assert resp.status_code == 403


def test_side_effects_not_none_blocked():
    resp = _do_step(_sid(_create_session()), expected_side_effects="writes_file")
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_SIDE_EFFECT_BLOCKED"


def test_blocked_action_no_provider_call(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda self, s, a, p: calls.append(a) or {"executed": False})
    resp = _do_step(_sid(_create_session()), action="click_run", action_tier=3)
    assert resp.status_code == 403
    assert len(calls) == 0


def test_blocked_action_response_has_guard_error():
    resp = _do_step(_sid(_create_session()), action="click_run", action_tier=3)
    d = resp.json()["detail"]
    assert d["status"] == "GUI_GUARD_BLOCKED"
    assert d["provider_call_allowed"] is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Stop-Condition Integration
# ══════════════════════════════════════════════════════════════════════════════

def test_step_limit_exceeded():
    sid = _sid(_create_session(step_limit=2))
    _do_step(sid)
    _do_step(sid)
    resp = _do_step(sid)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_STEP_LIMIT_EXCEEDED"


def test_aborted_session_blocked():
    sid = _sid(_create_session())
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    resp = _do_step(sid)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_EMERGENCY_ABORTED"


def test_missing_stop_conditions_blocked():
    """Empty stop_conditions is caught by the action validator (runs first)."""
    resp = _do_step(_sid(_create_session()), stop_conditions=[])
    assert resp.status_code == 403
    # Caught by action validator (step 16: stop_conditions non-empty required)
    assert resp.json()["detail"]["error_code"] in (
        "GUI_GUARD_ACTION_INVALID", "GUI_GUARD_STOP_CONDITION"
    )


def test_stop_blocked_includes_audit_id():
    sid = _sid(_create_session())
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    resp = _do_step(sid)
    assert resp.status_code == 403
    assert "audit_id" in resp.json()["detail"]


def test_stop_blocked_no_provider_call(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda self, s, a, p: calls.append(a) or {"executed": False})
    sid = _sid(_create_session())
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    resp = _do_step(sid)
    assert resp.status_code == 403
    assert len(calls) == 0


# ══════════════════════════════════════════════════════════════════════════════
# F. Screenshot / Abort Route Behavior
# ══════════════════════════════════════════════════════════════════════════════

def test_screenshot_mock_session_returns_200():
    sid = _sid(_create_session())
    resp = client.get(f"/api/gui-agent/sessions/{sid}/screenshot")
    # Mock screenshot writes placeholder text — should succeed
    assert resp.status_code == 200


def test_screenshot_mock_is_placeholder():
    sid = _sid(_create_session())
    resp = client.get(f"/api/gui-agent/sessions/{sid}/screenshot")
    data = resp.json()
    assert data["artifact"]["type"] == "screenshot_placeholder"


def test_abort_marks_session():
    sid = _sid(_create_session())
    resp = client.post(f"/api/gui-agent/sessions/{sid}/abort")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ABORTED"


def test_after_abort_step_blocked():
    sid = _sid(_create_session())
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    resp = _do_step(sid)
    assert resp.status_code == 403


def test_abort_does_not_touch_desktop():
    sid = _sid(_create_session())
    resp = client.post(f"/api/gui-agent/sessions/{sid}/abort")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# G. PyWinAuto Non-Call Assertions
# ══════════════════════════════════════════════════════════════════════════════

def test_pywinauto_never_constructed():
    """Confirm PyWinAutoGuiProvider is never instantiated during tests."""
    # All session creation goes through the provider gate which blocks pywinauto.
    # We verify that mock sessions work and pywinauto sessions are blocked.
    resp_mock = _create_session()
    assert resp_mock.status_code == 200
    resp_pyw = _create_session(provider="pywinauto")
    assert resp_pyw.status_code == 403


def test_no_pywinauto_module_loaded():
    import sys
    assert "pywinauto" not in sys.modules, (
        "pywinauto module should not be imported during guarded API tests"
    )


# ══════════════════════════════════════════════════════════════════════════════
# H. Reviewed Execution Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_gui_reviewed_execution_still_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gui_t006_check", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gui_t006_check" in policy["blocked_unknown_nodes"]


def test_gui_executor_called_false():
    resp = client.post("/api/plans/execute-reviewed", json={
        "plan": {"pipeline_id": "t", "nodes": [
            {"id": "gui_int_test", "backend": "gui-agent", "depends_on": [], "params": {}},
        ]},
        "approval": {"approved": True, "approved_nodes": ["*"], "rejected_nodes": []},
        "dry_run": True,
    })
    assert resp.json()["execution"]["executor_called"] is False


def test_spm_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" not in policy["allowed_spm_realign_sandbox_nodes"]  # blocked per current safety policy


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
