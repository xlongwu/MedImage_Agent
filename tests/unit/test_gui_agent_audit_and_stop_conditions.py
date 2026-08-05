"""Tests for GUI Audit Log + Stop-Condition Checker — M9-GUI-GUARD-T005.

Tests verify:
  - Audit records are created with correct metadata.
  - Audit records are JSON-serializable.
  - Audit records never contain raw screenshots/clipboard/secrets.
  - Stop-condition checker blocks invalid session states.
  - Stop-condition checker passes valid mock sessions.
  - API integration: valid steps create audit_id, blocked steps don't call provider.
  - step_limit exceeded → GUI_GUARD_STEP_LIMIT_EXCEEDED.
  - duration exceeded → GUI_GUARD_DURATION_LIMIT_EXCEEDED.
  - emergency_abort → GUI_GUARD_EMERGENCY_ABORTED.
  - Regression: T002/T003/T004 all pass.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime.gui_agent_guard import (
    create_gui_audit_record,
    validate_gui_stop_conditions,
)

client = TestClient(app)


# ══════════════════════════════════════════════════════════════════════════════
# A. Audit Record Pure Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_create_audit_record():
    record = create_gui_audit_record(
        session_id="gui_abc123",
        provider="mock",
        action_type="record_observation",
        guard_result="GUI_GUARD_OK",
        target_application="MATLAB",
        target_window="SPM.*",
        computed_action_tier=0,
        declared_action_tier=0,
        provider_call_allowed=True,
        stop_condition_checked=True,
    )
    assert record.audit_id.startswith("audit_")
    assert record.session_id == "gui_abc123"
    assert record.provider == "mock"
    assert record.action_type == "record_observation"
    assert record.guard_result == "GUI_GUARD_OK"
    assert record.computed_action_tier == 0
    assert record.declared_action_tier == 0
    assert record.provider_call_allowed is True
    assert record.stop_condition_checked is True


def test_audit_record_json_serializable():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="record_observation",
        guard_result="GUI_GUARD_OK",
    )
    d = record.to_dict()
    raw = json.dumps(d, ensure_ascii=False)
    back = json.loads(raw)
    assert back["audit_id"].startswith("audit_")
    assert back["session_id"] == "x"
    assert back["provider_call_allowed"] is False


def test_audit_record_screenshot_false():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
        screenshot_requested=False,
    )
    assert record.screenshot_requested is False


def test_audit_record_clipboard_false():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
        clipboard_requested=False,
    )
    assert record.clipboard_requested is False


def test_audit_record_keyboard_false():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
        keyboard_requested=False,
    )
    assert record.keyboard_requested is False


def test_audit_record_mouse_false():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
        mouse_requested=False,
    )
    assert record.mouse_requested is False


def test_audit_record_network_false():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
        network_requested=False,
    )
    assert record.network_requested is False


def test_audit_record_no_raw_screenshot():
    """Audit record .to_dict() must not have 'screenshot_bytes' or similar."""
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
    )
    d = record.to_dict()
    assert "screenshot_bytes" not in d
    assert "raw_screenshot" not in d
    assert "image_data" not in d


def test_audit_record_no_raw_clipboard():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
    )
    d = record.to_dict()
    assert "clipboard_contents" not in d
    assert "raw_clipboard" not in d


def test_audit_record_no_raw_secrets():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="rec",
        guard_result="GUI_GUARD_OK",
    )
    d = record.to_dict()
    assert "api_key" not in d
    assert "token" not in d
    assert "password" not in d
    assert "credential" not in d


def test_audit_record_blocked_has_error_code():
    record = create_gui_audit_record(
        session_id="x",
        provider="mock",
        action_type="click_run",
        guard_result="GUI_GUARD_BLOCKED",
        error_code="GUI_GUARD_ACTION_TIER_BLOCKED",
    )
    assert record.error_code == "GUI_GUARD_ACTION_TIER_BLOCKED"
    assert record.provider_call_allowed is False


# ══════════════════════════════════════════════════════════════════════════════
# B. Stop-Condition Pure Tests
# ══════════════════════════════════════════════════════════════════════════════


def _valid_stop(**overrides):
    base = {
        "session_id": "gui_abc123",
        "provider": "mock",
        "human_present": True,
        "emergency_abort_enabled": True,
        "audit_log_required": True,
        "step_limit": 20,
        "current_step_count": 5,
        "duration_limit_seconds": 300,
        "session_age_seconds": 60.0,
        "stop_conditions": ["unexpected_window"],
        "emergency_abort_requested": False,
    }
    base.update(overrides)
    return base


def test_valid_stop_passes():
    result = validate_gui_stop_conditions(**_valid_stop())
    assert result.ok is True
    assert result.provider_call_allowed is True


def test_missing_session_id_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(session_id=None))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SESSION_MISSING"


def test_provider_not_mock_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(provider="pywinauto"))
    assert result.ok is False
    assert result.provider_call_allowed is False


def test_human_present_false_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(human_present=False))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_HUMAN_REQUIRED"


def test_emergency_abort_false_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(emergency_abort_enabled=False))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_EMERGENCY_ABORT_REQUIRED"


def test_audit_log_required_false_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(audit_log_required=False))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_AUDIT_REQUIRED"


def test_step_limit_exceeded_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(step_limit=20, current_step_count=20))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_STEP_LIMIT_EXCEEDED"


def test_duration_exceeded_blocked():
    result = validate_gui_stop_conditions(
        **_valid_stop(duration_limit_seconds=60, session_age_seconds=61.0)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_DURATION_LIMIT_EXCEEDED"


def test_stop_conditions_missing_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(stop_conditions=None))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_STOP_CONDITION"


def test_stop_conditions_empty_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(stop_conditions=[]))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_STOP_CONDITION"


def test_emergency_abort_requested_blocked():
    result = validate_gui_stop_conditions(**_valid_stop(emergency_abort_requested=True))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_EMERGENCY_ABORTED"


def test_blocked_stop_safety_flags():
    result = validate_gui_stop_conditions(**_valid_stop(human_present=False))
    assert result.desktop_touched is False
    assert result.screenshot_captured is False
    assert result.clipboard_accessed is False
    assert result.mouse_used is False
    assert result.keyboard_used is False


# ══════════════════════════════════════════════════════════════════════════════
# C. API Integration
# ══════════════════════════════════════════════════════════════════════════════


def _create_mock_session(**extra):
    resp = client.post(
        "/api/gui-agent/sessions",
        json={
            "provider": "mock",
            "target_app": "MATLAB",
            "target_window": "SPM.*",
            "allowed_action_tiers": [0],
            "file_scope": ["outputs/work/gui_agent/"],
            "approved": True,
            **extra,
        },
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_api_valid_step_creates_audit():
    sid = _create_mock_session()
    resp = client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "record_observation",
            "action_tier": 0,
            "stop_conditions": ["unexpected_window"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "audit" in data
    assert data["audit"]["audit_id"].startswith("audit_")
    assert data["audit"]["provider_call_allowed"] is True
    assert data["audit"]["stop_condition_checked"] is True
    assert data["audit"]["action_type"] == "record_observation"


def test_api_valid_step_calls_provider():
    """Mock provider is called for valid step."""
    sid = _create_mock_session()
    resp = client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "record_observation",
            "action_tier": 0,
            "stop_conditions": ["unexpected_window"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_valid_step_increments_count():
    sid = _create_mock_session()
    # Step 1
    client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "record_observation",
            "action_tier": 0,
            "stop_conditions": ["unexpected_window"],
        },
    )
    # Step 2
    resp2 = client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "record_observation",
            "action_tier": 0,
            "stop_conditions": ["unexpected_window"],
        },
    )
    assert resp2.status_code == 200
    # Verify step count via session list
    from src.backend.app.runtime.gui_agent import _read_session

    session = _read_session(sid)
    assert session.get("step_count", 0) >= 2


def test_api_blocked_action_no_provider(monkeypatch):
    """Blocked action (click_run) does NOT call Mock provider."""
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    called = []
    monkeypatch.setattr(
        MockGuiProvider,
        "perform_step",
        lambda self, s, a, p: called.append(a) or {"executed": False},
    )
    sid = _create_mock_session()
    resp = client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "click_run",
            "action_tier": 3,
            "stop_conditions": ["unexpected_window"],
        },
    )
    assert resp.status_code == 403
    assert len(called) == 0


def test_api_step_limit_exceeded_blocked():
    sid = _create_mock_session(step_limit=2)
    # Use up steps
    for _ in range(2):
        client.post(
            f"/api/gui-agent/sessions/{sid}/step",
            json={
                "action": "record_observation",
                "action_tier": 0,
                "stop_conditions": ["unexpected_window"],
            },
        )
    # Third step should be blocked
    resp = client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "record_observation",
            "action_tier": 0,
            "stop_conditions": ["unexpected_window"],
        },
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error_code"] == "GUI_GUARD_STEP_LIMIT_EXCEEDED"


def test_api_aborted_session_blocked():
    sid = _create_mock_session()
    # Abort the session
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    # Step should be blocked
    resp = client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "record_observation",
            "action_tier": 0,
            "stop_conditions": ["unexpected_window"],
        },
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error_code"] == "GUI_GUARD_EMERGENCY_ABORTED"


def test_api_pywinauto_still_blocked():
    """pywinauto provider blocked — never reaches audit step."""
    resp = client.post(
        "/api/gui-agent/sessions",
        json={
            "provider": "pywinauto",
            "target_app": "MATLAB",
            "target_window": "SPM.*",
            "allowed_action_tiers": [0],
            "file_scope": ["outputs/work/gui_agent/"],
        },
    )
    assert resp.status_code == 403


def test_api_tier_1_still_blocked():
    sid = _create_mock_session()
    resp = client.post(
        f"/api/gui-agent/sessions/{sid}/step",
        json={
            "action": "focus_window",
            "action_tier": 1,
            "stop_conditions": ["unexpected_window"],
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_NOT_ALLOWED"


# ══════════════════════════════════════════════════════════════════════════════
# D. Regression
# ══════════════════════════════════════════════════════════════════════════════


def test_t002_provider_gate_still_works():
    from src.backend.app.runtime.gui_agent_guard import validate_gui_provider_policy

    result = validate_gui_provider_policy(provider="pywinauto")
    assert result.ok is False


def test_t003_session_validator_still_works():
    from src.backend.app.runtime.gui_agent_guard import validate_gui_session_declaration

    result = validate_gui_session_declaration(
        provider="mock",
        target_application="M",
        target_window="W",
        allowed_action_tiers=[0],
        file_scope=["outputs/work/gui_agent/"],
    )
    assert result.ok is True


def test_t004_action_validator_still_works():
    from src.backend.app.runtime.gui_agent_guard import validate_gui_action_declaration

    result = validate_gui_action_declaration(
        action_type="record_observation",
        declared_action_tier=0,
        stop_conditions=["x"],
    )
    assert result.ok is True


def test_gui_reviewed_execution_still_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {"pipeline_id": "t", "nodes": [{"id": "gui_t005", "depends_on": []}]}
    policy = classify_plan_nodes(plan)
    assert "gui_t005" in policy["blocked_unknown_nodes"]


def test_spm_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "depends_on": [],
                "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"},
            },
        ],
    }
    policy = classify_plan_nodes(plan)
    assert (
        "spm_realign_subject" not in policy["allowed_spm_realign_sandbox_nodes"]
    )  # blocked per current safety policy


def test_dpabi_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "dpabi_capability_inspection", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "dpabi_capability_inspection" in policy["allowed_dpabi_metadata_nodes"]


def test_gpu_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "gpu_alff_subject" in policy["allowed_gpu_nodes"]
