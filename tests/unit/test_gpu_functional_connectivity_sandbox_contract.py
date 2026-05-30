"""Sandbox contract tests for gpu_functional_connectivity_subject (M8-GPU-T010c)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from src.backend.app.tools.gpu_functional_connectivity_runner import run_gpu_functional_connectivity_subject
from src.backend.app.runtime.node_registry import NODE_REGISTRY


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"
    func.parent.mkdir(parents=True, exist_ok=True)
    func.write_bytes(b"\x00" * 100)
    return str(func), str(deriv)


def test_node_registered():
    assert "gpu_functional_connectivity_subject" in NODE_REGISTRY


# ── Input ──

def test_scoped_derivative_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=func, derivatives_dir=deriv, run_id="r")
    assert r["ok"] is True


def test_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir(); (raw / "f.nii").write_bytes(b"\x00")
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=str(raw / "f.nii"), derivatives_dir=deriv, run_id="r")
    assert r["ok"] is False


def test_missing_input_blocked():
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        derivatives_dir="/d", run_id="r")
    assert r["ok"] is False


# ── Atlas / ROI ──

def test_invalid_atlas_source_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=func, derivatives_dir=deriv, run_id="r", atlas_source="custom")
    assert r["ok"] is False


def test_roi_out_of_range_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=func, derivatives_dir=deriv, run_id="r", roi_count=1000)
    assert r["ok"] is False


# ── Correlation ──

def test_partial_correlation_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=func, derivatives_dir=deriv, run_id="r", correlation_method="partial")
    assert r["ok"] is False


def test_fisher_z_non_bool_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=func, derivatives_dir=deriv, run_id="r", fisher_z="yes")
    assert r["ok"] is False


# ── Output ──

def test_output_in_derivatives(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=func, derivatives_dir=deriv, run_id="r", dry_run=True)
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "functional_connectivity" in od


# ── Policy ──

def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_functional_connectivity_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_functional_connectivity_subject" not in policy.get("allowed_gpu_temporal_filtering_sandbox_nodes", [])


def test_gpu_temporal_allowed():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_temporal_filtering_subject", "depends_on": [], "params": {"sandbox_mode": True, "subject_level": True,
            "input_source": "scoped_functional_derivative", "output_policy": "derivatives_dir_scoped",
            "device_policy": "guarded_auto_cpu_cuda0", "memory_policy": "bounded_subject_gpu_512mb",
            "temporal_filter_policy": "bounded_bandpass_butterworth"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_temporal_filtering_subject" in policy["allowed_gpu_temporal_filtering_sandbox_nodes"]


# ── M8-T010d: sandbox declaration allowlist ──

def test_fc_sandbox_allowed():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_functional_connectivity_subject", "depends_on": [],
         "params": {"sandbox_mode": True, "subject_level": True,
                    "input_source": "scoped_functional_or_timeseries_derivative",
                    "output_policy": "derivatives_dir_scoped",
                    "device_policy": "guarded_auto_cpu_cuda0",
                    "memory_policy": "bounded_subject_gpu_512mb",
                    "fc_policy": "bounded_roi_pearson_only"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_functional_connectivity_subject" in policy["allowed_gpu_functional_connectivity_sandbox_nodes"]


def test_fc_no_sandbox_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_functional_connectivity_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_functional_connectivity_subject" not in policy["allowed_gpu_functional_connectivity_sandbox_nodes"]


def test_json_serializable(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_functional_connectivity_subject(subject_id="s",
        input_functional=func, derivatives_dir=deriv, run_id="r")
    json.dumps(r)
