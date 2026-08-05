"""Sandbox contract tests for gpu_temporal_filtering_subject (M8-GPU-T009c)."""

from __future__ import annotations

import json

from src.backend.app.runtime.node_registry import NODE_REGISTRY
from src.backend.app.tools.gpu_temporal_filtering_runner import run_gpu_temporal_filtering_subject


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"
    func.parent.mkdir(parents=True, exist_ok=True)
    func.write_bytes(b"\x00" * 100)
    return str(func), str(deriv)


def test_node_registered():
    assert "gpu_temporal_filtering_subject" in NODE_REGISTRY


# ── Input ──


def test_scoped_derivative_passes(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", tr=2.0
    )
    assert r["ok"] is True


def test_rawdata_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    (raw / "f.nii").write_bytes(b"\x00")
    _, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s",
        input_functional=str(raw / "f.nii"),
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
    )
    assert r["ok"] is False


# ── TR / band ──


def test_band_high_ge_nyquist_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        frequency_band=(0.01, 0.30),
    )
    assert r["ok"] is False


# ── Filter ──


def test_invalid_filter_mode_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        filter_mode="highpass",
    )
    assert r["ok"] is False


def test_filter_order_0_blocked(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        filter_order=0,
    )
    assert r["ok"] is False


# ── Mixed processing ──


def test_no_mixed_processing(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", tr=2.0
    )
    assert r["runs_alff"] is False
    assert r["runs_reho"] is False
    assert r["runs_functional_connectivity"] is False
    assert r["runs_nuisance_regression"] is False


# ── Output ──


def test_output_in_derivatives(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s",
        input_functional=func,
        derivatives_dir=deriv,
        run_id="r",
        tr=2.0,
        dry_run=True,
    )
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "temporal_filtering" in od


# ── Policy ──


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "gpu_temporal_filtering_subject", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "gpu_temporal_filtering_subject" not in policy.get("allowed_gpu_reho_sandbox_nodes", [])


def test_gpu_reho_allowed():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {
                "id": "gpu_reho_subject",
                "depends_on": [],
                "params": {
                    "sandbox_mode": True,
                    "subject_level": True,
                    "input_source": "scoped_functional_derivative",
                    "output_policy": "derivatives_dir_scoped",
                    "device_policy": "guarded_auto_cpu_cuda0",
                    "memory_policy": "bounded_subject_gpu_512mb",
                    "reho_policy": "bounded_neighborhood",
                },
            },
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "gpu_reho_subject" in policy["allowed_gpu_reho_sandbox_nodes"]


# ── M8-T009d: sandbox declaration allowlist ──


def test_temporal_sandbox_allowed():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {
                "id": "gpu_temporal_filtering_subject",
                "depends_on": [],
                "params": {
                    "sandbox_mode": True,
                    "subject_level": True,
                    "input_source": "scoped_functional_derivative",
                    "output_policy": "derivatives_dir_scoped",
                    "device_policy": "guarded_auto_cpu_cuda0",
                    "memory_policy": "bounded_subject_gpu_512mb",
                    "temporal_filter_policy": "bounded_bandpass_butterworth",
                },
            },
        ],
    }
    policy = classify_plan_nodes(plan)
    assert (
        "gpu_temporal_filtering_subject" in policy["allowed_gpu_temporal_filtering_sandbox_nodes"]
    )


def test_temporal_no_sandbox_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "gpu_temporal_filtering_subject", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert (
        "gpu_temporal_filtering_subject"
        not in policy["allowed_gpu_temporal_filtering_sandbox_nodes"]
    )


def test_json_serializable(tmp_path):
    func, deriv = _make_derivative(tmp_path)
    r = run_gpu_temporal_filtering_subject(
        subject_id="s", input_functional=func, derivatives_dir=deriv, run_id="r", tr=2.0
    )
    json.dumps(r)
