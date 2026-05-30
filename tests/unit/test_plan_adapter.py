"""Tests for Plan Adapter — reviewed plan → executor pipeline dict conversion."""

from __future__ import annotations

import json

import pytest
from src.backend.app.planner.plan_adapter import (
    PlanAdapterResult,
    adapt_reviewed_plan,
    classify_plan_nodes,
    reviewed_plan_to_pipeline_dict,
)


def _valid_plan(**overrides):
    p = {
        "pipeline_id": "test_plan",
        "nodes": [
            {"id": "data_inspection", "backend": "python", "depends_on": [], "params": {}},
            {"id": "motion_qc_subject", "backend": "python",
             "depends_on": ["data_inspection"], "params": {}},
        ],
    }
    p.update(overrides)
    return p


# ── 1. Valid plan converts ──

def test_valid_plan_converts():
    result = reviewed_plan_to_pipeline_dict(_valid_plan())
    assert result["pipeline_id"] == "test_plan"
    assert len(result["nodes"]) == 2


# ── 2. Output has required fields ──

def test_output_has_required_fields():
    result = reviewed_plan_to_pipeline_dict(_valid_plan())
    assert "version" in result
    assert "modality" in result
    assert "execution" in result
    assert "nodes" in result
    assert "run_id" in result["execution"]


# ── 3. Name from pipeline_id ──

def test_name_from_pipeline_id():
    result = reviewed_plan_to_pipeline_dict(_valid_plan())
    assert result["pipeline_id"] == "test_plan"


# ── 4. Backend fill from catalog ──

def test_backend_fill_from_catalog():
    plan = {
        "pipeline_id": "test",
        "nodes": [{"id": "data_inspection", "depends_on": []}],
    }
    result = reviewed_plan_to_pipeline_dict(plan)
    assert result["nodes"][0]["backend"] == "python"


# ── 5. depends_on default ──

def test_depends_on_default():
    plan = {"pipeline_id": "test", "nodes": [{"id": "data_inspection"}]}
    result = reviewed_plan_to_pipeline_dict(plan)
    assert result["nodes"][0]["depends_on"] == []


# ── 6. params default ──

def test_params_default():
    plan = {"pipeline_id": "test", "nodes": [{"id": "data_inspection"}]}
    result = reviewed_plan_to_pipeline_dict(plan)
    assert result["nodes"][0]["params"] == {}


# ── 7. Unknown node → error ──

def test_unknown_node_error():
    plan = {"pipeline_id": "test", "nodes": [{"id": "nonexistent_xyz", "depends_on": []}]}
    result = reviewed_plan_to_pipeline_dict(plan)
    # Backend becomes "unknown" but conversion still succeeds
    assert result["nodes"][0]["backend"] == "unknown"


# ── 8. Duplicate node → error ──

def test_duplicate_node_error():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "data_inspection"}, {"id": "data_inspection"},
    ]}
    with pytest.raises(ValueError, match="Duplicate"):
        reviewed_plan_to_pipeline_dict(plan)


# ── 9. Unknown dependency → error ──

def test_unknown_dependency_error():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "data_inspection"},
        {"id": "motion_qc_subject", "depends_on": ["nonexistent"]},
    ]}
    with pytest.raises(ValueError, match="unknown node"):
        reviewed_plan_to_pipeline_dict(plan)


# ── 10. SPM node blocked ──

def test_spm_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_realign_subject", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" in policy["blocked_spm_nodes"]


# ── 11. DPABI execution blocked ──

def test_dpabi_execution_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "dpabi_subject_smooth", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "dpabi_subject_smooth" in policy["blocked_dpabi_execution_nodes"]


# ── 12. Manual required blocked ──

def test_unknown_node_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "nonexistent_gui_xyz", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "nonexistent_gui_xyz" in policy["blocked_unknown_nodes"]


# ── 13. Python QC allowed ──

def test_python_qc_allowed():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "motion_qc_subject", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "motion_qc_subject" in policy["allowed_python_nodes"]


# ── 14. GPU allowed ──

def test_gpu_allowed():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "gpu_alff_subject", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_alff_subject" in policy["allowed_gpu_nodes"]


# ── 15. Contract node allowed ──

def test_contract_allowed():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "dpabi_capability_inspection", "depends_on": []},
    ]}
    policy = classify_plan_nodes(plan)
    assert "dpabi_capability_inspection" in policy["allowed_contract_nodes"]


