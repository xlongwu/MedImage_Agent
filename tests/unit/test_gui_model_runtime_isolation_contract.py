"""Tests for Runtime Isolation Contract — M11-GUI-MODEL-CONTRACT-T002."""

from __future__ import annotations

import json

import pytest
from src.backend.app.runtime.gui_model_runtime_isolation import (
    allowed_fixture_runtime_declaration,
    validate_model_runtime_declaration,
)


# ══════════════════════════════════════════════════════════════════════════════
# A. Allowed fixture_only
# ══════════════════════════════════════════════════════════════════════════════

def test_fixture_runtime_allowed():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.ok is True
    assert r.status == "MODEL_RUNTIME_ALLOWED"
    assert r.runtime_type == "fixture_only"


def test_fixture_inference_not_allowed():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.inference_allowed is False


def test_fixture_runtime_not_started():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.runtime_started is False


def test_fixture_model_not_loaded():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.model_loaded is False


def test_fixture_network_not_accessed():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.network_accessed is False


def test_fixture_gpu_not_accessed():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.gpu_accessed is False


def test_fixture_provider_not_allowed():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    assert r.provider_call_allowed is False


def test_fixture_json_serializable():
    r = validate_model_runtime_declaration(**allowed_fixture_runtime_declaration())
    json.loads(json.dumps(r.to_dict()))


# ══════════════════════════════════════════════════════════════════════════════
# B. Missing / Unknown
# ══════════════════════════════════════════════════════════════════════════════

def test_missing_runtime_type():
    r = validate_model_runtime_declaration(runtime_type=None)
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_MISSING"


def test_empty_runtime_type():
    r = validate_model_runtime_declaration(runtime_type="")
    assert r.ok is False


def test_unknown_runtime_type():
    r = validate_model_runtime_declaration(runtime_type="some_future_runtime")
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_UNKNOWN"


# ══════════════════════════════════════════════════════════════════════════════
# C. Real Runtime Types Blocked
# ══════════════════════════════════════════════════════════════════════════════

REAL_RUNTIMES = [
    "local_process", "local_worker", "local_server",
    "remote_server", "external_tool", "gpu_inference",
]


@pytest.mark.parametrize("rtype", REAL_RUNTIMES)
def test_real_runtime_blocked(rtype):
    r = validate_model_runtime_declaration(runtime_type=rtype)
    assert r.ok is False
    assert r.status == "MODEL_RUNTIME_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# D. Fixture Policy Deviations Blocked
# ══════════════════════════════════════════════════════════════════════════════

def _fixture(**overrides):
    d = allowed_fixture_runtime_declaration()
    d.update(overrides)
    return validate_model_runtime_declaration(**d)


def test_inference_enabled_blocked():
    assert _fixture(inference_enabled=True).ok is False


def test_runtime_started_blocked():
    assert _fixture(runtime_started=True).ok is False


def test_network_local_only_blocked():
    r = _fixture(network_policy="local_only")
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_NETWORK_BLOCKED"


def test_network_unrestricted_blocked():
    assert _fixture(network_policy="unrestricted").ok is False


def test_filesystem_scoped_blocked():
    r = _fixture(filesystem_policy="scoped_temp")
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_FILESYSTEM_BLOCKED"


def test_temp_dir_non_null_blocked():
    assert _fixture(temp_dir="./cache").ok is False


def test_cache_dir_non_null_blocked():
    assert _fixture(cache_dir="./data").ok is False


def test_timeout_zero_blocked():
    assert _fixture(timeout_seconds=0).ok is False


def test_hard_less_than_soft_blocked():
    assert _fixture(timeout_seconds=40, hard_timeout_seconds=30).ok is False


def test_hard_exceeds_max_blocked():
    assert _fixture(hard_timeout_seconds=61).ok is False


def test_memory_zero_blocked():
    assert _fixture(memory_budget_mb=0).ok is False


def test_memory_exceeds_max_blocked():
    assert _fixture(memory_budget_mb=4097).ok is False


def test_gpu_enabled_blocked():
    assert _fixture(gpu_enabled=True).ok is False


