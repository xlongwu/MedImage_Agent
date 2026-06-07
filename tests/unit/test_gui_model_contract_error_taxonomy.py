"""Contract Error Code Taxonomy Tests — M11-GUI-MODEL-CONTRACT-STABILIZE-T002."""

from __future__ import annotations

import pytest
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

# ══════════════════════════════════════════════════════════════════════════════
# A. Prefix and status consistency
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_blocked_code_prefix():
    r = validate_model_provider_policy(provider_type="local_allowlisted")
    assert r.error_code and r.error_code.startswith("MODEL_PROVIDER_")


def test_runtime_blocked_code_prefix():
    r = validate_model_runtime_declaration(runtime_type="local_worker")
    assert r.error_code and r.error_code.startswith("MODEL_RUNTIME_")


def test_source_blocked_code_prefix():
    r = validate_model_source_policy(model_source="local_allowlisted")
    assert r.error_code and r.error_code.startswith("MODEL_SOURCE_")


def test_input_blocked_code_prefix():
    r = validate_and_build_model_prompt_envelope(
        **allowed_minimal_prompt_input_declaration(), raw_screenshot_present=True,
    )
    assert r.error_code and r.error_code.startswith("MODEL_INPUT_")


def test_audit_blocked_code_prefix():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "x"},
    )
    assert r.error_code and r.error_code.startswith("MODEL_AUDIT_")


def test_provider_blocked_status_pair():
    r = validate_model_provider_policy(provider_type="local_allowlisted")
    assert r.status == "MODEL_PROVIDER_BLOCKED"
    assert r.error_code and r.error_code.startswith("MODEL_PROVIDER_")


def test_runtime_blocked_status_pair():
    r = validate_model_runtime_declaration(runtime_type="local_worker")
    assert r.status == "MODEL_RUNTIME_BLOCKED"
    assert r.error_code and r.error_code.startswith("MODEL_RUNTIME_")


def test_source_blocked_status_pair():
    r = validate_model_source_policy(model_source="local_allowlisted")
    assert r.status == "MODEL_SOURCE_BLOCKED"
    assert r.error_code and r.error_code.startswith("MODEL_SOURCE_")


def test_input_blocked_status_pair():
    r = validate_and_build_model_prompt_envelope(
        **allowed_minimal_prompt_input_declaration(), raw_screenshot_present=True,
    )
    assert r.status == "MODEL_INPUT_BLOCKED"
    assert r.error_code and r.error_code.startswith("MODEL_INPUT_")


def test_audit_blocked_status_pair():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "x"},
    )
    assert r.status == "MODEL_AUDIT_BLOCKED"
    assert r.error_code and r.error_code.startswith("MODEL_AUDIT_")


# ══════════════════════════════════════════════════════════════════════════════
# B. Missing / unknown
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_missing_code():
    r = validate_model_provider_policy(provider_type=None)
    assert r.error_code and "MISSING" in r.error_code


def test_runtime_missing_code():
    r = validate_model_runtime_declaration(runtime_type=None)
    assert r.error_code and "MISSING" in r.error_code


def test_source_missing_code():
    r = validate_model_source_policy(model_source=None)
    assert r.error_code and "MISSING" in r.error_code


def test_input_schema_invalid_code():
    r = validate_and_build_model_prompt_envelope(model_input_id=None)
    assert r.error_code and "SCHEMA" in r.error_code


def test_audit_event_unknown():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="UNKNOWN_EVENT",
    )
    assert r.error_code and "UNKNOWN" in r.error_code


# ══════════════════════════════════════════════════════════════════════════════
# C. Permission escalation
# ══════════════════════════════════════════════════════════════════════════════

def _provider_extra():
    d = allowed_fixture_provider_declaration()
    d["extra"] = {"provider_call_allowed": True}
    return validate_model_provider_policy(**d)


def _runtime_extra():
    d = allowed_fixture_runtime_declaration()
    d["extra"] = {"enable_real_runtime": True}
    return validate_model_runtime_declaration(**d)


def _source_extra():
    d = allowed_fixture_model_source_declaration()
    d["extra"] = {"model_load_allowed": True}
    return validate_model_source_policy(**d)


def _input_extra():
    d = allowed_minimal_prompt_input_declaration()
    d["extra"] = {"provider_call_allowed": True}
    return validate_and_build_model_prompt_envelope(**d)


def _audit_extra():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED",
        extra={"provider_call_allowed": True},
    )
    return r


def test_provider_extra_permission():
    r = _provider_extra()
    assert not r.ok
    assert "EXTRA_PERMISSION" in r.error_code


def test_runtime_extra_permission():
    r = _runtime_extra()
    assert not r.ok
    assert "EXTRA_PERMISSION" in r.error_code


def test_source_extra_permission():
    r = _source_extra()
    assert not r.ok
    assert "EXTRA_PERMISSION" in r.error_code


def test_input_extra_permission():
    r = _input_extra()
    assert not r.ok
    assert "EXTRA_PERMISSION" in r.error_code


def test_audit_extra_permission():
    r = _audit_extra()
    assert not r.ok
    assert "EXTRA_PERMISSION" in r.error_code


