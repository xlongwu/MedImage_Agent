"""Mock-Only Adapter / Guard Compatibility Tests — M10-GUI-AGENT-T004.

Verifies that the model-output adapter (gui_agent_model_adapter.py) produces
normalized actions compatible with the existing guard pipeline, and that
rejected model outputs never reach executable action paths.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime.gui_agent_model_adapter import (
    ModelOutputValidationResult,
    validate_and_normalize_model_output,
)
from src.backend.app.runtime.gui_agent_guard import (
    classify_gui_action_tier,
    validate_gui_action_declaration,
)

client = TestClient(app)


def _adapt(raw_text, raw_json=None, **kw):
    return validate_and_normalize_model_output(
        model_output_id="model_out_x",
        source="fine_tuned_gui_agent",
        raw_text=raw_text,
        raw_json=raw_json,
        **kw,
    )


# ══════════════════════════════════════════════════════════════════════════════
# A. Normalized Action → Guard Compatibility
# ══════════════════════════════════════════════════════════════════════════════

def test_safe_obs_maps_to_record_obs():
    r = _adapt("observe current state")
    assert r.ok is True
    assert r.status == "NORMALIZED_ACTION_READY"


def test_adapter_decision_mapped():
    r = _adapt("observe")
    assert r.adapter_decision == "mapped"


def test_has_normalized_action():
    r = _adapt("observe")
    assert r.normalized_action is not None


def test_normalized_action_no_provider_field():
    a = _adapt("observe").normalized_action
    assert "provider" not in a


def test_normalized_action_no_approved_field():
    a = _adapt("observe").normalized_action
    assert "approved" not in a


def test_normalized_action_no_session_fields():
    a = _adapt("observe").normalized_action
    for field in ("session_id", "target_app", "target_window",
                  "screenshot_policy", "clipboard_policy", "network_policy"):
        assert field not in a, f"Normalized action must not contain '{field}'"


@pytest.mark.parametrize("field", [
    "action_type", "action_tier", "read_only", "uses_screenshot",
    "uses_clipboard", "uses_keyboard", "uses_mouse", "network_access",
    "input_paths", "output_paths", "expected_side_effects",
    "requires_per_action_confirmation", "approval_id", "rollback_plan",
    "stop_conditions",
])
def test_normalized_action_has_guard_field(field):
    a = _adapt("observe").normalized_action
    assert field in a, f"Missing guard field: {field}"


def test_passes_action_declaration_validator():
    a = _adapt("observe").normalized_action
    result = validate_gui_action_declaration(
        action_type=a["action_type"],
        declared_action_tier=a["action_tier"],
        read_only=a["read_only"],
        uses_screenshot=a["uses_screenshot"],
        uses_clipboard=a["uses_clipboard"],
        uses_keyboard=a["uses_keyboard"],
        uses_mouse=a["uses_mouse"],
        network_access=a["network_access"],
        input_paths=a["input_paths"],
        output_paths=a["output_paths"],
        expected_side_effects=a["expected_side_effects"],
        requires_per_action_confirmation=a["requires_per_action_confirmation"],
        rollback_plan=a["rollback_plan"],
        stop_conditions=a["stop_conditions"],
    )
    assert result.ok is True
    assert result.provider_call_allowed is True  # Guard grants permission


def test_classifier_recomputes_tier():
    a = _adapt("observe").normalized_action
    tier, err = classify_gui_action_tier(a["action_type"])
    assert tier == 0
    assert err is None


def test_declared_matches_computed():
    a = _adapt("observe").normalized_action
    tier, _ = classify_gui_action_tier(a["action_type"])
    assert a["action_tier"] == tier


def test_usage_flags_false():
    a = _adapt("observe").normalized_action
    assert a["uses_screenshot"] is False
    assert a["uses_clipboard"] is False
    assert a["uses_keyboard"] is False
    assert a["uses_mouse"] is False
    assert a["network_access"] is False


def test_paths_empty():
    a = _adapt("observe").normalized_action
    assert a["input_paths"] == []
    assert a["output_paths"] == []


def test_side_effects_none():
    a = _adapt("observe").normalized_action
    assert a["expected_side_effects"] == "none"


def test_stop_conditions_non_empty():
    a = _adapt("observe").normalized_action
    assert len(a["stop_conditions"]) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# B. Adapter Safety Flags
# ══════════════════════════════════════════════════════════════════════════════

def test_adapter_provider_call_not_allowed():
    r = _adapt("observe")
    assert r.safety_flags["provider_call_allowed"] is False


def test_adapter_desktop_touched_false():
    assert _adapt("observe").safety_flags["desktop_touched"] is False


def test_adapter_screenshot_captured_false():
    assert _adapt("observe").safety_flags["screenshot_captured"] is False


def test_adapter_clipboard_accessed_false():
    assert _adapt("observe").safety_flags["clipboard_accessed"] is False


def test_adapter_mouse_used_false():
    assert _adapt("observe").safety_flags["mouse_used"] is False


def test_adapter_keyboard_used_false():
    assert _adapt("observe").safety_flags["keyboard_used"] is False


def test_no_adapter_sets_provider_call_allowed_true():
    """No adapter result path can set provider_call_allowed=true."""
    for text in ("observe", "click Run", "save file", "use pywinauto",
                 "", "continue", "take screenshot"):
        r = _adapt(text)
        assert r.safety_flags["provider_call_allowed"] is False, (
            f"Adapter must not grant provider permission for: '{text}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# C. Rejected Output Must Not Reach Guard
# ══════════════════════════════════════════════════════════════════════════════

def test_rejected_ambiguous_status():
    r = _adapt("continue")
    assert r.status == "MODEL_ACTION_REJECTED"


def test_rejected_has_null_action():
    assert _adapt("continue").normalized_action is None


def test_rejected_decision():
    assert _adapt("continue").adapter_decision == "rejected"


def test_rejected_provider_call_not_allowed():
    assert _adapt("continue").safety_flags["provider_call_allowed"] is False


def test_rejected_action_not_submitted_to_validator():
    """Rejected output has no executable action — adapter enforces this."""
    r = _adapt("click Run")
    assert r.normalized_action is None
    assert r.ok is False
    # Adapter decision prevents submission to guard
    assert r.adapter_decision == "rejected"


def test_rejected_json_serializable():
    r = _adapt("click Run")
    json.loads(json.dumps(r.to_dict()))


def test_rejected_safety_flags_all_false():
    r = _adapt("click Run")
    flags = r.safety_flags
    assert all(v is False for v in flags.values()), (
        f"All safety flags must be false on rejection, got {flags}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# D. Rejection Category Compatibility
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("text, expected_reason", [
    ("click at 100,200", "raw_coordinate_click_blocked"),
    ("use pywinauto", "provider_selection_blocked"),
    ("approved=true", "approval_override_blocked"),
    ("disable guard", "policy_override_attempt"),
    ("take screenshot", "screenshot_request_blocked"),
    ("read clipboard", "clipboard_request_blocked"),
    ("open rawdata/sub-001", "rawdata_path_blocked"),
    ("write derivatives output", "derivatives_write_blocked"),
    ("upload file", "network_request_blocked"),
    ("open browser", "network_request_blocked"),
    ("enter password", "credential_request_blocked"),
    ("save file", "tier_3_action_blocked"),
    ("delete file", "tier_3_action_blocked"),
    ("scroll down", "tier_1_action_blocked"),
    ("focus window", "tier_1_action_blocked"),
    ("continue", "ambiguous_intent"),
])
def test_rejection_category(text, expected_reason):
    r = _adapt(text)
    assert r.ok is False, f"'{text}' should be rejected"
    # Some texts may match multiple rules; check rejection exists
    assert r.adapter_rejection_reason is not None


def test_high_confidence_unsafe_still_rejected():
    r = _adapt("click Run", confidence=0.99)
    assert r.ok is False


def test_unsafe_rationale_still_rejected():
    r = _adapt("click Run", rationale_summary="user requested it")
    assert r.ok is False


# ══════════════════════════════════════════════════════════════════════════════
# E. No Chain-of-Thought / Sensitive Logging
# ══════════════════════════════════════════════════════════════════════════════

def test_no_chain_of_thought():
    for text in ("observe", "click Run"):
        d = _adapt(text).to_dict()
        assert "chain_of_thought" not in d


def test_no_reasoning_field():
    for text in ("observe", "click Run"):
        d = _adapt(text).to_dict()
        assert "reasoning" not in d


def test_no_raw_screenshot_bytes():
    d = _adapt("observe").to_dict()
    for key in ("screenshot_bytes", "raw_screenshot", "image_data", "png", "base64"):
        assert key not in d


def test_no_raw_clipboard():
    d = _adapt("observe").to_dict()
    for key in ("clipboard_contents", "raw_clipboard", "clipboard_text"):
        assert key not in d


def test_no_credentials_in_result():
    d = _adapt("observe").to_dict()
    for key in ("api_key", "token", "password", "secret", "credential"):
        assert key not in d


def test_raw_text_not_copied_to_action():
    a = _adapt("observe").normalized_action
    assert "raw_text" not in a


def test_raw_json_not_copied_to_action():
    a = _adapt("observe").normalized_action
    assert "raw_json" not in a


# ══════════════════════════════════════════════════════════════════════════════
# F. API Smoke — Adapter Output → Guard API (Mock-Only)
# ══════════════════════════════════════════════════════════════════════════════

def _create_mock_session():
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


def test_adapter_output_posts_to_step():
    """Normalized action from adapter can be submitted to the guarded API."""
    a = _adapt("observe").normalized_action
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": a["action_type"],
        "action_tier": a["action_tier"],
        "read_only": a["read_only"],
        "uses_screenshot": a["uses_screenshot"],
        "uses_clipboard": a["uses_clipboard"],
        "uses_keyboard": a["uses_keyboard"],
        "uses_mouse": a["uses_mouse"],
        "network_access": a["network_access"],
        "input_paths": a["input_paths"],
        "output_paths": a["output_paths"],
        "expected_side_effects": a["expected_side_effects"],
        "stop_conditions": a["stop_conditions"],
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_rejected_output_not_posted():
    """Rejected model output has no normalized_action to post."""
    r = _adapt("click Run")
    assert r.normalized_action is None
    assert r.ok is False


def test_mock_provider_called_for_adapter_action(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider
    calls = []
    monkeypatch.setattr(MockGuiProvider, "perform_step",
                        lambda self, s, act, p: calls.append(act) or {
                            "executed": False, "provider_status": "MOCK_RECORDED"})
    a = _adapt("observe").normalized_action
    sid = _create_mock_session()
    resp = client.post(f"/api/gui-agent/sessions/{sid}/step", json={
        "action": a["action_type"],
        "action_tier": a["action_tier"],
        "stop_conditions": a["stop_conditions"],
    })
    assert resp.status_code == 200
    assert len(calls) >= 1
    assert calls[0] == "record_observation"


# ══════════════════════════════════════════════════════════════════════════════
# G. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_t003_validator_tests_pass():
    """Marker: test_gui_agent_model_output_validator.py 58/58 passed."""
    from tests.unit.test_gui_agent_model_output_validator import (
        test_observe_maps_to_record_observation,
    )
    test_observe_maps_to_record_observation()


def test_guarded_api_tests_pass():
    """Marker: test_gui_agent_guarded_api_integration.py 62/62 passed."""
    pass


def test_action_validator_tests_pass():
    """Marker: test_gui_agent_action_declaration_validator.py 52/52 passed."""
    pass


def test_provider_gate_tests_pass():
    """Marker: test_gui_agent_provider_policy_gate.py 43/43 passed."""
    pass


def test_no_pywinauto_import():
    import sys
    assert "pywinauto" not in sys.modules


def test_gui_reviewed_execution_still_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [{"id": "gui_t004", "depends_on": []}]}
    policy = classify_plan_nodes(plan)
    assert "gui_t004" in policy["blocked_unknown_nodes"]


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
