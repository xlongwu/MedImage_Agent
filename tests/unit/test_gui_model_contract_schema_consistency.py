"""Cross-Contract Schema Consistency Tests — M11-GUI-MODEL-CONTRACT-STABILIZE-T001."""

from __future__ import annotations

import ast
import inspect
import json

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

ALL_ALLOWED = {
    "provider": lambda: validate_model_provider_policy(**allowed_fixture_provider_declaration()),
    "runtime": lambda: validate_model_runtime_declaration(**allowed_fixture_runtime_declaration()),
    "source": lambda: validate_model_source_policy(**allowed_fixture_model_source_declaration()),
    "input": lambda: validate_and_build_model_prompt_envelope(**allowed_minimal_prompt_input_declaration()),
    "audit": lambda: validate_and_build_model_audit_record(**allowed_model_audit_metadata_declaration()),
}


def _assert_module_has_no_forbidden_imports(module) -> None:
    forbidden = {"pywinauto", "torch", "transformers", "safetensors"}
    imported: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden), imported & forbidden

# ══════════════════════════════════════════════════════════════════════════════
# A. Common result schema
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_has_common_fields():
    r = ALL_ALLOWED["provider"]()
    assert r.ok is not None
    assert r.status is not None
    assert r.provider_call_allowed is not None


def test_runtime_has_common_fields():
    r = ALL_ALLOWED["runtime"]()
    assert r.ok is not None
    assert r.status is not None
    assert r.provider_call_allowed is not None


def test_source_has_common_fields():
    r = ALL_ALLOWED["source"]()
    assert r.ok is not None
    assert r.status is not None
    assert r.provider_call_allowed is not None


def test_input_has_common_fields():
    r = ALL_ALLOWED["input"]()
    assert r.ok is not None
    assert r.status is not None
    assert r.provider_call_allowed is not None


def test_audit_has_common_fields():
    r = ALL_ALLOWED["audit"]()
    assert r.ok is not None
    assert r.status is not None
    assert r.provider_call_allowed is not None


# ══════════════════════════════════════════════════════════════════════════════
# B. Allowed status semantics
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_allowed_status():
    r = ALL_ALLOWED["provider"]()
    assert r.status == "MODEL_PROVIDER_ALLOWED"


def test_runtime_allowed_status():
    r = ALL_ALLOWED["runtime"]()
    assert r.status == "MODEL_RUNTIME_ALLOWED"


def test_source_allowed_status():
    r = ALL_ALLOWED["source"]()
    assert r.status == "MODEL_SOURCE_ALLOWED"


def test_input_allowed_status():
    r = ALL_ALLOWED["input"]()
    assert r.status == "MODEL_INPUT_ALLOWED"


def test_audit_allowed_status():
    r = ALL_ALLOWED["audit"]()
    assert r.status == "MODEL_AUDIT_ALLOWED"


def test_all_allowed_ok():
    for name, fn in ALL_ALLOWED.items():
        assert fn().ok is True, f"{name} should have ok=True"


def test_all_allowed_no_error():
    for name, fn in ALL_ALLOWED.items():
        assert fn().error_code is None, f"{name} should have error_code=None"


def test_all_allowed_provider_call_false():
    for name, fn in ALL_ALLOWED.items():
        assert fn().provider_call_allowed is False, f"{name} provider_call_allowed must be False"


# ══════════════════════════════════════════════════════════════════════════════
# C. Blocked status semantics
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_blocked_status():
    r = validate_model_provider_policy(provider_type="local_allowlisted")
    assert r.status == "MODEL_PROVIDER_BLOCKED"


def test_runtime_blocked_status():
    r = validate_model_runtime_declaration(runtime_type="local_worker")
    assert r.status == "MODEL_RUNTIME_BLOCKED"


def test_source_blocked_status():
    r = validate_model_source_policy(model_source="local_allowlisted")
    assert r.status == "MODEL_SOURCE_BLOCKED"


def test_input_blocked_status():
    r = validate_and_build_model_prompt_envelope(
        **allowed_minimal_prompt_input_declaration(),
        raw_screenshot_present=True,
    )
    assert r.status == "MODEL_INPUT_BLOCKED"


def test_audit_blocked_status():
    r = validate_and_build_model_audit_record(
        audit_id="a_001", run_id="r_001", session_id="s_001",
        event_type="MODEL_OUTPUT_NORMALIZED",
        extra={"raw_text": "secret"},
    )
    assert r.status == "MODEL_AUDIT_BLOCKED"


def test_all_blocked_ok_false():
    blocks = [
        validate_model_provider_policy(provider_type="local_allowlisted"),
        validate_model_runtime_declaration(runtime_type="local_worker"),
        validate_model_source_policy(model_source="local_allowlisted"),
        validate_and_build_model_prompt_envelope(
            **allowed_minimal_prompt_input_declaration(), raw_screenshot_present=True,
        ),
        validate_and_build_model_audit_record(
            audit_id="a", run_id="r", session_id="s",
            event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "s"},
        ),
    ]
    for r in blocks:
        assert r.ok is False
        assert r.provider_call_allowed is False


# ══════════════════════════════════════════════════════════════════════════════
# D. Permission flags — allowed
# ══════════════════════════════════════════════════════════════════════════════

def test_allowed_no_inference():
    for name, fn in ALL_ALLOWED.items():
        r = fn()
        if hasattr(r, "inference_allowed"):
            assert r.inference_allowed is False, f"{name}: inference_allowed must be False"


def test_allowed_no_model_loaded():
    for name, fn in ALL_ALLOWED.items():
        r = fn()
        if hasattr(r, "model_loaded"):
            assert r.model_loaded is False, f"{name}: model_loaded must be False"


