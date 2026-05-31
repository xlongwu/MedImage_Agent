"""Tests for GUI Action Declaration Validator — M9-GUI-GUARD-T004.

Tests verify:
  - Action tier classifier maps all 29 actions to correct tiers.
  - Only record_observation passes in T004.
  - All other Tier 0/1/2/3 actions blocked.
  - Usage flags (screenshot/clipboard/keyboard/mouse/network) blocked.
  - Path/side-effect/confirmation/rollback violations blocked.
  - Tier mismatch blocked.
  - API integration: valid mock record_observation → 200, blocked → 403.
  - Mock provider only called for valid actions.
  - PyWinAuto never called.
  - Regression: T002/T003/T004 blocklist all pass.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime.gui_agent_guard import (
    classify_gui_action_tier,
    validate_gui_action_declaration,
)

client = TestClient(app)


# ── Helper ──

def _valid_action(**overrides):
    base = {
        "action_type": "record_observation",
        "declared_action_tier": 0,
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
        "session_allowed_action_tiers": [0],
        "screenshot_policy": "disabled",
        "clipboard_policy": "disabled",
        "network_policy": "disabled",
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# A. Action Tier Classifier
# ══════════════════════════════════════════════════════════════════════════════

def test_record_observation_tier_0():
    tier, err = classify_gui_action_tier("record_observation")
    assert tier == 0
    assert err is None


def test_get_window_title_tier_0():
    tier, _ = classify_gui_action_tier("get_window_title")
    assert tier == 0


def test_screenshot_ephemeral_tier_0():
    tier, _ = classify_gui_action_tier("screenshot_ephemeral")
    assert tier == 0


def test_focus_window_tier_1():
    tier, _ = classify_gui_action_tier("focus_window")
    assert tier == 1


def test_scroll_tier_1():
    tier, _ = classify_gui_action_tier("scroll")
    assert tier == 1


def test_fill_form_field_tier_2():
    tier, _ = classify_gui_action_tier("fill_form_field_non_secret")
    assert tier == 2


def test_click_dry_run_tier_2():
    tier, _ = classify_gui_action_tier("click_dry_run")
    assert tier == 2


def test_click_run_tier_3():
    tier, _ = classify_gui_action_tier("click_run")
    assert tier == 3


def test_save_file_tier_3():
    tier, _ = classify_gui_action_tier("save_file")
    assert tier == 3


def test_read_clipboard_tier_3():
    tier, _ = classify_gui_action_tier("read_clipboard")
    assert tier == 3


def test_unknown_action_blocked():
    tier, err = classify_gui_action_tier("nonexistent_action")
    assert tier is None
    assert err is not None


def test_none_action_blocked():
    tier, err = classify_gui_action_tier(None)
    assert tier is None
    assert err is not None


def test_empty_action_blocked():
    tier, err = classify_gui_action_tier("")
    assert tier is None
    assert err is not None


# ══════════════════════════════════════════════════════════════════════════════
# B. Valid T004 Action
# ══════════════════════════════════════════════════════════════════════════════

def test_valid_record_observation_passes():
    result = validate_gui_action_declaration(**_valid_action())
    assert result.ok is True
    assert result.provider_call_allowed is True


def test_valid_result_json_serializable():
    result = validate_gui_action_declaration(**_valid_action())
    d = result.to_dict()
    raw = json.dumps(d, ensure_ascii=False)
    back = json.loads(raw)
    assert back["ok"] is True
    assert back["provider_call_allowed"] is True


# ══════════════════════════════════════════════════════════════════════════════
# C. Tier / Mismatch Blocks
# ══════════════════════════════════════════════════════════════════════════════

def test_declared_tier_mismatch_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(declared_action_tier=1)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_TIER_MISMATCH"


def test_declared_tier_missing_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(declared_action_tier=None)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_TIER_MISMATCH"


def test_tier_not_in_session_tiers_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(session_allowed_action_tiers=[1])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_TIER_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# D. Blocked Actions in T004 (non-record_observation)
# ══════════════════════════════════════════════════════════════════════════════

def test_get_window_title_blocked_in_t004():
    result = validate_gui_action_declaration(
        **_valid_action(action_type="get_window_title", declared_action_tier=0)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_NOT_ALLOWED"


def test_screenshot_ephemeral_blocked_in_t004():
    result = validate_gui_action_declaration(
        **_valid_action(action_type="screenshot_ephemeral", declared_action_tier=0)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_NOT_ALLOWED"


def test_focus_window_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(action_type="focus_window", declared_action_tier=1)
    )
    assert result.ok is False


def test_click_dry_run_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(action_type="click_dry_run", declared_action_tier=2)
    )
    assert result.ok is False


def test_click_run_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(action_type="click_run", declared_action_tier=3)
    )
    assert result.ok is False


def test_save_file_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(action_type="save_file", declared_action_tier=3)
    )
    assert result.ok is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Read-Only + Usage Flags
# ══════════════════════════════════════════════════════════════════════════════

def test_read_only_false_blocked():
    result = validate_gui_action_declaration(**_valid_action(read_only=False))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_READ_ONLY_REQUIRED"


def test_uses_screenshot_true_blocked():
    result = validate_gui_action_declaration(**_valid_action(uses_screenshot=True))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SCREENSHOT_BLOCKED"


def test_uses_clipboard_true_blocked():
    result = validate_gui_action_declaration(**_valid_action(uses_clipboard=True))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_CLIPBOARD_BLOCKED"


def test_uses_keyboard_true_blocked():
    result = validate_gui_action_declaration(**_valid_action(uses_keyboard=True))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_KEYBOARD_BLOCKED"


def test_uses_mouse_true_blocked():
    result = validate_gui_action_declaration(**_valid_action(uses_mouse=True))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_MOUSE_BLOCKED"


def test_network_access_true_blocked():
    result = validate_gui_action_declaration(**_valid_action(network_access=True))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_NETWORK_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# F. Paths + Side Effects
# ══════════════════════════════════════════════════════════════════════════════

def test_input_paths_non_empty_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(input_paths=["some/file.nii"])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_output_paths_non_empty_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(output_paths=["some/output.json"])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_side_effects_writes_file_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(expected_side_effects="writes_file")
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SIDE_EFFECT_BLOCKED"


def test_confirmation_required_blocked_in_t004():
    result = validate_gui_action_declaration(
        **_valid_action(requires_per_action_confirmation=True)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_CONFIRMATION_UNSUPPORTED"


def test_rollback_non_none_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(rollback_plan="undo_click")
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_INVALID"


def test_stop_conditions_missing_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(stop_conditions=None)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_INVALID"


def test_stop_conditions_empty_blocked():
    result = validate_gui_action_declaration(
        **_valid_action(stop_conditions=[])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_INVALID"


# ══════════════════════════════════════════════════════════════════════════════
# G. API Integration
# ══════════════════════════════════════════════════════════════════════════════

def _create_mock_session():
    """Create a valid mock session and return session_id."""
    resp = client.post("/api/gui-agent/sessions", json={
        "provider": "mock",
        "target_app": "MATLAB",
        "target_window": "SPM.*",
        "allowed_action_tiers": [0],
        "file_scope": ["outputs/work/gui_agent/"],
        "approved": True,
    })
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_api_record_observation_200():
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "record_observation",
        "parameters": {"window": "SPM"},
        "action_tier": 0,
        "read_only": True,
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_click_run_blocked():
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "click_run",
        "action_tier": 3,
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_NOT_ALLOWED"


def test_api_get_window_title_blocked():
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "get_window_title",
        "action_tier": 0,
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_NOT_ALLOWED"


def test_api_uses_mouse_true_blocked():
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "record_observation",
        "action_tier": 0,
        "uses_mouse": True,
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_MOUSE_BLOCKED"


def test_api_output_paths_non_empty_blocked():
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "record_observation",
        "action_tier": 0,
        "output_paths": ["some/file.txt"],
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_api_tier_mismatch_blocked():
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "record_observation",
        "action_tier": 1,
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_TIER_MISMATCH"


def test_api_pywinauto_session_step_blocked(monkeypatch):
    """Step on a pywinauto session is blocked at runtime provider gate.

    The runtime _provider() function calls validate_gui_provider_policy()
    and raises ValueError for non-mock providers.  This test verifies that
    the route handler catches ValueError and returns an error status.
    """
    # Create mock session, then patch it to look like pywinauto
    sid = _create_mock_session()
    from src.backend.app.runtime.gui_agent import _read_session as _orig_read
    from pathlib import Path as _Path

    def _patched(sid_inner):
        s = _orig_read(sid_inner)
        s["provider"] = "pywinauto"
        s["approved"] = True
        return s

    monkeypatch.setattr("src.backend.app.runtime.gui_agent._read_session", _patched)
    # Write session must return a valid Path for session path tracking
    monkeypatch.setattr(
        "src.backend.app.runtime.gui_agent._write_session",
        lambda s: _Path(f"outputs/work/gui_agent/sessions/{s.get('session_id', 'x')}"),
    )

    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "record_observation",
        "action_tier": 0,
        "stop_conditions": ["unexpected_window"],
    })
    # Runtime guard blocks pywinauto — expect error (403 from ValueError handler or 400)
    assert resp.status_code in (400, 403)


# ══════════════════════════════════════════════════════════════════════════════
# H. Provider Call Gating
# ══════════════════════════════════════════════════════════════════════════════

def test_mock_provider_called_for_valid_action(monkeypatch):
    """Mock provider perform_step is called for valid record_observation."""
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    called = []

    def _tracking_step(self, session, action, parameters):
        called.append(action)
        return {"executed": False, "provider_status": "MOCK_RECORDED"}

    monkeypatch.setattr(MockGuiProvider, "perform_step", _tracking_step)

    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "record_observation",
        "action_tier": 0,
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 200
    assert len(called) >= 1
    assert called[0] == "record_observation"


def test_mock_provider_not_called_for_blocked_action(monkeypatch):
    """Mock provider perform_step is NOT called for blocked actions."""
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    called = []

    def _tracking_step(self, session, action, parameters):
        called.append(action)
        return {"executed": False, "provider_status": "MOCK_RECORDED"}

    monkeypatch.setattr(MockGuiProvider, "perform_step", _tracking_step)

    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": "click_run",
        "action_tier": 3,
        "stop_conditions": ["unexpected_window"],
    })
    assert resp.status_code == 403
    assert len(called) == 0  # Provider NOT called


# ══════════════════════════════════════════════════════════════════════════════
# I. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_t002_provider_gate_still_works():
    from src.backend.app.runtime.gui_agent_guard import validate_gui_provider_policy
    result = validate_gui_provider_policy(provider="pywinauto")
    assert result.ok is False
    assert result.provider_call_allowed is False


def test_t003_session_validator_still_works():
    from src.backend.app.runtime.gui_agent_guard import validate_gui_session_declaration
    result = validate_gui_session_declaration(
        provider="mock",
        target_application="MATLAB",
        target_window="SPM.*",
        allowed_action_tiers=[0],
        file_scope=["outputs/work/gui_agent/"],
    )
    assert result.ok is True


def test_gui_reviewed_execution_still_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "gui_t004_check", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gui_t004_check" in policy["blocked_unknown_nodes"]


def test_spm_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" in policy["allowed_spm_realign_sandbox_nodes"]


def test_dpabi_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "dpabi_capability_inspection", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "dpabi_capability_inspection" in policy["allowed_dpabi_metadata_nodes"]


def test_gpu_allowlist_still_works():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_alff_subject" in policy["allowed_gpu_nodes"]
