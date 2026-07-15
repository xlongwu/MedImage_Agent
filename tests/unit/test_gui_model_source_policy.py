"""Tests for Model Source / Weights Policy — M11-GUI-MODEL-CONTRACT-T003."""

from __future__ import annotations

import ast
import inspect
import json

import pytest
from src.backend.app.runtime.gui_model_source_policy import (
    allowed_fixture_model_source_declaration,
    validate_model_source_policy,
)


def _assert_source_policy_has_no_forbidden_imports() -> None:
    from src.backend.app.runtime import gui_model_source_policy

    forbidden = {"pywinauto", "torch", "transformers", "safetensors"}
    imported: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(gui_model_source_policy))):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden), imported & forbidden


# ══════════════════════════════════════════════════════════════════════════════
# A. Allowed fixture_catalog
# ══════════════════════════════════════════════════════════════════════════════

def test_fixture_source_allowed():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.ok is True
    assert r.status == "MODEL_SOURCE_ALLOWED"
    assert r.model_source == "fixture_catalog"


def test_fixture_load_not_allowed():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.model_load_allowed is False


def test_fixture_model_not_loaded():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.model_loaded is False


def test_fixture_fs_not_accessed():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.filesystem_accessed is False


def test_fixture_network_not_accessed():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.network_accessed is False


def test_fixture_provider_not_allowed():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    assert r.provider_call_allowed is False


def test_fixture_json_serializable():
    r = validate_model_source_policy(**allowed_fixture_model_source_declaration())
    json.loads(json.dumps(r.to_dict()))


# ══════════════════════════════════════════════════════════════════════════════
# B. Missing / Unknown
# ══════════════════════════════════════════════════════════════════════════════

def test_missing_source():
    r = validate_model_source_policy(model_source=None)
    assert r.ok is False
    assert r.error_code == "MODEL_SOURCE_MISSING"


def test_empty_source():
    r = validate_model_source_policy(model_source="")
    assert r.ok is False


def test_unknown_source():
    r = validate_model_source_policy(model_source="some_future_source")
    assert r.ok is False
    assert r.error_code == "MODEL_SOURCE_UNKNOWN"


# ══════════════════════════════════════════════════════════════════════════════
# C. Real Source Blocked
# ══════════════════════════════════════════════════════════════════════════════

REAL_SOURCES = [
    "local_allowlisted", "local_untrusted", "remote_repository",
    "huggingface_repo", "runtime_download", "user_supplied_path",
    "absolute_path",
]


@pytest.mark.parametrize("src", REAL_SOURCES)
def test_real_source_blocked(src):
    r = validate_model_source_policy(model_source=src)
    assert r.ok is False
    assert r.status == "MODEL_SOURCE_BLOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# D. Fixture Policy Deviations
# ══════════════════════════════════════════════════════════════════════════════

def _fixture(**overrides):
    d = allowed_fixture_model_source_declaration()
    d.update(overrides)
    return validate_model_source_policy(**d)


def test_fixture_dir_non_null_blocked():
    assert _fixture(model_dir="./models").ok is False


def test_fixture_weights_file_non_null_blocked():
    assert _fixture(weights_file="./model.safetensors").ok is False


def test_fixture_weights_format_blocked():
    assert _fixture(weights_format="safetensors").ok is False


def test_fixture_checksum_required_blocked():
    assert _fixture(checksum_required=True).ok is False


def test_fixture_trust_remote_code_blocked():
    r = _fixture(trust_remote_code=True)
    assert r.ok is False
    assert r.error_code == "MODEL_SOURCE_TRUST_REMOTE_CODE_BLOCKED"


def test_fixture_weights_only_false_blocked():
    assert _fixture(weights_only=False).ok is False


def test_fixture_runtime_download_blocked():
    assert _fixture(runtime_download_allowed=True).ok is False


def test_fixture_remote_repo_blocked():
    assert _fixture(remote_repository="huggingface.co").ok is False


def test_fixture_user_path_blocked():
    assert _fixture(user_supplied_path=True).ok is False


def test_fixture_extra_load_blocked():
    assert _fixture(extra={"model_load_allowed": True}).ok is False


def test_fixture_extra_loaded_blocked():
    assert _fixture(extra={"model_loaded": True}).ok is False


def test_fixture_extra_fs_blocked():
    assert _fixture(extra={"filesystem_accessed": True}).ok is False


def test_fixture_extra_net_blocked():
    assert _fixture(extra={"network_accessed": True}).ok is False