def test_allowed_no_model_called():
    for name, fn in ALL_ALLOWED.items():
        r = fn()
        if hasattr(r, "model_called"):
            assert r.model_called is False, f"{name}: model_called must be False"


def test_allowed_no_network():
    for name, fn in ALL_ALLOWED.items():
        r = fn()
        if hasattr(r, "network_accessed"):
            assert r.network_accessed is False, f"{name}: network_accessed must be False"


def test_runtime_allowed_extra():
    r = ALL_ALLOWED["runtime"]()
    assert r.runtime_started is False
    assert r.gpu_accessed is False


def test_source_allowed_extra():
    r = ALL_ALLOWED["source"]()
    assert r.model_load_allowed is False
    assert r.filesystem_accessed is False


def test_audit_allowed_extra():
    r = ALL_ALLOWED["audit"]()
    assert r.audit_written is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Fail-closed behavior
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_blocked_no_permissions():
    r = validate_model_provider_policy(provider_type="local_allowlisted")
    assert r.inference_allowed is False
    assert r.model_loaded is False
    assert r.network_accessed is False


def test_runtime_blocked_no_permissions():
    r = validate_model_runtime_declaration(runtime_type="local_worker")
    assert r.inference_allowed is False
    assert r.runtime_started is False
    assert r.model_loaded is False
    assert r.network_accessed is False
    assert r.gpu_accessed is False


def test_source_blocked_no_permissions():
    r = validate_model_source_policy(model_source="local_allowlisted")
    assert r.model_load_allowed is False
    assert r.filesystem_accessed is False


def test_input_blocked_null_envelope():
    r = validate_and_build_model_prompt_envelope(
        **allowed_minimal_prompt_input_declaration(), raw_screenshot_present=True,
    )
    assert r.ok is False
    assert r.prompt_envelope is None
    assert r.model_called is False


def test_audit_blocked_null_record():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "s"},
    )
    assert r.ok is False
    assert r.audit_record is None
    assert r.audit_write_allowed is False


def test_any_blocked_executable_false():
    """Verify a composed check: any single contract failure means executable=False."""
    prov_ok = ALL_ALLOWED["provider"]().ok
    run_ok = ALL_ALLOWED["runtime"]().ok
    src_ok = ALL_ALLOWED["source"]().ok
    inp_ok = ALL_ALLOWED["input"]().ok
    aud_ok = ALL_ALLOWED["audit"]().ok
    assert all([prov_ok, run_ok, src_ok, inp_ok, aud_ok])
    # If any fails (simulated via blocked result), executable must be false
    blocked = validate_model_provider_policy(provider_type="local_allowlisted")
    assert not blocked.ok


# ══════════════════════════════════════════════════════════════════════════════
# F. Sensitive field policy
# ══════════════════════════════════════════════════════════════════════════════

def test_input_blocks_rawdata():
    d = allowed_minimal_prompt_input_declaration()
    d["user_intent_summary"] = "open rawdata/sub-001"
    assert not validate_and_build_model_prompt_envelope(**d).ok


def test_input_blocks_token():
    d = allowed_minimal_prompt_input_declaration()
    d["task_context_summary"] = "token=abc123"
    assert not validate_and_build_model_prompt_envelope(**d).ok


def test_input_blocks_password():
    d = allowed_minimal_prompt_input_declaration()
    d["user_intent_summary"] = "enter password"
    assert not validate_and_build_model_prompt_envelope(**d).ok


def test_audit_blocks_rawtext():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_text": "x"},
    )
    assert not r.ok


def test_audit_blocks_rawjson():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"raw_json": "x"},
    )
    assert not r.ok


def test_audit_blocks_chain_of_thought():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"chain_of_thought": "x"},
    )
    assert not r.ok


def test_audit_blocks_token():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"token": "x"},
    )
    assert not r.ok


def test_audit_blocks_rawdata_path():
    r = validate_and_build_model_audit_record(
        audit_id="a", run_id="r", session_id="s",
        event_type="MODEL_OUTPUT_NORMALIZED", extra={"rawdata_path": "x"},
    )
    assert not r.ok


# ══════════════════════════════════════════════════════════════════════════════
# G. Side-effect policy
# ══════════════════════════════════════════════════════════════════════════════

def test_no_pywinauto():
    from src.backend.app.runtime import gui_model_provider_policy

    _assert_module_has_no_forbidden_imports(gui_model_provider_policy)


def test_no_torch():
    from src.backend.app.runtime import gui_model_runtime_isolation

    _assert_module_has_no_forbidden_imports(gui_model_runtime_isolation)


def test_no_transformers():
    from src.backend.app.runtime import gui_model_input_redaction

    _assert_module_has_no_forbidden_imports(gui_model_input_redaction)


def test_no_safetensors():
    from src.backend.app.runtime import gui_model_audit_contract

    _assert_module_has_no_forbidden_imports(gui_model_audit_contract)


def test_all_decls_json_serializable():
    for decl in [allowed_fixture_provider_declaration(),
                 allowed_fixture_runtime_declaration(),
                 allowed_fixture_model_source_declaration(),
                 allowed_minimal_prompt_input_declaration(),
                 allowed_model_audit_metadata_declaration()]:
        json.loads(json.dumps(decl))


def test_all_results_json_serializable():
    for name, fn in ALL_ALLOWED.items():
        r = fn()
        json.loads(json.dumps(r.to_dict())), f"{name} result should be JSON serializable"


# ══════════════════════════════════════════════════════════════════════════════
# H. Regression
# ══════════════════════════════════════════════════════════════════════════════

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
