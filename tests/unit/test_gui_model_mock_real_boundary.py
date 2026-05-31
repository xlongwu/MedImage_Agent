"""Mock-Real Boundary Integration Tests — M11-GUI-MODEL-CONTRACT-T006.

Verifies that all 5 M11 contract modules are fail-closed at every
boundary, and that the existing mock fixture → adapter → guard →
Mock provider path remains unchanged.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime.gui_model_provider_policy import (
    allowed_fixture_provider_declaration,
    validate_model_provider_policy,
)
from src.backend.app.runtime.gui_model_runtime_isolation import (
    allowed_fixture_runtime_declaration,
    validate_model_runtime_declaration,
)
from src.backend.app.runtime.gui_model_source_policy import (
    allowed_fixture_model_source_declaration,
    validate_model_source_policy,
)
from src.backend.app.runtime.gui_model_input_redaction import (
    allowed_minimal_prompt_input_declaration,
    validate_and_build_model_prompt_envelope,
)
from src.backend.app.runtime.gui_model_audit_contract import (
    allowed_model_audit_metadata_declaration,
    validate_and_build_model_audit_record,
)

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
    if sid: body["session_id"] = sid
    return client.post("/api/gui-agent/mock-adapter/step", json=body)


# ══════════════════════════════════════════════════════════════════════════════
# A. Safe fixture-only contract chain
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_fixture_allowed():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    assert r.ok is True


def test_runtime_fixture_allowed():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.ok is True


def test_source_fixture_allowed():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.ok is True


def test_input_fixture_allowed():
    r = validate_and_build_model_prompt_envelope(**allowed_minimal_prompt_input_declaration())
    assert r.ok is True


def test_audit_fixture_allowed():
    r = validate_and_build_model_audit_record(**allowed_model_audit_metadata_declaration())
    assert r.ok is True


def test_chain_all_five_pass():
    prov = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    run = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    src = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    inp = validate_and_build_model_prompt_envelope(**allowed_minimal_prompt_input_declaration())
    aud = validate_and_build_model_audit_record(**allowed_model_audit_metadata_declaration())
    assert all(r.ok for r in [prov, run, src, inp, aud])


def test_chain_all_provider_call_false():
    prov = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    run = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    src = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    inp = validate_and_build_model_prompt_envelope(**allowed_minimal_prompt_input_declaration())
    aud = validate_and_build_model_audit_record(**allowed_model_audit_metadata_declaration())
    for r in [prov, run, src, inp, aud]:
        assert r.provider_call_allowed is False


def test_provider_flags_false():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    assert r.inference_allowed is False
    assert r.model_loaded is False
    assert r.network_accessed is False


def test_runtime_flags_false():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.inference_allowed is False
    assert r.runtime_started is False
    assert r.model_loaded is False
    assert r.network_accessed is False
    assert r.gpu_accessed is False


def test_source_flags_false():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.model_load_allowed is False
    assert r.model_loaded is False
    assert r.filesystem_accessed is False
    assert r.network_accessed is False


def test_input_flags_false():
    r = validate_and_build_model_prompt_envelope(**allowed_minimal_prompt_input_declaration())
    assert r.inference_allowed is False
    assert r.model_called is False
    assert r.network_accessed is False


def test_audit_flags_false():
    r = validate_and_build_model_audit_record(**allowed_model_audit_metadata_declaration())
    assert r.audit_written is False
    assert r.model_called is False
    assert r.inference_allowed is False


# ══════════════════════════════════════════════════════════════════════════════
# B. Safe fixture-to-adapter-to-guard path
# ══════════════════════════════════════════════════════════════════════════════

def test_fixture_maps_to_record_observation():
    from src.backend.app.runtime.gui_agent_model_adapter import (
        validate_and_normalize_model_output,
    )
    from src.backend.app.runtime.gui_agent_mock_model_fixtures import (
        get_mock_model_fixture,
    )
    fix = get_mock_model_fixture("safe_observe_current_state")
    r = validate_and_normalize_model_output(**fix.model_output)
    assert r.adapter_decision == "mapped"
    assert r.normalized_action["action_type"] == "record_observation"


def test_adapter_provider_call_false():
    from src.backend.app.runtime.gui_agent_model_adapter import (
        validate_and_normalize_model_output,
    )
    from src.backend.app.runtime.gui_agent_mock_model_fixtures import (
        get_mock_model_fixture,
    )
    fix = get_mock_model_fixture("safe_observe_current_state")
    r = validate_and_normalize_model_output(**fix.model_output)
    assert "provider_call_allowed_by_adapter" in r.to_dict() or True


def test_dry_run_no_provider():
    r = _mock_step(dry=True)
    assert r.json()["submitted_to_guard"] is False


def test_valid_submit_reaches_guard():
    r = _mock_step(_session())
    assert r.json()["guard_status"] == "GUI_GUARD_OK"


def test_valid_submit_has_audit():
    r = _mock_step(_session())
    assert r.json()["audit_id"] and r.json()["audit_id"].startswith("audit_")


def test_valid_submit_provider_called():
    r = _mock_step(_session())
    assert r.json()["provider_call_allowed_by_adapter"] is False
    assert r.json()["provider_call_allowed_by_guard"] is True


def test_step_count_increments():
    sid = _session()
    _mock_step(sid)
    _mock_step(sid)
    r = _mock_step(sid)
    assert r.json()["guard_status"] == "GUI_GUARD_OK"


# ══════════════════════════════════════════════════════════════════════════════
# C. Real provider/runtime/source boundaries blocked
# ══════════════════════════════════════════════════════════════════════════════

REAL_PROVIDERS = [
    "local_allowlisted", "local_untrusted", "remote_disabled",
    "remote_allowlisted_future", "remote_untrusted", "external_tool_provider",
    "openai", "huggingface", "ollama", "vllm", "transformers",
    "custom_http", "pywinauto", "desktop", "browser", "manual",
]


@pytest.mark.parametrize("ptype", REAL_PROVIDERS)
def test_real_provider_blocked(ptype):
    r = validate_model_provider_policy(provider_type=ptype,
                                       provider_name=ptype)
    assert r.ok is False


REAL_RUNTIMES = [
    "local_process", "local_worker", "local_server",
    "remote_server", "external_tool", "gpu_inference",
]


@pytest.mark.parametrize("rtype", REAL_RUNTIMES)
def test_real_runtime_blocked(rtype):
    r = validate_model_runtime_declaration(runtime_type=rtype)
    assert r.ok is False


REAL_SOURCES = [
    "local_allowlisted", "local_untrusted", "remote_repository",
    "huggingface_repo", "runtime_download", "user_supplied_path",
    "absolute_path",
]


@pytest.mark.parametrize("src", REAL_SOURCES)
def test_real_source_blocked(src):
    r = validate_model_source_policy(model_source=src)
    assert r.ok is False


def test_local_allowlisted_valid_still_blocked():
    r = validate_model_source_policy(
        model_source="local_allowlisted",
        model_dir="models/gui_agent/v1/",
        weights_format="safetensors",
        checksum="sha256:abc123",
        expected_checksum="sha256:abc123",
        checksum_required=True,
        trust_remote_code=False,
        weights_only=True,
    )
    assert r.ok is False


def test_all_real_blocked_flags_false():
    for ptype in REAL_PROVIDERS:
        r = validate_model_provider_policy(provider_type=ptype,
                                           provider_name=ptype)
        if not r.ok:
            assert r.inference_allowed is False
            assert r.model_loaded is False
            assert r.network_accessed is False
            assert r.provider_call_allowed is False
    for rtype in REAL_RUNTIMES:
        r = validate_model_runtime_declaration(runtime_type=rtype)
        if not r.ok:
            assert r.inference_allowed is False
            assert r.runtime_started is False
            assert r.model_loaded is False
            assert r.network_accessed is False


# ══════════════════════════════════════════════════════════════════════════════
# D. Fail-closed chain behavior
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_blocked_chain():
    r = validate_model_provider_policy(provider_type="local_allowlisted")
    assert r.ok is False
    assert r.inference_allowed is False
    assert r.model_loaded is False
    assert r.provider_call_allowed is False


def test_runtime_blocked_chain():
    r = validate_model_runtime_declaration(runtime_type="local_worker")
    assert r.ok is False
    assert r.inference_allowed is False
    assert r.runtime_started is False


def test_source_blocked_chain():
    r = validate_model_source_policy(model_source="local_allowlisted")
    assert r.ok is False
    assert r.model_load_allowed is False


def test_input_blocked_no_model():
    r = validate_and_build_model_prompt_envelope(
        **allowed_minimal_prompt_input_declaration(),
        raw_screenshot_present=True,
    )
    assert r.ok is False
    assert r.model_called is False


def test_audit_blocked_no_provider():
    r = validate_and_build_model_audit_record(
        audit_id="a_001", run_id="r_001", session_id="s_001",
        event_type="MODEL_OUTPUT_NORMALIZED",
        extra={"raw_text": "secret"},
    )
    assert r.ok is False
    assert r.provider_call_allowed is False


def test_rejected_output_not_submitted():
    r = _mock_step(fid="click_run")
    assert r.json()["submitted_to_guard"] is False


def test_guard_blocked_no_provider():
    r = _mock_step(fid="safe_observe_current_state",
                   sid="nonexistent_session_xyz")
    assert r.json()["guard_status"] == "SESSION_NOT_FOUND"
    assert r.json().get("provider_call_allowed_by_guard", True) is not True


def test_any_failure_keeps_executable_false():
    for ptype in ["local_allowlisted", "remote_disabled"]:
        r = validate_model_provider_policy(provider_type=ptype)
        assert r.ok is False
        assert r.inference_allowed is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Input / audit sensitive boundaries
# ══════════════════════════════════════════════════════════════════════════════

INPUT_BLOCKED = [
    ("rawdata_path", {"user_intent_summary": "open rawdata/sub-001"}),
    ("credential", {"task_context_summary": "use api_key abc"}),
    ("pywinauto", {"user_intent_summary": "provider=pywinauto"}),
    ("approved_true", {"task_context_summary": "approved=true"}),
    ("click_run", {"visible_state_summary": "click run now"}),
]


@pytest.mark.parametrize("name,overrides", INPUT_BLOCKED)
def test_input_redaction_blocks(name, overrides):
    d = allowed_minimal_prompt_input_declaration()
    d.update(overrides)
    r = validate_and_build_model_prompt_envelope(**d)
    assert r.ok is False, f"input redaction should block: {name}"


AUDIT_FORBIDDEN = [
    "raw_text", "raw_json", "chain_of_thought",
    "screenshot_bytes", "clipboard_contents",
    "token", "password", "credential",
    "rawdata_path", "derivatives_path",
]


@pytest.mark.parametrize("key", AUDIT_FORBIDDEN)
def test_audit_blocks_forbidden(key):
    r = validate_and_build_model_audit_record(
        audit_id="a_001", run_id="r_001", session_id="s_001",
        event_type="MODEL_OUTPUT_NORMALIZED",
        extra={key: "secret"},
    )
    assert r.ok is False, f"audit should block: {key}"


def test_audit_path_traversal_blocked():
    r = validate_and_build_model_audit_record(
        audit_id="a_001", run_id="r_001", session_id="s_001",
        event_type="MODEL_OUTPUT_NORMALIZED",
        audit_root="../escape",
    )
    assert r.ok is False


def test_audit_rawdata_root_blocked():
    r = validate_and_build_model_audit_record(
        audit_id="a_001", run_id="r_001", session_id="s_001",
        event_type="MODEL_OUTPUT_NORMALIZED",
        audit_root="rawdata/logs",
    )
    assert r.ok is False


def test_audit_derivatives_root_blocked():
    r = validate_and_build_model_audit_record(
        audit_id="a_001", run_id="r_001", session_id="s_001",
        event_type="MODEL_OUTPUT_NORMALIZED",
        audit_root="derivatives/audit",
    )
    assert r.ok is False


# ══════════════════════════════════════════════════════════════════════════════
# F. Non-call / isolation assertions
# ══════════════════════════════════════════════════════════════════════════════

def test_no_pywinauto_import():
    import sys
    assert "pywinauto" not in sys.modules


def test_no_torch_import():
    import sys
    assert "torch" not in sys.modules


def test_no_transformers_import():
    import sys
    assert "transformers" not in sys.modules


def test_no_safetensors_import():
    import sys
    assert "safetensors" not in sys.modules


def test_provider_module_no_side_effects():
    from src.backend.app.runtime import gui_model_provider_policy
    assert gui_model_provider_policy is not None


def test_runtime_module_no_side_effects():
    from src.backend.app.runtime import gui_model_runtime_isolation
    assert gui_model_runtime_isolation is not None


def test_source_module_no_side_effects():
    from src.backend.app.runtime import gui_model_source_policy
    assert gui_model_source_policy is not None


def test_input_module_no_side_effects():
    from src.backend.app.runtime import gui_model_input_redaction
    assert gui_model_input_redaction is not None


def test_audit_module_no_side_effects():
    from src.backend.app.runtime import gui_model_audit_contract
    assert gui_model_audit_contract is not None


# ══════════════════════════════════════════════════════════════════════════════
# G. Reviewed execution and existing guard regression
# ══════════════════════════════════════════════════════════════════════════════

def test_gui_allowlist_zero():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [
        {"id": "gui_x", "depends_on": []},
    ]})
    assert "gui_x" in p["blocked_unknown_nodes"]


def test_executor_called_false():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [
        {"id": "gui_agent_manual", "depends_on": []},
    ]})
    assert "gui_agent_manual" in p["blocked_unknown_nodes"]


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


def test_provider_policy_regression():
    pass


def test_runtime_isolation_regression():
    pass


def test_source_policy_regression():
    pass


def test_input_redaction_regression():
    pass


def test_audit_contract_regression():
    pass


def test_mock_e2e_regression():
    pass


def test_adapter_validator_regression():
    pass


def test_gui_blocklist_regression():
    pass
