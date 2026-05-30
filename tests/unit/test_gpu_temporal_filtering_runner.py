"""Tests for gpu_temporal_filtering_subject runner (M8-GPU-T009b)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from src.backend.app.tools.gpu_temporal_filtering_runner import run_gpu_temporal_filtering_subject
from src.backend.app.runtime.node_registry import NODE_REGISTRY


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"
    func.parent.mkdir(parents=True, exist_ok=True)
    func.write_bytes(b"\x00" * 100)
    return str(func), str(deriv)


def test_node_registered():
    assert "gpu_temporal_filtering_subject" in NODE_REGISTRY


def test_approved_false_blocks():
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional="/d/f.nii",
        derivatives_dir="/d", run_id="r", tr=2.0, approved=False)
    assert r["ok"] is False


def test_scoped_derivative_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0)
    assert r["ok"] is True


def test_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir(); (raw / "f.nii").write_bytes(b"\x00")
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=str(raw / "f.nii"),
        derivatives_dir=deriv, run_id="r", tr=2.0)
    assert r["ok"] is False


# ── TR / band ──

def test_tr_too_small_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=0.01)
    assert r["ok"] is False


def test_band_high_ge_nyquist_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0, frequency_band=(0.01, 0.30))
    assert r["ok"] is False


# ── Filter params ──

def test_invalid_filter_mode_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0, filter_mode="highpass")
    assert r["ok"] is False


def test_invalid_filter_order_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0, filter_order=0)
    assert r["ok"] is False


# ── Mixed processing ──

def test_no_mixed_processing(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0)
    assert r["runs_nuisance_regression"] is False
    assert r["runs_alff"] is False
    assert r["runs_reho"] is False
    assert r["runs_functional_connectivity"] is False


# ── Output ──

def test_output_in_derivatives(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0, dry_run=True)
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "temporal_filtering" in od


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_temporal_filtering_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_temporal_filtering_subject" not in policy.get("allowed_gpu_reho_sandbox_nodes", [])


def test_json_serializable(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0)
    json.dumps(r)