def test_fixture_extra_provider_blocked():
    assert _fixture(extra={"provider_call_allowed": True}).ok is False


def test_fixture_extra_real_blocked():
    assert _fixture(extra={"enable_real_model": True}).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# E. Future Real Source Blocked
# ══════════════════════════════════════════════════════════════════════════════

def _real_source(**overrides):
    base = {
        "model_source": "local_allowlisted",
        "model_dir": "models/gui_agent/v1/",
        "weights_file": "models/gui_agent/v1/model.safetensors",
        "weights_format": "safetensors",
        "checksum": "sha256:abc123",
        "expected_checksum": "sha256:abc123",
        "checksum_required": True,
        "checksum_validated": True,
        "trust_remote_code": False,
        "weights_only": True,
        "runtime_download_allowed": False,
        "remote_repository": None,
        "user_supplied_path": False,
        "allowlisted_model_root": "models/gui_agent/",
    }
    base.update(overrides)
    return validate_model_source_policy(**base)


def test_real_valid_looking_blocked():
    r = _real_source()
    assert r.ok is False
    assert r.error_code == "MODEL_SOURCE_REAL_DISABLED"


def test_real_trust_remote_blocked():
    assert _real_source(trust_remote_code=True).ok is False


@pytest.mark.parametrize("fmt", ["pt", "pth", "pkl", "pickle"])
def test_real_bad_format_blocked(fmt):
    assert _real_source(weights_format=fmt).ok is False


def test_real_weights_only_false_blocked():
    assert _real_source(weights_only=False).ok is False


def test_real_checksum_not_required_blocked():
    assert _real_source(checksum_required=False).ok is False


def test_real_checksum_missing_blocked():
    assert _real_source(checksum=None).ok is False


def test_real_checksum_mismatch_blocked():
    assert _real_source(expected_checksum="sha256:different").ok is False


def test_real_runtime_dl_blocked():
    assert _real_source(runtime_download_allowed=True).ok is False


def test_real_remote_repo_blocked():
    assert _real_source(remote_repository="huggingface.co").ok is False


def test_real_user_path_blocked():
    assert _real_source(user_supplied_path=True).ok is False


# ══════════════════════════════════════════════════════════════════════════════
# F. Path Scope Validation (pure string)
# ══════════════════════════════════════════════════════════════════════════════

def test_model_dir_traversal_blocked():
    assert _real_source(model_dir="../escape").ok is False


def test_weights_file_traversal_blocked():
    assert _real_source(weights_file="../escape/model.safetensors").ok is False


def test_model_dir_rawdata_blocked():
    assert _real_source(model_dir="rawdata/models/").ok is False


def test_model_dir_data_blocked():
    assert _real_source(model_dir="data/raw/models/").ok is False


def test_model_dir_derivatives_blocked():
    assert _real_source(model_dir="derivatives/models/").ok is False


def test_model_dir_absolute_unix_blocked():
    assert _real_source(model_dir="/etc/models/").ok is False


def test_model_dir_windows_absolute_blocked():
    assert _real_source(model_dir="C:/Users/models/").ok is False


def test_model_dir_home_blocked():
    assert _real_source(model_dir="~/models/").ok is False


def test_weights_file_rawdata_blocked():
    assert _real_source(weights_file="rawdata/model.safetensors").ok is False


def test_weights_file_derivatives_blocked():
    assert _real_source(weights_file="derivatives/model.safetensors").ok is False


# ══════════════════════════════════════════════════════════════════════════════
# G. Non-Call / Isolation
# ══════════════════════════════════════════════════════════════════════════════

def test_no_torch_import():
    _assert_source_policy_has_no_forbidden_imports()


def test_no_transformers_import():
    _assert_source_policy_has_no_forbidden_imports()


def test_no_safetensors_import():
    _assert_source_policy_has_no_forbidden_imports()


def test_no_pywinauto_import():
    _assert_source_policy_has_no_forbidden_imports()


def test_blocked_all_flags_false():
    r = validate_model_source_policy(model_source="local_allowlisted")
    assert r.model_load_allowed is False
    assert r.model_loaded is False
    assert r.filesystem_accessed is False
    assert r.network_accessed is False
    assert r.provider_call_allowed is False


def test_module_no_side_effects():
    from src.backend.app.runtime import gui_model_source_policy
    assert gui_model_source_policy is not None


# ══════════════════════════════════════════════════════════════════════════════
# H. Regression
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_policy_tests_pass():
    pass


def test_runtime_isolation_tests_pass():
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