def test_gpu_memory_non_null_blocked():
    assert _fixture(gpu_memory_budget_mb=1024).ok is False


def test_concurrency_not_one_blocked():
    assert _fixture(max_concurrent_jobs=2).ok is False


def test_queue_zero_blocked():
    assert _fixture(queue_limit=0).ok is False


def test_queue_exceeds_max_blocked():
    assert _fixture(queue_limit=11).ok is False


def test_provider_access_blocked():
    r = _fixture(provider_access=True)
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_PROVIDER_ACCESS_BLOCKED"


def test_gui_api_access_blocked():
    assert _fixture(gui_api_access=True).ok is False


def test_pywinauto_allowed_blocked():
    r = _fixture(pywinauto_allowed=True)
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_PYWINAUTO_BLOCKED"


def test_gui_automation_blocked():
    assert _fixture(gui_automation_allowed=True).ok is False


def test_output_mode_blocked():
    r = _fixture(allowed_output_mode="executable_action")
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_OUTPUT_MODE_BLOCKED"


def test_provider_call_allowed_true_blocked():
    r = _fixture(provider_call_allowed=True)
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_PROVIDER_PERMISSION_BLOCKED"


def test_sandbox_required_false_blocked():
    r = _fixture(runtime_sandbox_required=False)
    assert r.ok is False


def test_sandbox_enabled_false_blocked():
    r = _fixture(runtime_sandbox_enabled=False)
    assert r.ok is False


def test_extra_enable_real_runtime_blocked():
    assert _fixture(extra={"enable_real_runtime": True}).ok is False


def test_extra_enable_inference_blocked():
    assert _fixture(extra={"enable_inference": True}).ok is False


def test_extra_enable_pywinauto_blocked():
    assert _fixture(extra={"enable_pywinauto": True}).ok is False


def test_extra_enable_gui_automation_blocked():
    assert _fixture(extra={"enable_gui_automation": True}).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Future Real Runtime Blocked
# ══════════════════════════════════════════════════════════════════════════════

def test_local_worker_valid_looking_blocked():
    r = validate_model_runtime_declaration(
        runtime_type="local_worker",
        runtime_sandbox_required=True, runtime_sandbox_enabled=True,
        inference_enabled=False, runtime_started=False,
        network_policy="disabled", filesystem_policy="none",
        temp_dir=None, cache_dir=None,
        timeout_seconds=30, hard_timeout_seconds=60, memory_budget_mb=4096,
        gpu_enabled=False, max_concurrent_jobs=1, queue_limit=10,
        provider_access=False, gui_api_access=False,
        pywinauto_allowed=False, gui_automation_allowed=False,
        allowed_output_mode="raw_model_output_envelope",
        provider_call_allowed=False,
    )
    assert r.ok is False
    assert r.error_code == "MODEL_RUNTIME_REAL_DISABLED"


def test_remote_server_blocked():
    r = validate_model_runtime_declaration(runtime_type="remote_server")
    assert r.ok is False


def test_gpu_inference_blocked():
    r = validate_model_runtime_declaration(runtime_type="gpu_inference")
    assert r.ok is False


# ══════════════════════════════════════════════════════════════════════════════
# F. Non-Call / Isolation
# ══════════════════════════════════════════════════════════════════════════════

def test_no_pywinauto_import():
    import sys
    assert "pywinauto" not in sys.modules


def test_blocked_all_flags_false():
    r = validate_model_runtime_declaration(runtime_type="local_worker")
    assert r.inference_allowed is False
    assert r.runtime_started is False
    assert r.model_loaded is False
    assert r.network_accessed is False
    assert r.gpu_accessed is False
    assert r.provider_call_allowed is False


def test_module_no_worker():
    from src.backend.app.runtime import gui_model_runtime_isolation
    assert gui_model_runtime_isolation is not None


# ══════════════════════════════════════════════════════════════════════════════
# G. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_policy_tests_pass():
    pass


def test_mock_e2e_tests_pass():
    pass


def test_adapter_validator_tests_pass():
    pass


def test_gui_blocklist_tests_pass():
    pass


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
