"""Tests for gpu_reho_subject runner (M8-GPU-T008b)."""

from __future__ import annotations

import json
from pathlib import Path

from src.backend.app.runtime.node_registry import NODE_REGISTRY
from src.backend.app.tools.gpu_reho_runner import run_gpu_reho_subject


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"
    func.parent.mkdir(parents=True, exist_ok=True)
    func.write_bytes(b"\x00" * 100)
    return str(func), str(deriv)


def test_node_registered():
    assert "gpu_reho_subject" in NODE_REGISTRY


# ── Basic ──


def test_approved_false_blocks():
    r = run_gpu_reho_subject(
        subject_id="s",
        input_functional="/d/f.nii",
        derivatives_dir="/d",
        run_id="r",
        approved=False,
    )
    assert r["ok"] is False


def test_invalid_subject_blocked():
    r = run_gpu_reho_subject(
        subject_id="", input_functional="/d/f.nii", derivatives_dir="/d", run_id="r"
    )
    assert r["ok"] is False


# ── Input ──


def test_scoped_derivative_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r"
    )
    assert r["ok"] is True


def test_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    (raw / "f.nii").write_bytes(b"\x00")
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=str(raw / "f.nii"), derivatives_dir=deriv, run_id="r"
    )
    assert r["ok"] is False


def test_arbitrary_input_blocked(tmp_path):
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional="/tmp/f.nii", derivatives_dir=deriv, run_id="r"
    )
    assert r["ok"] is False


# ── Mask ──


def test_valid_mask_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    mask = Path(deriv) / "mask.nii"
    mask.write_bytes(b"\x00")
    r = run_gpu_reho_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        mask_path=str(mask),
    )
    assert r["ok"] is True


def test_rawdata_mask_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    raw = tmp_path / "rawdata"
    raw.mkdir()
    (raw / "m.nii").write_bytes(b"\x00")
    r = run_gpu_reho_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        mask_path=str(raw / "m.nii"),
    )
    assert r["ok"] is False


# ── Neighborhood ──


def test_neighborhood_27_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", neighborhood=27
    )
    assert r["ok"] is True


def test_neighborhood_0_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", neighborhood=0
    )
    assert r["ok"] is False


def test_neighborhood_125_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", neighborhood=125
    )
    assert r["ok"] is False


# ── GPU guard ──


def test_invalid_device_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", device="cuda:1"
    )
    assert r["ok"] is False


# ── Output ──


def test_output_in_derivatives(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="sub-001",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r1",
        dry_run=True,
    )
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "gpu_reho_subject" in od


# ── No CUDA ──


def test_no_cuda(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r"
    )
    assert r["cuda_called"] is False
    assert r["tensor_allocated"] is False


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "gpu_reho_subject", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "gpu_reho_subject" not in policy.get("allowed_gpu_alff_sandbox_nodes", [])


def test_json_serializable(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_reho_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r"
    )
    json.dumps(r)
