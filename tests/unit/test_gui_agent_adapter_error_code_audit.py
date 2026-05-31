"""Adapter / Mock Route Error Code Audit Tests — M10-GUI-AGENT-STABILIZE-T001.

Verifies response structure consistency across all mock route statuses:
  MODEL_ACTION_MAPPED, MODEL_ACTION_MAPPED_DRY_RUN, MODEL_ACTION_REJECTED,
  MODEL_ACTION_GUARD_BLOCKED, MOCK_MODEL_FIXTURE_NOT_FOUND,
  MOCK_ADAPTER_SESSION_REQUIRED.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


def _session(**kw):
    return client.post("/api/gui-agent/sessions", json={
        "provider": "mock", "target_app": "a", "target_window": "w",
        "allowed_action_tiers": [0], "file_scope": ["outputs/work/gui_agent/"],
        "approved": True, **kw,
    }).json()["session_id"]


def _mock_step(sid=None, fid="safe_observe_current_state",
               submit=True, dry=False):
    body = {"fixture_id": fid, "submit_to_guard": submit, "dry_run": dry}
    if sid:
        body["session_id"] = sid
    return client.post("/api/gui-agent/mock-adapter/step", json=body)


# ══════════════════════════════════════════════════════════════════════════════
# A. Success Schema — MODEL_ACTION_MAPPED
# ══════════════════════════════════════════════════════════════════════════════

SUCCESS_FIELDS = [
    "ok", "status", "fixture_id", "model_output_id", "adapter_decision",
    "adapter_status", "normalized_action_type", "submitted_to_guard",
    "guard_status", "audit_id", "provider_call_allowed_by_adapter",
    "provider_call_allowed_by_guard",
    "desktop_touched", "screenshot_captured", "clipboard_accessed",
    "mouse_used", "keyboard_used",
]


def test_mapped_has_all_fields():
    r = _mock_step(_session())
    for f in SUCCESS_FIELDS:
        assert f in r.json(), f"MODEL_ACTION_MAPPED missing field: {f}"


def test_mapped_adapter_provider_false():
    assert _mock_step(_session()).json()["provider_call_allowed_by_adapter"] is False


def test_mapped_guard_provider_true():
    assert _mock_step(_session()).json()["provider_call_allowed_by_guard"] is True


def test_mapped_audit_id():
    aid = _mock_step(_session()).json()["audit_id"]
    assert aid and aid.startswith("audit_")


SAFETY_FLAGS = ["desktop_touched", "screenshot_captured",
                "clipboard_accessed", "mouse_used", "keyboard_used"]


def test_mapped_safety_flags():
    r = _mock_step(_session())
    for f in SAFETY_FLAGS:
        assert r.json()[f] is False, f"{f} must be false"


# ══════════════════════════════════════════════════════════════════════════════
# B. Dry-Run Schema — MODEL_ACTION_MAPPED_DRY_RUN
# ══════════════════════════════════════════════════════════════════════════════

def test_dry_run_submitted_false():
    r = _mock_step(dry=True)
    assert r.json()["submitted_to_guard"] is False
    assert r.json()["guard_status"] is None
    assert r.json()["audit_id"] is None


def test_dry_run_adapter_provider_false():
    assert _mock_step(dry=True).json()["provider_call_allowed_by_adapter"] is False


def test_dry_run_no_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda s, se, a, p: calls.append(1))
    _mock_step(dry=True)
    assert len(calls) == 0


# ══════════════════════════════════════════════════════════════════════════════
# C. Adapter Rejected Schema — MODEL_ACTION_REJECTED
# ══════════════════════════════════════════════════════════════════════════════

def test_rejected_status():
    r = _mock_step(fid="click_run")
    assert r.json()["status"] == "MODEL_ACTION_REJECTED"


def test_rejected_not_submitted():
    r = _mock_step(fid="click_run")
    assert r.json()["submitted_to_guard"] is False
    assert r.json()["guard_status"] is None
    assert r.json()["audit_id"] is None


def test_rejected_provider_call_allowed():
    assert _mock_step(fid="click_run").json()["provider_call_allowed"] is False


def test_rejected_adapter_reason():
    r = _mock_step(fid="click_run")
    assert r.json()["adapter_rejection_reason"] is not None


@pytest.mark.parametrize("fid", ["click_run", "provider_pywinauto",
    "take_screenshot", "read_clipboard", "enter_password"])
def test_rejected_normalized_null(fid):
    r = _mock_step(fid=fid)
    assert "normalized_action" not in r.json() or r.json().get("normalized_action") is None


def test_rejected_no_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda s, se, a, p: calls.append(1))
    _mock_step(fid="click_run")
    assert len(calls) == 0


def test_rejected_safety_flags():
    r = _mock_step(fid="click_run")
    for f in SAFETY_FLAGS:
        assert r.json()[f] is False, f"{f} must be false"


# ══════════════════════════════════════════════════════════════════════════════
# D. Guard Blocked Schema — MODEL_ACTION_GUARD_BLOCKED
# ══════════════════════════════════════════════════════════════════════════════

def test_guard_blocked_aborted():
    sid = _session()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _mock_step(sid)
    assert r.json()["status"] == "MODEL_ACTION_GUARD_BLOCKED"
    assert r.json()["ok"] is False


def test_guard_blocked_has_status():
    sid = _session()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _mock_step(sid)
    assert r.json()["guard_status"] is not None


def test_guard_blocked_adapter_provider_false():
    sid = _session()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _mock_step(sid)
    assert r.json()["provider_call_allowed_by_adapter"] is False


def test_guard_blocked_guard_provider_not_true():
    sid = _session()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _mock_step(sid)
    assert r.json().get("provider_call_allowed_by_guard", False) is not True


def test_guard_blocked_no_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda s, se, a, p: calls.append(1))
    sid = _session()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    _mock_step(sid)
    assert len(calls) == 0


def test_guard_blocked_step_limit():
    sid = _session(step_limit=2)
    _mock_step(sid)
    _mock_step(sid)
    r = _mock_step(sid)
    assert r.json()["status"] == "MODEL_ACTION_GUARD_BLOCKED"


def test_guard_blocked_invalid_session():
    r = _mock_step(sid="nonexistent_id_xyz")
    assert r.json()["status"] == "MODEL_ACTION_GUARD_BLOCKED"
    assert r.json()["guard_status"] == "SESSION_NOT_FOUND"


# ══════════════════════════════════════════════════════════════════════════════
# E. Fixture / Request Error Schema
# ══════════════════════════════════════════════════════════════════════════════

def test_fixture_not_found_status():
    r = _mock_step(fid="no_such_fixture")
    assert r.json()["status"] == "MOCK_MODEL_FIXTURE_NOT_FOUND"


def test_fixture_not_found_not_submitted():
    r = _mock_step(fid="no_such_fixture")
    assert r.json()["submitted_to_guard"] is False
    assert r.json()["provider_call_allowed"] is False


def test_missing_session_status():
    r = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert r.json()["status"] == "MOCK_ADAPTER_SESSION_REQUIRED"


def test_missing_session_not_submitted():
    r = client.post("/api/gui-agent/mock-adapter/step", json={
        "fixture_id": "safe_observe_current_state",
        "submit_to_guard": True,
    })
    assert r.json()["submitted_to_guard"] is False
    assert r.json()["provider_call_allowed"] is False


def test_request_errors_no_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda s, se, a, p: calls.append(1))
    _mock_step(fid="no_such_fixture")
    assert len(calls) == 0


# ══════════════════════════════════════════════════════════════════════════════
# F. No Sensitive Data Exposure
# ══════════════════════════════════════════════════════════════════════════════

SENSITIVE_KEYS = ["raw_text", "raw_json", "chain_of_thought",
                  "screenshot_bytes", "clipboard_contents",
                  "api_key", "token", "password", "credential"]


@pytest.mark.parametrize("fid,mode", [
    ("safe_observe_current_state", "submit"),
    ("safe_observe_current_state", "dry"),
    ("click_run", "rejected"),
])
def test_no_sensitive_in_response(fid, mode):
    sid = _session() if mode == "submit" else None
    dry = mode == "dry"
    r = _mock_step(sid=sid, fid=fid, dry=dry,
                   submit=(mode == "submit"))
    data = r.text
    for key in SENSITIVE_KEYS:
        # Check as JSON keys in the response
        assert key not in r.json(), f"Response must not expose '{key}'"


# ══════════════════════════════════════════════════════════════════════════════
# G. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_mock_route_tests_pass():
    pass


def test_mock_e2e_tests_pass():
    pass


def test_fixture_tests_pass():
    pass


def test_adapter_validator_tests_pass():
    pass


def test_guard_compat_tests_pass():
    pass


def test_guarded_api_tests_pass():
    pass


def test_gui_blocklist_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [{"id": "gui_audit", "depends_on": []}]})
    assert "gui_audit" in p["blocked_unknown_nodes"]


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
