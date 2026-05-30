"""Sandbox contract tests for gpu_nuisance_regression_subject (M8-GPU-T011c)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from src.backend.app.tools.gpu_nuisance_regression_runner import run_gpu_nuisance_regression_subject
from src.backend.app.runtime.node_registry import NODE_REGISTRY


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"; func.parent.mkdir(parents=True, exist_ok=True); func.write_bytes(b"\x00" * 100)
    conf = deriv / "confounds.tsv"; conf.write_text("a\tb\n1\t2\n")
    return str(func), str(conf), str(deriv)


def test_node_registered():
    assert "gpu_nuisance_regression_subject" in NODE_REGISTRY


# ── Input ──

def test_scoped_inputs_pass(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=func, confounds_path=conf, derivatives_dir=deriv, run_id="r")
    assert r["ok"] is True


def test_rawdata_functional_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir(); (raw / "f.nii").write_bytes(b"\x00")
    _, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=str(raw / "f.nii"), confounds_path=conf, derivatives_dir=deriv, run_id="r")
    assert r["ok"] is False


def test_rawdata_confounds_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir(); (raw / "c.tsv").write_text("x\n1\n")
    func, _, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=func, confounds_path=str(raw / "c.tsv"), derivatives_dir=deriv, run_id="r")
    assert r["ok"] is False


# ── Policies ──

def test_global_signal_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=func, confounds_path=conf, derivatives_dir=deriv, run_id="r",
        allow_global_signal=True)
    assert r["ok"] is False


def test_scrubbing_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=func, confounds_path=conf, derivatives_dir=deriv, run_id="r",
        allow_scrubbing=True)
    assert r["ok"] is False


def test_ridge_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=func, confounds_path=conf, derivatives_dir=deriv, run_id="r",
        regression_mode="ridge")
    assert r["ok"] is False


# ── Output ──

def test_output_in_derivatives(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=func, confounds_path=conf, derivatives_dir=deriv, run_id="r", dry_run=True)
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "nuisance_regression" in od


# ── Policy ──

def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_nuisance_regression_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_nuisance_regression_subject" not in policy.get("allowed_gpu_functional_connectivity_sandbox_nodes", [])


def test_gpu_fc_allowed():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_functional_connectivity_subject", "depends_on": [], "params": {"sandbox_mode": True, "subject_level": True,
            "input_source": "scoped_functional_or_timeseries_derivative", "output_policy": "derivatives_dir_scoped",
            "device_policy": "guarded_auto_cpu_cuda0", "memory_policy": "bounded_subject_gpu_512mb",
            "fc_policy": "bounded_roi_pearson_only"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_functional_connectivity_subject" in policy["allowed_gpu_functional_connectivity_sandbox_nodes"]


def test_json_serializable(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(subject_id="s",
        input_functional=func, confounds_path=conf, derivatives_dir=deriv, run_id="r")
    json.dumps(r)