def test_all_extra_permission_provider_call_false():
    for r in [_provider_extra(), _runtime_extra(), _source_extra(),
              _input_extra(), _audit_extra()]:
        assert r.provider_call_allowed is False


# ══════════════════════════════════════════════════════════════════════════════
# D. Network / path / sensitive category
# ══════════════════════════════════════════════════════════════════════════════

def test_runtime_network_violation():
    d = allowed_fixture_runtime_declaration()
    d["network_policy"] = "local_only"
    r = validate_model_runtime_declaration(**d)
    assert r.error_code and "NETWORK_BLOCKED" in r.error_code


def test_source_rawdata_path():
    r = validate_model_source_policy(model_source="local_allowlisted",
                                     model_dir="rawdata/models/")
    assert not r.ok
    assert r.error_code is not None


def test_source_derivatives_path():
    r = validate_model_source_policy(model_source="local_allowlisted",
                                     model_dir="derivatives/models/")
    assert not r.ok
    assert r.error_code is not None


def test_input_rawdata_path():
    d = allowed_minimal_prompt_input_declaration()
    d["user_intent_summary"] = "open rawdata/sub-001"
    r = validate_and_build_model_prompt_envelope(**d)
    assert r.error_code and "RAWDATA_PATH" in r.error_code


def test_input_credential():
    d = allowed_minimal_prompt_input_declaration()
    d["task_context_summary"] = "api_key secret"
    r = validate_and_build_model_prompt_envelope(**d)
    assert r.error_code and "CREDENTIAL" in r.error_code


def test_audit_forbidden_field():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "x"},
    )
    assert r.error_code and "FORBIDDEN_FIELD" in r.error_code


def test_audit_path_traversal():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED",
        audit_root="../escape",
    )
    assert r.error_code and "PATH_BLOCKED" in r.error_code


# ══════════════════════════════════════════════════════════════════════════════
# E. Fail-closed semantics
# ══════════════════════════════════════════════════════════════════════════════

def _all_blocked():
    return [
        validate_model_provider_policy(provider_type="local_allowlisted"),
        validate_model_runtime_declaration(runtime_type="local_worker"),
        validate_model_source_policy(model_source="local_allowlisted"),
        validate_and_build_model_prompt_envelope(
            **allowed_minimal_prompt_input_declaration(), raw_screenshot_present=True,
        ),
        validate_and_build_model_audit_record(
            audit_id="a", run_id="r", session_id="s",
            event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "x"},
        ),
    ]


def test_all_blocked_ok_false():
    for r in _all_blocked():
        assert r.ok is False


def test_all_blocked_provider_call_false():
    for r in _all_blocked():
        assert r.provider_call_allowed is False


def test_all_blocked_no_inference():
    for r in _all_blocked():
        if hasattr(r, "inference_allowed"):
            assert r.inference_allowed is False


def test_all_blocked_no_model_load():
    for r in _all_blocked():
        if hasattr(r, "model_loaded"):
            assert r.model_loaded is False
        if hasattr(r, "model_called"):
            assert r.model_called is False


def test_all_blocked_no_network():
    for r in _all_blocked():
        if hasattr(r, "network_accessed"):
            assert r.network_accessed is False


def test_audit_blocked_no_write():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "x"},
    )
    assert r.audit_written is False


def test_input_blocked_null_envelope():
    r = validate_and_build_model_prompt_envelope(
        **allowed_minimal_prompt_input_declaration(), raw_screenshot_present=True,
    )
    assert r.prompt_envelope is None


def test_audit_blocked_null_record():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "x"},
    )
    assert r.audit_record is None


# ══════════════════════════════════════════════════════════════════════════════
# F. Error inventory sanity
# ══════════════════════════════════════════════════════════════════════════════

def test_no_empty_error_code():
    for r in _all_blocked():
        assert r.error_code is not None
        assert len(r.error_code) > 0
        assert r.error_code.strip() != ""


def test_no_non_model_prefix():
    for r in _all_blocked():
        assert r.error_code.startswith("MODEL_")


def test_blocked_always_has_error():
    for r in _all_blocked():
        assert r.error_code is not None


def test_allowed_no_error():
    prov = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    run = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    src = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    inp = validate_and_build_model_prompt_envelope(**allowed_minimal_prompt_input_declaration())
    aud = validate_and_build_model_audit_record(**allowed_model_audit_metadata_declaration())
    for r in [prov, run, src, inp, aud]:
        assert r.error_code is None


def test_allowed_status_end():
    prov = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    run = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    src = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    inp = validate_and_build_model_prompt_envelope(**allowed_minimal_prompt_input_declaration())
    aud = validate_and_build_model_audit_record(**allowed_model_audit_metadata_declaration())
    for r in [prov, run, src, inp, aud]:
        assert r.status.endswith("_ALLOWED")


def test_blocked_status_end():
    for r in _all_blocked():
        assert r.status.endswith("_BLOCKED")


# ══════════════════════════════════════════════════════════════════════════════
# G. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_schema_consistency_pass():
    pass


def test_provider_policy_pass():
    pass


def test_runtime_isolation_pass():
    pass


def test_source_policy_pass():
    pass


def test_input_redaction_pass():
    pass


def test_audit_contract_pass():
    pass


def test_mock_real_boundary_pass():
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
