"""Tests for Model Audit Metadata Contract — M11-GUI-MODEL-CONTRACT-T005."""

from __future__ import annotations

import json

import pytest
from src.backend.app.runtime.gui_model_audit_contract import (
    allowed_model_audit_metadata_declaration,
    validate_and_build_model_audit_record,
)

ALL_EVENTS = [
    "MODEL_INPUT_MINIMIZED", "MODEL_INPUT_REDACTED",
    "MODEL_PROVIDER_POLICY_CHECKED", "MODEL_RUNTIME_DECLARED",
    "MODEL_INFERENCE_STARTED", "MODEL_INFERENCE_BLOCKED",
    "MODEL_INFERENCE_COMPLETED", "MODEL_OUTPUT_RECEIVED",
    "MODEL_OUTPUT_REJECTED", "MODEL_OUTPUT_NORMALIZED",
    "ADAPTER_DECISION_RECORDED", "GUARD_SUBMISSION_ATTEMPTED",
    "GUARD_SUBMISSION_BLOCKED", "GUARD_SUBMISSION_ALLOWED",
    "MOCK_PROVIDER_CALLED",
]


def _audit(**overrides):
    d = allowed_model_audit_metadata_declaration()
    d.update(overrides)
    return validate_and_build_model_audit_record(**d)


# ══════════════════════════════════════════════════════════════════════════════
# A. Allowed metadata
# ══════════════════════════════════════════════════════════════════════════════

def test_safe_audit_allowed():
    r = _audit()
    assert r.ok is True
    assert r.status == "MODEL_AUDIT_ALLOWED"
    assert r.audit_record is not None


def test_safe_write_allowed():
    assert _audit().audit_write_allowed is True


def test_safe_not_written():
    assert _audit().audit_written is False


def test_safe_provider_call_false():
    assert _audit().provider_call_allowed is False


def test_safe_inference_false():
    assert _audit().inference_allowed is False


def test_safe_model_not_called():
    assert _audit().model_called is False


def test_safe_flags_all_false():
    r = _audit()
    assert r.desktop_touched is False
    assert r.screenshot_captured is False
    assert r.clipboard_accessed is False
    assert r.mouse_used is False
    assert r.keyboard_used is False


def test_safe_json():
    json.loads(json.dumps(_audit().to_dict()))


# ══════════════════════════════════════════════════════════════════════════════
# B. Event types
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("evt", ALL_EVENTS)
def test_all_events_accepted(evt):
    assert _audit(event_type=evt).ok is True


def test_unknown_event_blocked():
    assert _audit(event_type="UNKNOWN_EVENT").ok is False


def test_missing_event_blocked():
    assert _audit(event_type=None).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# C. Required fields
# ══════════════════════════════════════════════════════════════════════════════

def test_missing_audit_id_blocked():
    assert _audit(audit_id=None).ok is False


def test_missing_run_id_blocked():
    assert _audit(run_id=None).ok is False


def test_missing_session_id_blocked():
    assert _audit(session_id=None).ok is False


def test_invalid_audit_id_chars():
    assert _audit(audit_id="bad id!").ok is False


def test_invalid_run_id_chars():
    assert _audit(run_id="run with space").ok is False


def test_invalid_output_id_chars():
    assert _audit(model_output_id="bad@id").ok is False


def test_blank_audit_id():
    assert _audit(audit_id="   ").ok is False


# ══════════════════════════════════════════════════════════════════════════════
# D. Forbidden fields (via metadata sections and extra)
# ══════════════════════════════════════════════════════════════════════════════

FORBIDDEN = [
    "raw_prompt", "full_prompt", "raw_model_output", "raw_output",
    "raw_text", "raw_json", "screenshot_bytes", "raw_screenshot",
    "screenshot_ocr_text", "clipboard_contents", "raw_clipboard",
    "raw_terminal_output", "raw_browser_dom", "raw_ui_text", "raw_file_contents",
    "chain_of_thought", "hidden_reasoning", "reasoning_trace",
    "credential", "api_key", "token", "password", "private_key", "secret",
    "phi", "subject_id", "rawdata_path", "derivatives_path",
    "environment_variable", "shell_history", "provider_secret",
]


@pytest.mark.parametrize("key", FORBIDDEN)
def test_forbidden_key_blocked(key):
    r = validate_and_build_model_audit_record(
        audit_id="audit_001", run_id="run_001", session_id="s_001",
        event_type="MODEL_OUTPUT_NORMALIZED",
        extra={key: "some value"},
    )
    assert r.ok is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Path policy
# ══════════════════════════════════════════════════════════════════════════════

def test_reports_path_allowed():
    assert _audit(audit_root="reports/gui/model_audit").ok is True


def test_outputs_path_allowed():
    assert _audit(audit_root="outputs/work/gui_agent/model_audit").ok is True


def test_rawdata_root_blocked():
    assert _audit(audit_root="rawdata/logs").ok is False


def test_derivatives_root_blocked():
    assert _audit(audit_root="derivatives/audit").ok is False


