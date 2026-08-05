"""Tests for gpu_safety.py (M8-GPU-T003). Pure Python — no CUDA required."""

from __future__ import annotations

import json

from src.backend.app.safety.gpu_safety import (
    check_cuda_availability,
    estimate_tensor_bytes,
    normalize_gpu_exception,
    validate_gpu_concurrency,
    validate_gpu_device,
    validate_gpu_memory_budget,
    validate_gpu_runtime_request,
    validate_gpu_timeout,
    validate_live_gpu_memory,
)

# ── Device ──


def test_auto_allowed():
    r = validate_gpu_device("auto")
    assert r.ok


def test_cpu_allowed():
    r = validate_gpu_device("cpu")
    assert r.ok


def test_cuda0_allowed():
    r = validate_gpu_device("cuda:0")
    assert r.ok


def test_cuda1_blocked():
    r = validate_gpu_device("cuda:1")
    assert not r.ok


def test_cuda_blocked():
    r = validate_gpu_device("cuda")
    assert not r.ok


def test_mps_blocked():
    r = validate_gpu_device("mps")
    assert not r.ok


def test_empty_blocked():
    r = validate_gpu_device("")
    assert not r.ok


def test_none_blocked():
    r = validate_gpu_device(None)
    assert not r.ok


def test_semicolon_blocked():
    r = validate_gpu_device("cuda:0;rm -rf /")
    assert not r.ok


def test_path_traversal_blocked():
    r = validate_gpu_device("../rawdata")
    assert not r.ok


# ── CUDA availability ──


def test_unavailable_no_require_warns():
    r = check_cuda_availability(torch_cuda_available=False, require_gpu=False)
    assert r.ok
    assert len(r.warnings) >= 1


def test_unavailable_require_errors():
    r = check_cuda_availability(torch_cuda_available=False, require_gpu=True)
    assert not r.ok


def test_unknown_no_require_warns():
    r = check_cuda_availability(require_gpu=False)
    assert r.ok
    assert len(r.warnings) >= 1


def test_device_available_is_ok():
    r = check_cuda_availability(torch_cuda_available=True, device_count=2, require_gpu=True)
    assert r.ok


# ── Memory ──


def test_estimate_tensor_bytes():
    assert estimate_tensor_bytes([100, 100, 100]) == 100 * 100 * 100 * 4


def test_small_shape_ok():
    r = validate_gpu_memory_budget([64, 64, 64])
    assert r.ok


def test_1e6_elements_ok():
    r = validate_gpu_memory_budget([100, 100, 100])
    assert r.ok


def test_too_many_elements_blocked():
    r = validate_gpu_memory_budget([200, 200, 200])  # 8e6
    assert not r.ok


def test_negative_dim_blocked():
    r = validate_gpu_memory_budget([-1, 64, 64])
    assert not r.ok


def test_zero_dim_blocked():
    r = validate_gpu_memory_budget([0, 64, 64])
    assert not r.ok


def test_invalid_batch_size_blocked():
    r = validate_gpu_memory_budget([64, 64, 64], batch_size=0)
    assert not r.ok


def test_live_memory_guard_uses_runtime_free_vram_and_reserve():
    ok = validate_live_gpu_memory(
        estimated_peak_bytes=512 * 1024 * 1024,
        free_vram_bytes=4 * 1024 * 1024 * 1024,
        total_vram_bytes=8 * 1024 * 1024 * 1024,
    )
    blocked = validate_live_gpu_memory(
        estimated_peak_bytes=2 * 1024 * 1024 * 1024,
        free_vram_bytes=700 * 1024 * 1024,
        total_vram_bytes=8 * 1024 * 1024 * 1024,
    )
    assert ok.ok
    assert not blocked.ok
    assert any(item.code == "GPU_MEMORY_BUDGET_EXCEEDED" for item in blocked.errors)


# ── Timeout ──


def test_timeout_30_passes():
    r = validate_gpu_timeout(30)
    assert r.ok


def test_timeout_gt_30_blocked():
    r = validate_gpu_timeout(60)
    assert not r.ok


def test_timeout_0_blocked():
    r = validate_gpu_timeout(0)
    assert not r.ok


def test_timeout_negative_blocked():
    r = validate_gpu_timeout(-1)
    assert not r.ok


def test_timeout_none_passes():
    r = validate_gpu_timeout(None)
    assert r.ok


# ── Concurrency ──


def test_concurrency_idle_ok():
    r = validate_gpu_concurrency(active_jobs=0, max_concurrent_jobs=1)
    assert r.ok


def test_concurrency_busy_blocked():
    r = validate_gpu_concurrency(active_jobs=1, max_concurrent_jobs=1)
    assert not r.ok


def test_concurrency_invalid_max_blocked():
    r = validate_gpu_concurrency(max_concurrent_jobs=0)
    assert not r.ok


# ── OOM ──


def test_oom_normalized():
    r = normalize_gpu_exception(RuntimeError("CUDA out of memory"))
    assert not r.ok
    assert r.cleanup_recommended
    assert any(e.code == "GPU_OOM" for e in r.errors)


def test_generic_error_normalized():
    r = normalize_gpu_exception(ValueError("bad"))
    assert not r.ok
    assert any(e.code == "GPU_GUARD_FAILED" for e in r.errors)


# ── Combined ──


def test_combined_metadata_ok():
    r = validate_gpu_runtime_request(device="cpu", torch_cuda_available=False, require_gpu=False)
    assert r.ok


def test_combined_require_gpu_unavailable_blocked():
    r = validate_gpu_runtime_request(device="cuda:0", require_gpu=True, torch_cuda_available=False)
    assert not r.ok


def test_combined_invalid_device_and_shape():
    r = validate_gpu_runtime_request(
        device="invalid", shape=[10000, 10000, 10000], require_gpu=True, torch_cuda_available=False
    )
    assert not r.ok
    assert len(r.errors) >= 2


def test_result_json_serializable():
    r = validate_gpu_runtime_request(
        device="cuda:0",
        shape=[64, 64, 64],
        require_gpu=True,
        torch_cuda_available=True,
        device_count=1,
    )
    json.dumps(r.to_dict())
