"""Sandbox contract tests for gpu_alff_subject (M8-GPU-T007e)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from src.backend.app.tools.gpu_alff_runner import run_gpu_alff_subject
from src.backend.app.runtime.node_registry import NODE_REGISTRY


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"
    func.parent.mkdir(parents=True, exist_ok=True)
    func.write_bytes(b"\x00" * 100)
    return str(func), str(deriv)


# ── Registry ──

def test_node_registered():
    assert "gpu_alff_subject" in NODE_REGISTRY


# ── Input contract ──

def test_scoped_derivative_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0)
    assert r["ok"] is True


def test_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir()
    (raw / "f.nii").write_bytes(b"\x00")
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="s", input_functional=str(raw / "f.nii"),
        derivatives_dir=deriv, run_id="r", tr=2.0)
    assert r["ok"] is False


def test_arbitrary_input_blocked(tmp_path):
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="s", input_functional="/tmp/f.nii",
        derivatives_dir=deriv, run_id="r", tr=2.0)
    assert r["ok"] is False


# ── TR / band ──

def test_band_high_ge_nyquist_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0, frequency_band=(0.01, 0.30))
    assert r["ok"] is False


def test_band_high_le_low_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0, frequency_band=(0.08, 0.01))
    assert r["ok"] is False


# ── Output ──

def test_output_in_derivatives(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="sub-001", input_functional=func,
        derivatives_dir=deriv, run_id="r1", tr=2.0, dry_run=True)
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "gpu_alff_subject" in od


# ── No CUDA ──

def test_no_cuda(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0)
    assert r["cuda_called"] is False
    assert r["tensor_allocated"] is False


# ── Policy ──

def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    plan = {"pipeline_id": "t", "nodes": [
        {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
    ]}
    policy = classify_plan_nodes(plan)
    assert "gpu_alff_subject" not in policy.get("allowed_gpu_synthetic_smoke_nodes", [])
    assert "gpu_alff_subject" not in policy.get("allowed_contract_nodes", [])


def test_gpu_smoke_allowed():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    nid = "gpu_synthetic_smoke"
    plan = {"pipeline_id": "t", "nodes": [
        {"id": nid, "depends_on": [], "params": {"sandbox_mode": True, "synthetic_smoke": True,
            "device_policy": "guarded_auto_cpu_cuda0", "memory_policy": "bounded_1e6_elements_256mb",
            "output_policy": "reports_dir_gpu_smoke_only"}},
    ]}
    policy = classify_plan_nodes(plan)
    assert nid in policy["allowed_gpu_synthetic_smoke_nodes"]


def test_other_gpu_subject_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    for nid in ["gpu_reho_subject", "gpu_temporal_filtering_subject"]:
        plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
        policy = classify_plan_nodes(plan)
        assert nid not in policy.get("allowed_contract_nodes", [])
        assert nid not in policy.get("allowed_gpu_synthetic_smoke_nodes", [])


def test_json_serializable(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(subject_id="s", input_functional=func,
        derivatives_dir=deriv, run_id="r", tr=2.0)
    json.dumps(r)
