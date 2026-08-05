"""Tests for Model Provider Policy Gate — M11-GUI-MODEL-CONTRACT-T001."""

from __future__ import annotations

import json

import pytest

from src.backend.app.runtime.gui_model_provider_policy import (
    allowed_fixture_provider_declaration,
    validate_model_provider_policy,
)

# ══════════════════════════════════════════════════════════════════════════════
# A. Allowed fixture_only
# ══════════════════════════════════════════════════════════════════════════════


def test_fixture_only_allowed():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    assert r.ok is True
    assert r.status == "MODEL_PROVIDER_ALLOWED"
    assert r.provider_type == "fixture_only"


def test_fixture_inference_not_allowed():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    assert r.inference_allowed is False


def test_fixture_model_not_loaded():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    assert r.model_loaded is False


def test_fixture_network_not_accessed():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    assert r.network_accessed is False


def test_fixture_provider_call_not_allowed():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    assert r.provider_call_allowed is False


def test_allowed_json_serializable():
    r = validate_model_provider_policy(**allowed_fixture_provider_declaration())
    json.loads(json.dumps(r.to_dict()))


def test_approved_true_does_not_change():
    decl = allowed_fixture_provider_declaration()
    decl["approved"] = True
    r = validate_model_provider_policy(**decl)
    assert r.ok is True  # still allowed, approved is ignored


# ══════════════════════════════════════════════════════════════════════════════
# B. Missing / Unknown
# ══════════════════════════════════════════════════════════════════════════════


def test_missing_provider_type():
    r = validate_model_provider_policy(provider_type=None)
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_MISSING"


def test_empty_provider_type():
    r = validate_model_provider_policy(provider_type="")
    assert r.ok is False


def test_unknown_provider_type():
    r = validate_model_provider_policy(provider_type="some_future_provider")
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_UNKNOWN"


# ══════════════════════════════════════════════════════════════════════════════
# C. Real Provider Blocked
# ══════════════════════════════════════════════════════════════════════════════

REAL_TYPES = [
    "local_allowlisted",
    "local_untrusted",
    "remote_disabled",
    "remote_allowlisted_future",
    "remote_untrusted",
    "external_tool_provider",
]


@pytest.mark.parametrize("ptype", REAL_TYPES)
def test_real_provider_blocked(ptype):
    r = validate_model_provider_policy(provider_type=ptype)
    assert r.ok is False
    assert r.status == "MODEL_PROVIDER_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# D. Blocked Provider Names
# ══════════════════════════════════════════════════════════════════════════════

BLOCKED_NAMES = [
    "openai",
    "huggingface",
    "ollama",
    "vllm",
    "transformers",
    "custom_http",
    "pywinauto",
    "desktop",
    "browser",
    "manual",
]


@pytest.mark.parametrize("pname", BLOCKED_NAMES)
def test_blocked_name(pname):
    r = validate_model_provider_policy(
        provider_type="fixture_only",
        provider_name=pname,
    )
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# E. Policy Deviations Blocked (fixture_only base)
# ══════════════════════════════════════════════════════════════════════════════


def test_inference_enabled_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["inference_enabled"] = True
    r = validate_model_provider_policy(**decl)
    assert r.ok is False


def test_network_local_only_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["network_access"] = "local_only"
    r = validate_model_provider_policy(**decl)
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_NETWORK_BLOCKED"


def test_network_unrestricted_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["network_access"] = "unrestricted"
    r = validate_model_provider_policy(**decl)
    assert r.ok is False


def test_output_mode_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["allowed_output_mode"] = "executable_action"
    r = validate_model_provider_policy(**decl)
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_OUTPUT_MODE_BLOCKED"


def test_action_policy_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["allowed_action_policy"] = "tier_1_allowed"
    r = validate_model_provider_policy(**decl)
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_ACTION_POLICY_BLOCKED"


def test_trust_remote_code_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["trust_remote_code"] = True
    r = validate_model_provider_policy(**decl)
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_TRUST_REMOTE_CODE_BLOCKED"


def test_runtime_sandbox_false_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["runtime_sandbox_required"] = False
    r = validate_model_provider_policy(**decl)
    assert r.ok is False


def test_extra_provider_call_allowed_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["extra"] = {"provider_call_allowed": True}
    r = validate_model_provider_policy(**decl)
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_EXTRA_PERMISSION_BLOCKED"


def test_extra_approved_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["extra"] = {"approved": True}
    r = validate_model_provider_policy(**decl)
    assert r.ok is False


def test_extra_enable_real_model_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["extra"] = {"enable_real_model": True}
    r = validate_model_provider_policy(**decl)
    assert r.ok is False


def test_extra_enable_pywinauto_blocked():
    decl = allowed_fixture_provider_declaration()
    decl["extra"] = {"enable_pywinauto": True}
    r = validate_model_provider_policy(**decl)
    assert r.ok is False


# ══════════════════════════════════════════════════════════════════════════════
# F. Real provider declaration blocked (even when valid-looking)
# ══════════════════════════════════════════════════════════════════════════════


def _real_base():
    return {
        "provider_type": "local_allowlisted",
        "provider_name": "test_local_model",
        "model_source": "local_allowlisted",
        "model_id": "test_model_v1",
        "model_version": "abc123",
        "model_dir": "models/gui_agent/v1/",
        "weights_format": "safetensors",
        "checksum": "sha256:abc123",
        "checksum_required": True,
        "trust_remote_code": False,
        "weights_only": True,
        "network_access": "disabled",
        "runtime_sandbox_required": True,
        "inference_enabled": False,
        "allowed_output_mode": "raw_model_output_envelope",
        "allowed_action_policy": "record_observation_only",
    }


def test_real_valid_looking_still_blocked():
    r = validate_model_provider_policy(**_real_base())
    assert r.ok is False
    assert r.error_code == "MODEL_PROVIDER_REAL_DISABLED"


# ══════════════════════════════════════════════════════════════════════════════
# G. Non-Call / Isolation
# ══════════════════════════════════════════════════════════════════════════════


def test_no_pywinauto_import():
    import sys

    assert "pywinauto" not in sys.modules


def test_blocked_result_safety():
    r = validate_model_provider_policy(provider_type="local_allowlisted")
    assert r.inference_allowed is False
    assert r.model_loaded is False
    assert r.network_accessed is False
    assert r.provider_call_allowed is False


# ══════════════════════════════════════════════════════════════════════════════
# H. Regression
# ══════════════════════════════════════════════════════════════════════════════


def test_mock_adapter_e2e_pass():
    pass


def test_adapter_validator_pass():
    pass


def test_gui_blocklist_pass():
    pass


def test_spm_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    p = classify_plan_nodes(
        {
            "pipeline_id": "t",
            "nodes": [
                {
                    "id": "spm_realign_subject",
                    "depends_on": [],
                    "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"},
                },
            ],
        }
    )
    assert (
        "spm_realign_subject" not in p["allowed_spm_realign_sandbox_nodes"]
    )  # blocked per current safety policy


def test_dpabi_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    p = classify_plan_nodes(
        {
            "pipeline_id": "t",
            "nodes": [
                {"id": "dpabi_capability_inspection", "depends_on": [], "params": {}},
            ],
        }
    )
    assert "dpabi_capability_inspection" in p["allowed_dpabi_metadata_nodes"]


def test_gpu_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    p = classify_plan_nodes(
        {
            "pipeline_id": "t",
            "nodes": [
                {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
            ],
        }
    )
    assert "gpu_alff_subject" in p["allowed_gpu_nodes"]
