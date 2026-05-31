"""Tests for GUI Agent Session Declaration Validator — M9-GUI-GUARD-T003.

Tests verify that:
  - Valid mock session declarations pass.
  - Sandbox/target/tier/file/rawdata/derivatives/screenshot/clipboard/network
    policy violations are blocked.
  - Provider policy gate still works (regression from T002).
  - API integration: valid sessions return 200, invalid return 403.
  - Reviewed execution GUI blocklist and SPM/DPABI/GPU allowlists do not regress.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime.gui_agent_guard import (
    GuiGuardResult,
    validate_gui_session_declaration,
)

client = TestClient(app)


# ── Helper: build a valid minimal mock session declaration ──

def _valid_session(**overrides):
    """Return kwargs for a valid T003 session declaration."""
    base = {
        "provider": "mock",
        "gui_sandbox_mode": True,
        "target_application": "MATLAB",
        "target_window": "SPM.*",
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
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# A. Valid Case
# ══════════════════════════════════════════════════════════════════════════════

def test_valid_mock_session_passes():
    result = validate_gui_session_declaration(**_valid_session())
    assert result.ok is True
    assert result.provider_call_allowed is True
    assert result.status == "GUI_GUARD_OK"


def test_valid_result_json_serializable():
    result = validate_gui_session_declaration(**_valid_session())
    d = result.to_dict()
    raw = json.dumps(d, ensure_ascii=False)
    back = json.loads(raw)
    assert back["ok"] is True
    assert back["provider_call_allowed"] is True


def test_provider_call_allowed_only_for_valid():
    result = validate_gui_session_declaration(**_valid_session())
    assert result.provider_call_allowed is True


# ══════════════════════════════════════════════════════════════════════════════
# B. Sandbox / Provider
# ══════════════════════════════════════════════════════════════════════════════

def test_sandbox_mode_false_blocked():
    result = validate_gui_session_declaration(**_valid_session(gui_sandbox_mode=False))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SANDBOX_REQUIRED"


def test_provider_mock_passes():
    result = validate_gui_session_declaration(**_valid_session(provider="mock"))
    assert result.ok is True


def test_provider_pywinauto_sets_blocked_provider():
    """Even though provider gate runs separately, session validator
    normalizes and records the provider.  The provider gate itself
    must be called before session validation."""
    result = validate_gui_session_declaration(**_valid_session(provider="pywinauto"))
    # Session validator normalizes but does NOT block non-mock here;
    # that's the provider gate's job.  Session passes on its own fields.
    assert result.ok is True
    assert result.provider == "pywinauto"


# ══════════════════════════════════════════════════════════════════════════════
# C. Target Scope
# ══════════════════════════════════════════════════════════════════════════════

def test_missing_target_application_blocked():
    result = validate_gui_session_declaration(**_valid_session(target_application=None))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_TARGET_SCOPE_REQUIRED"


def test_empty_target_application_blocked():
    result = validate_gui_session_declaration(**_valid_session(target_application=""))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_TARGET_SCOPE_REQUIRED"


def test_missing_target_window_blocked():
    result = validate_gui_session_declaration(**_valid_session(target_window=None))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_TARGET_SCOPE_REQUIRED"


def test_empty_target_window_blocked():
    result = validate_gui_session_declaration(**_valid_session(target_window=""))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_TARGET_SCOPE_REQUIRED"


# ══════════════════════════════════════════════════════════════════════════════
# D. Action Tiers
# ══════════════════════════════════════════════════════════════════════════════

def test_tier_0_passes():
    result = validate_gui_session_declaration(**_valid_session(allowed_action_tiers=[0]))
    assert result.ok is True


def test_empty_tiers_blocked():
    result = validate_gui_session_declaration(**_valid_session(allowed_action_tiers=[]))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_TIER_BLOCKED"


def test_tier_1_blocked():
    result = validate_gui_session_declaration(**_valid_session(allowed_action_tiers=[1]))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_TIER_BLOCKED"


def test_tier_2_blocked():
    result = validate_gui_session_declaration(**_valid_session(allowed_action_tiers=[2]))
    assert result.ok is False


def test_tier_3_blocked():
    result = validate_gui_session_declaration(**_valid_session(allowed_action_tiers=[3]))
    assert result.ok is False


def test_mixed_tiers_blocked():
    result = validate_gui_session_declaration(**_valid_session(allowed_action_tiers=[0, 1]))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_TIER_BLOCKED"


def test_non_int_tier_blocked():
    result = validate_gui_session_declaration(**_valid_session(allowed_action_tiers=["0"]))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_ACTION_TIER_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# E. File Scope
# ══════════════════════════════════════════════════════════════════════════════

def test_valid_file_scope_passes():
    result = validate_gui_session_declaration(
        **_valid_session(file_scope=["outputs/work/gui_agent/"])
    )
    assert result.ok is True


def test_missing_file_scope_blocked():
    result = validate_gui_session_declaration(**_valid_session(file_scope=None))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_empty_file_scope_blocked():
    result = validate_gui_session_declaration(**_valid_session(file_scope=[]))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_rawdata_file_scope_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(file_scope=["rawdata/sub-001/"])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_data_file_scope_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(file_scope=["data/sub-001/"])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_derivatives_write_scope_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(file_scope=["derivatives/output/"])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_traversal_file_scope_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(file_scope=["../etc/passwd"])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_arbitrary_absolute_path_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(file_scope=["/etc/passwd"])
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# F. High-Risk Booleans
# ══════════════════════════════════════════════════════════════════════════════

def test_allow_rawdata_access_true_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(allow_rawdata_access=True)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_allow_derivatives_write_true_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(allow_derivatives_write=True)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_FILE_SCOPE_BLOCKED"


def test_human_present_false_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(human_present=False)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_HUMAN_REQUIRED"


def test_emergency_abort_false_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(emergency_abort_enabled=False)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_EMERGENCY_ABORT_REQUIRED"


def test_audit_log_required_false_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(audit_log_required=False)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_AUDIT_REQUIRED"


# ══════════════════════════════════════════════════════════════════════════════
# G. Policy Fields
# ══════════════════════════════════════════════════════════════════════════════

def test_screenshot_disabled_passes():
    result = validate_gui_session_declaration(
        **_valid_session(screenshot_policy="disabled")
    )
    assert result.ok is True


def test_screenshot_ephemeral_blocked_in_t003():
    result = validate_gui_session_declaration(
        **_valid_session(screenshot_policy="ephemeral_only")
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SCREENSHOT_BLOCKED"


def test_screenshot_persist_raw_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(screenshot_policy="persist_raw")
    )
    assert result.ok is False


def test_clipboard_read_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(clipboard_policy="read")
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_CLIPBOARD_BLOCKED"


def test_clipboard_read_write_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(clipboard_policy="read_write")
    )
    assert result.ok is False


def test_network_local_only_blocked_in_t003():
    result = validate_gui_session_declaration(
        **_valid_session(network_policy="local_only")
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_NETWORK_BLOCKED"


def test_network_unrestricted_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(network_policy="unrestricted")
    )
    assert result.ok is False


def test_external_app_any_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(external_app_policy="any_app")
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_EXTERNAL_APP_BLOCKED"


def test_redaction_policy_invalid_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(redaction_policy="none")
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SESSION_INVALID"


# ══════════════════════════════════════════════════════════════════════════════
# H. Limits
# ══════════════════════════════════════════════════════════════════════════════

def test_duration_300_passes():
    result = validate_gui_session_declaration(
        **_valid_session(duration_limit_seconds=300)
    )
    assert result.ok is True


def test_duration_0_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(duration_limit_seconds=0)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SESSION_INVALID"


def test_duration_exceeds_max_blocked():
    result = validate_gui_session_declaration(
        **_valid_session(duration_limit_seconds=301)
    )
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SESSION_INVALID"


def test_step_limit_20_passes():
    result = validate_gui_session_declaration(**_valid_session(step_limit=20))
    assert result.ok is True


def test_step_limit_0_blocked():
    result = validate_gui_session_declaration(**_valid_session(step_limit=0))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SESSION_INVALID"


def test_step_limit_exceeds_max_blocked():
    result = validate_gui_session_declaration(**_valid_session(step_limit=21))
    assert result.ok is False
    assert result.error_code == "GUI_GUARD_SESSION_INVALID"


# ══════════════════════════════════════════════════════════════════════════════
# I. API Integration
# ══════════════════════════════════════════════════════════════════════════════

def test_api_valid_mock_session_200():
    resp = client.post("/api/gui-agent/sessions", json={
        "provider": "mock",
        "target_app": "MATLAB",
        "target_window": "SPM.*",
        "allowed_action_tiers": [0],
        "file_scope": ["outputs/work/gui_agent/"],
        "approved": True,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_invalid_session_blocked():
    """Session with Tier 1 should be blocked."""
    resp = client.post("/api/gui-agent/sessions", json={
        "provider": "mock",
        "target_app": "MATLAB",
        "target_window": "SPM.*",
        "allowed_action_tiers": [1],
        "file_scope": ["outputs/work/gui_agent/"],
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_ACTION_TIER_BLOCKED"


def test_api_screenshot_persist_raw_blocked():
    resp = client.post("/api/gui-agent/sessions", json={
        "provider": "mock",
        "target_app": "MATLAB",
        "target_window": "SPM.*",
        "allowed_action_tiers": [0],
        "file_scope": ["outputs/work/gui_agent/"],
        "screenshot_policy": "persist_raw",
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "GUI_GUARD_SCREENSHOT_BLOCKED"


def test_api_pywinauto_still_blocked_before_session():
    """Provider gate runs first — pywinauto blocked before session validation."""
    resp = client.post("/api/gui-agent/sessions", json={
        "provider": "pywinauto",
        "target_app": "MATLAB",
        "target_window": "SPM.*",
        "allowed_action_tiers": [0],
        "file_scope": ["outputs/work/gui_agent/"],
    })
    assert resp.status_code == 403
    # Provider gate error, not session error
    assert "pywinauto" in resp.json()["detail"]["message"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# J. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_t002_provider_gate_still_works():
    """Provider policy gate from T002 still functions correctly."""
    from src.backend.app.runtime.gui_agent_guard import validate_gui_provider_policy
    result = validate_gui_provider_policy(provider="pywinauto")
    assert result.ok is False
    assert result.provider_call_allowed is False


def test_gui_reviewed_execution_still_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "gui_t003_check", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gui_t003_check" in policy["blocked_unknown_nodes"]


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
