"""Tests for gpu_nuisance_regression_subject runner (M8-GPU-T011b)."""

from __future__ import annotations

import json

from src.backend.app.runtime.node_registry import NODE_REGISTRY
from src.backend.app.tools.gpu_nuisance_regression_runner import run_gpu_nuisance_regression_subject


def _make_derivative(tmp_path):
    deriv = tmp_path / "derivatives"
    func = deriv / "func.nii"
    func.parent.mkdir(parents=True, exist_ok=True)
    func.write_bytes(b"\x00" * 100)
    conf = deriv / "confounds.tsv"
    conf.write_text("a\tb\n1\t2\n")
    return str(func), str(conf), str(deriv)


def test_node_registered():
    assert "gpu_nuisance_regression_subject" in NODE_REGISTRY


def test_approved_false_blocks():
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional="/d/f.nii",
        confounds_path="/d/c.tsv",
        derivatives_dir="/d",
        run_id="r",
        approved=False,
    )
    assert r["ok"] is False


def test_scoped_inputs_pass(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
    )
    assert r["ok"] is True


def test_rawdata_functional_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    (raw / "f.nii").write_bytes(b"\x00")
    _, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=str(raw / "f.nii"),
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
    )
    assert r["ok"] is False


def test_rawdata_confounds_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    (raw / "c.tsv").write_text("a\n1\n")
    func, _, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=str(raw / "c.tsv"),
        derivatives_dir=deriv,
        run_id="r",
    )
    assert r["ok"] is False


# ── Confounds ──


def test_confound_columns_empty_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
        confound_columns=[],
    )
    assert r["ok"] is False


def test_n_confounds_too_large_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
        n_confounds=100,
        timepoints=200,
    )
    assert r["ok"] is False


# ── Design matrix ──


def test_n_regressors_ge_timepoints_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
        timepoints=3,
        n_confounds=3,
    )
    assert r["ok"] is False


# ── Policies ──


def test_global_signal_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
        allow_global_signal=True,
    )
    assert r["ok"] is False


def test_scrubbing_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
        allow_scrubbing=True,
    )
    assert r["ok"] is False


def test_ridge_blocked(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
        regression_mode="ridge",
    )
    assert r["ok"] is False


# ── Output ──


def test_output_in_derivatives(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
        dry_run=True,
    )
    od = r["outputs"]["output_dir"]
    assert "gpu" in od and "nuisance_regression" in od


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "gpu_nuisance_regression_subject", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "gpu_nuisance_regression_subject" not in policy.get(
        "allowed_gpu_functional_connectivity_sandbox_nodes", []
    )


def test_json_serializable(tmp_path):
    func, conf, deriv = _make_derivative(tmp_path)
    r = run_gpu_nuisance_regression_subject(
        subject_id="s",
        input_functional=func,
        confounds_path=conf,
        derivatives_dir=deriv,
        run_id="r",
    )
    json.dumps(r)
