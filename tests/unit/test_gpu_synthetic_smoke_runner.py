"""Tests for gpu_synthetic_smoke runner (M8-GPU-T006b)."""

from __future__ import annotations

import json

from src.backend.app.runtime.node_registry import NODE_REGISTRY
from src.backend.app.tools.gpu_smoke_runner import run_gpu_synthetic_smoke

# ── Registration ──


def test_node_registered():
    assert "gpu_synthetic_smoke" in NODE_REGISTRY


# ── Runner guard ──


def test_valid_request_ok():
    r = run_gpu_synthetic_smoke()
    assert r["ok"] is True
    assert r["synthetic_only"] is True
    assert "gpu_guard" in r


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


def test_approved_false_blocks():
    r = run_gpu_synthetic_smoke(approved=False)
    assert r["ok"] is False


# ── Output scope ──


def test_report_written(tmp_path):
    r = run_gpu_synthetic_smoke(reports_dir=str(tmp_path), run_id="test")
    assert r["ok"] is True
    report = tmp_path / "gpu" / "smoke" / "test" / "gpu_synthetic_smoke_result.json"
    assert report.exists()


# ── No CUDA / no GPU ──


def test_no_cuda_called():
    r = run_gpu_synthetic_smoke()
    assert r["cuda_called"] is False
    assert r["gpu_called"] is False
    assert r["tensor_allocated"] is False
    assert r["runs_training"] is False
    assert r["runs_model_inference"] is False


# ── Policy ──


def test_blocked_by_safe_allowlist():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "gpu_synthetic_smoke", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    # gpu backend → allowed_gpu_nodes, then blocked by safe allowlist
    assert "gpu_synthetic_smoke" in policy.get(
        "allowed_gpu_nodes", []
    ) or "gpu_synthetic_smoke" not in policy.get("allowed_contract_nodes", [])
    assert "gpu_synthetic_smoke" not in policy.get("allowed_python_nodes", [])


def test_result_json_serializable():
    r = run_gpu_synthetic_smoke()
    json.dumps(r)
