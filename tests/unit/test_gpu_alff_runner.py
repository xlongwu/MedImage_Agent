"""Tests for gpu_alff_subject runner (M8-GPU-T007d)."""

from __future__ import annotations

import json

from src.backend.app.runtime.node_registry import NODE_REGISTRY
from src.backend.app.tools.gpu_alff_runner import run_gpu_alff_subject


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"
    func.parent.mkdir(parents=True, exist_ok=True)
    func.write_bytes(b"\x00" * 100)
    return str(func), str(deriv)


def test_node_registered():
    assert "gpu_alff_subject" in NODE_REGISTRY


# ── Basic ──


def test_approved_false_blocks():
    r = run_gpu_alff_subject(
        subject_id="s",
        input_functional="/d/f.nii",
        derivatives_dir="/d",
        run_id="r1",
        tr=2.0,
        approved=False,
    )
    assert r["ok"] is False


def test_invalid_subject_blocked():
    r = run_gpu_alff_subject(
        subject_id="", input_functional="/d/f.nii", derivatives_dir="/d", run_id="r1", tr=2.0
    )
    assert r["ok"] is False


# ── Input ──


def test_scoped_derivative_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="sub-001", input_functional=func, derivatives_dir=deriv, run_id="r1", tr=2.0
    )
    assert r["ok"] is True


def test_rawdata_input_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    (raw / "func.nii").write_bytes(b"\x00")
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s",
        input_functional=str(raw / "func.nii"),
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
    )
    assert r["ok"] is False


def test_arbitrary_input_blocked(tmp_path):
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s", input_functional="/etc/func.nii", derivatives_dir=deriv, run_id="r", tr=2.0
    )
    assert r["ok"] is False


# ── TR / band ──


def test_tr_too_small_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", tr=0.01
    )
    assert r["ok"] is False


def test_tr_too_large_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", tr=20.0
    )
    assert r["ok"] is False


def test_band_high_ge_nyquist_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        frequency_band=(0.01, 0.30),
    )
    assert r["ok"] is False


def test_band_high_le_low_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        frequency_band=(0.08, 0.01),
    )
    assert r["ok"] is False


# ── GPU guard ──


def test_invalid_device_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        device="cuda:1",
    )
    assert r["ok"] is False


def test_timeout_too_large_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        timeout_seconds=200,
    )
    assert r["ok"] is False


# ── Output ──


def test_output_in_derivatives(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="sub-001",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r1",
        tr=2.0,
        dry_run=True,
    )
    assert r["ok"] is True
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "gpu_alff_subject" in od


# ── No CUDA ──


def test_no_cuda(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", tr=2.0
    )
    assert r["cuda_called"] is False
    assert r["tensor_allocated"] is False


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "gpu_alff_subject" not in policy.get("allowed_gpu_synthetic_smoke_nodes", [])


def test_json_serializable(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_alff_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", tr=2.0
    )
    json.dumps(r)
