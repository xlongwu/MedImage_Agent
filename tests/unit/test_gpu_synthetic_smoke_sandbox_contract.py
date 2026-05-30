"""Sandbox contract tests for gpu_synthetic_smoke (M8-GPU-T006c)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from src.backend.app.tools.gpu_smoke_runner import run_gpu_synthetic_smoke
from src.backend.app.runtime.node_registry import NODE_REGISTRY


# ── Registry / catalog ──

def test_node_registered():
    assert "gpu_synthetic_smoke" in NODE_REGISTRY


def test_runner_callable():
    from src.backend.app.runtime.node_registry import get_node_runner
    runner = get_node_runner("gpu_synthetic_smoke")
    assert callable(runner)


# ── Guard behavior ──

def test_valid_smoke_ok():
    r = run_gpu_synthetic_smoke()
    assert r["ok"] is True
    assert r["synthetic_only"] is True


def test_invalid_device_blocked():
    r = run_gpu_synthetic_smoke(device="cuda:1")
    assert r["ok"] is False


def test_large_shape_blocked():
    r = run_gpu_synthetic_smoke(shape=(10000, 10000))
    assert r["ok"] is False


def test_timeout_gt_30_blocked():
    r = run_gpu_synthetic_smoke(timeout_seconds=60)
    assert r["ok"] is False


def test_concurrency_busy_blocked():
    r = run_gpu_synthetic_smoke(active_jobs=1, max_concurrent_jobs=1)
    assert r["ok"] is False


def test_require_gpu_unavailable_blocked():
    r = run_gpu_synthetic_smoke(require_gpu=True, torch_cuda_available=False)
    assert r["ok"] is False


def test_require_gpu_false_warns():
    r = run_gpu_synthetic_smoke(require_gpu=False, torch_cuda_available=False)
    assert r["ok"] is True
    assert r["gpu_guard"]["warnings"]


# ── No CUDA / no GPU ──

def test_no_cuda_gpu_tensor():
    r = run_gpu_synthetic_smoke()
    assert r["cuda_called"] is False
    assert r["gpu_called"] is False
    assert r["tensor_allocated"] is False
    assert r["runs_training"] is False
    assert r["runs_model_inference"] is False


def test_no_subprocess_import(monkeypatch):
    import builtins
    real_import = builtins.__import__
    def mock(name, *args, **kw):
        if name == "torch":
            raise ImportError("GPU smoke must not import torch")
        return real_import(name, *args, **kw)
    monkeypatch.setattr(builtins, "__import__", mock)
    r = run_gpu_synthetic_smoke()
    assert r["ok"] is True


# ── Output scope ──

def test_report_written(tmp_path):
    r = run_gpu_synthetic_smoke(reports_dir=str(tmp_path), run_id="test")
    assert r["ok"] is True
    report = tmp_path / "gpu" / "smoke" / "test" / "gpu_synthetic_smoke_result.json"
    assert report.exists()


def test_no_rawdata_written(tmp_path):
    run_gpu_synthetic_smoke(reports_dir=str(tmp_path), run_id="test")
    rawdata = tmp_path / "rawdata"
    assert not rawdata.exists() or not any(f.is_file() for f in rawdata.glob("**/*"))


# ── Policy ──

def test_blocked_by_safe_allowlist():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    nid = "gpu_synthetic_smoke"
    plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
    policy = classify_plan_nodes(plan)
    # gpu backend → allowed_gpu_nodes (blocked by safe allowlist)
    assert nid in policy.get("allowed_gpu_nodes", [])
    assert nid not in policy.get("allowed_python_nodes", [])
    assert nid not in policy.get("allowed_contract_nodes", [])


def test_gpu_contract_nodes_allowlisted():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    nid = "alff_falff_gpu_candidate_contract"
    plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
    policy = classify_plan_nodes(plan)
    assert nid in policy["allowed_contract_nodes"]


def test_gpu_subject_exec_still_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    for nid in ["gpu_alff_subject", "gpu_reho_subject"]:
        plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
        policy = classify_plan_nodes(plan)
        assert nid not in policy.get("allowed_contract_nodes", [])
        assert nid not in policy.get("allowed_python_nodes", [])


# ── misc ──

def test_json_serializable():
    r = run_gpu_synthetic_smoke()
    json.dumps(r)