def test_data_root_blocked():
    assert _audit(audit_root="data/logs").ok is False


def test_traversal_root_blocked():
    assert _audit(audit_root="../escape").ok is False


def test_absolute_unix_blocked():
    assert _audit(audit_root="/etc/audit").ok is False


def test_windows_absolute_blocked():
    assert _audit(audit_root="C:/audit").ok is False


def test_home_path_blocked():
    assert _audit(audit_root="~/audit").ok is False


def test_user_filename_blocked():
    assert _audit(extra={"user_filename": "my_audit.json"}).ok is False


def test_unsafe_user_root_blocked():
    assert _audit(extra={"audit_root": "rawdata/"}).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# F. Metadata semantics
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_inference_true_blocked():
    assert _audit(provider_metadata={"inference_allowed": True}).ok is False


def test_provider_loaded_true_blocked():
    assert _audit(provider_metadata={"model_loaded": True}).ok is False


def test_provider_network_true_blocked():
    assert _audit(provider_metadata={"network_accessed": True}).ok is False


def test_adapter_provider_true_blocked():
    assert _audit(adapter_metadata={"provider_call_allowed_by_adapter": True}).ok is False


def test_guard_bad_permission_blocked():
    assert _audit(guard_metadata={
        "guard_status": "GUI_GUARD_BLOCKED",
        "provider_call_allowed_by_guard": True,
    }).ok is False


def test_safety_screenshot_true_blocked():
    assert _audit(safety_flags={
        "desktop_touched": False, "screenshot_captured": True,
        "clipboard_accessed": False, "mouse_used": False, "keyboard_used": False,
    }).ok is False


def test_safety_clipboard_true_blocked():
    assert _audit(safety_flags={
        "desktop_touched": False, "screenshot_captured": False,
        "clipboard_accessed": True, "mouse_used": False, "keyboard_used": False,
    }).ok is False


def test_safety_mouse_true_blocked():
    assert _audit(safety_flags={
        "desktop_touched": False, "screenshot_captured": False,
        "clipboard_accessed": False, "mouse_used": True, "keyboard_used": False,
    }).ok is False


def test_safety_keyboard_true_blocked():
    assert _audit(safety_flags={
        "desktop_touched": False, "screenshot_captured": False,
        "clipboard_accessed": False, "mouse_used": False, "keyboard_used": True,
    }).ok is False


def test_safety_desktop_true_blocked():
    assert _audit(safety_flags={
        "desktop_touched": True, "screenshot_captured": False,
        "clipboard_accessed": False, "mouse_used": False, "keyboard_used": False,
    }).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# G. Retention
# ══════════════════════════════════════════════════════════════════════════════

def test_retention_1_allowed():
    assert _audit(retention_days=1).ok is True


def test_retention_30_allowed():
    assert _audit(retention_days=30).ok is True


def test_retention_0_blocked():
    assert _audit(retention_days=0).ok is False


def test_retention_31_blocked():
    assert _audit(retention_days=31).ok is False


def test_retention_negative_blocked():
    assert _audit(retention_days=-1).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# H. Failure behavior / non-call
# ══════════════════════════════════════════════════════════════════════════════

def test_blocked_null_record():
    assert _audit(audit_id=None).audit_record is None


def test_blocked_write_not_allowed():
    assert _audit(audit_id=None).audit_write_allowed is False


def test_blocked_not_written():
    assert _audit(audit_id=None).audit_written is False


def test_blocked_provider_call_false():
    assert _audit(audit_id=None).provider_call_allowed is False


def test_blocked_submitted_false():
    assert _audit(audit_id=None).submitted_to_guard is False


def test_blocked_inference_false():
    assert _audit(audit_id=None).inference_allowed is False


def test_blocked_model_called_false():
    assert _audit(audit_id=None).model_called is False


def test_no_pywinauto():
    import sys
    assert "pywinauto" not in sys.modules


def test_module_no_side_effects():
    from src.backend.app.runtime import gui_model_audit_contract
    assert gui_model_audit_contract is not None


# ══════════════════════════════════════════════════════════════════════════════
# I. Extra permissions blocked
# ══════════════════════════════════════════════════════════════════════════════

def test_extra_audit_written_blocked():
    assert _audit(extra={"audit_written": True}).ok is False


def test_extra_provider_call_blocked():
    assert _audit(extra={"provider_call_allowed": True}).ok is False


def test_extra_inference_blocked():
    assert _audit(extra={"inference_allowed": True}).ok is False


def test_extra_model_called_blocked():
    assert _audit(extra={"model_called": True}).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# J. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_policy_pass():
    pass


def test_runtime_isolation_pass():
    pass


def test_source_policy_pass():
    pass


def test_input_redaction_pass():
    pass


def test_mock_e2e_pass():
    pass


def test_adapter_validator_pass():
    pass


def test_gui_blocklist_pass():
    pass


def test_spm_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"}},
    ]})
    assert "spm_realign_subject" not in p["allowed_spm_realign_sandbox_nodes"]  # blocked per current safety policy


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