# ── 16. Adapter result JSON ──

def test_adapter_result_json():
    result = adapt_reviewed_plan(_valid_plan())
    d = result.to_dict()
    raw = json.dumps(d, ensure_ascii=False)
    back = json.loads(raw)
    assert back["ok"] is True


# ── 17. No file writes ──

def test_no_file_writes(tmp_path):
    import os
    before = set(os.listdir(tmp_path))
    adapt_reviewed_plan(_valid_plan())
    after = set(os.listdir(tmp_path))
    assert after == before


# ── 18. No executor ──

def test_no_executor():
    adapt_reviewed_plan(_valid_plan())


# ── 19. No runner ──

def test_no_runner():
    adapt_reviewed_plan(_valid_plan())


# ── 20. No rawdata writes ──

def test_no_rawdata():
    adapt_reviewed_plan(_valid_plan())


# ══════════════════════════════════════════════════════════════════════════════
# M6-T004b: spm_smoke_test allowlist
# ══════════════════════════════════════════════════════════════════════════════

# ── 21. spm_smoke_test classified as allowed_spm_smoke_nodes ──

def test_spm_smoke_test_allowed():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_smoke_test", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_smoke_test" in policy["allowed_spm_smoke_nodes"]
    assert "spm_smoke_test" not in policy["blocked_spm_nodes"]


# ── 22. spm_realign_subject still blocked ──

def test_spm_realign_still_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" in policy["blocked_spm_nodes"]
    assert "spm_realign_subject" not in policy["allowed_spm_smoke_nodes"]


# ── 23. spm_slice_timing_subject still blocked ──

def test_spm_slice_timing_still_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["blocked_spm_nodes"]


# ══════════════════════════════════════════════════════════════════════════════
# M6-T005d: sandbox-only spm_realign_subject allowlist
# ══════════════════════════════════════════════════════════════════════════════

# ── 24. spm_realign_subject + sandbox → allowed_spm_realign_sandbox_nodes ──

def test_spm_realign_sandbox_allowed():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" in policy["allowed_spm_realign_sandbox_nodes"]


# ── 25. spm_realign_subject without sandbox_mode → blocked ──

def test_spm_realign_no_sandbox_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" in policy["blocked_spm_nodes"]


# ── 26. spm_realign_subject without input_bold → blocked ──

def test_spm_realign_no_input_bold_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_realign_subject", "depends_on": [],
         "params": {"sandbox_mode": True}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_realign_subject" in policy["blocked_spm_nodes"]


# ── 27. spm_normalize_subject still blocked ──

def test_spm_normalize_still_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_normalize_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_normalize_subject" in policy["blocked_spm_nodes"]


# ══════════════════════════════════════════════════════════════════════════════
# M6-T006d: sandbox-only spm_slice_timing_subject allowlist
# ══════════════════════════════════════════════════════════════════════════════

def test_slice_timing_synthetic_allowed():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "examples/synthetic_bids/rawdata/sub-001/func/bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["allowed_spm_slice_timing_sandbox_nodes"]


def test_slice_timing_derivatives_allowed():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "allow_derivative_input": True,
                    "input_bold": "derivatives/rsfmri_preproc/sub-001/func/rsub-001_bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["allowed_spm_slice_timing_sandbox_nodes"]


def test_slice_timing_derivatives_no_allow_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "allow_derivative_input": False,
                    "input_bold": "derivatives/rsfmri_preproc/sub-001/func/rsub-001_bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["blocked_spm_nodes"]


def test_slice_timing_arbitrary_input_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "/etc/passwd"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["blocked_spm_nodes"]


def test_slice_timing_rawdata_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "data/sub-001/func/bold.nii"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["blocked_spm_nodes"]


def test_slice_timing_path_traversal_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "input_bold": "../etc/passwd"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["blocked_spm_nodes"]


def test_slice_timing_no_sandbox_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["blocked_spm_nodes"]


def test_slice_timing_no_input_bold_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_slice_timing_subject", "depends_on": [],
         "params": {"sandbox_mode": True}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_slice_timing_subject" in policy["blocked_spm_nodes"]


def test_spm_coregister_still_blocked():
    plan = {"pipeline_id": "test", "nodes": [
        {"id": "spm_coregister_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "spm_coregister_subject" in policy["blocked_spm_nodes"]
