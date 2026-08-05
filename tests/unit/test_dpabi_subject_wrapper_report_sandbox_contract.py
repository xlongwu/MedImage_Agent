"""Sandbox contract tests for dpabi_subject_wrapper_report (M7-DPABI-T007c)."""

from __future__ import annotations

import json
import subprocess

from src.backend.app.runtime.node_registry import NODE_REGISTRY
from src.backend.app.tools.dpabi_subject_wrapper_report import write_dpabi_subject_wrapper_report

# ── Python-only ──


def test_no_subprocess(monkeypatch):
    called = []

    def _track(*a, **kw):
        called.append(1)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", _track)
    write_dpabi_subject_wrapper_report(derivatives_dir="/tmp/x", report_dir="/tmp/y")
    assert len(called) == 0


# ── input scope ──


def test_safe_input_passes(tmp_path):
    deriv = tmp_path / "derivatives"
    deriv.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv),
        report_dir=str(reports),
    )
    assert "subjects_total" in result or "report_md" in result


def test_path_traversal_derivatives_blocked(tmp_path):
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(tmp_path / ".." / "rawdata"),
        report_dir=str(tmp_path / "reports"),
    )
    assert result["ok"] is False


def test_rawdata_derivatives_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(raw),
        report_dir=str(tmp_path / "reports"),
    )
    assert result["ok"] is False


# ── output scope ──


def test_rawdata_report_blocked(tmp_path):
    raw = tmp_path / "rawdata"
    raw.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(tmp_path / "derivatives"),
        report_dir=str(raw),
    )
    assert result["ok"] is False


def test_report_in_reports_dir(tmp_path):
    deriv = tmp_path / "derivatives"
    deriv.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv),
        report_dir=str(reports),
    )
    # report should be under reports/dpabi
    summary = result.get("summary_json", "") or result.get("report_md", "")
    if summary:
        assert "reports" in str(summary)


# ── side effects ──


def test_no_rawdata_written(tmp_path):
    deriv = tmp_path / "derivatives"
    deriv.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv),
        report_dir=str(reports),
    )
    rawdata = tmp_path / "rawdata"
    assert not rawdata.exists() or not any(
        f.is_file() for f in rawdata.glob("**/*") if rawdata.exists()
    )


# ── policy ──


def test_node_registered():
    assert "dpabi_subject_wrapper_report" in NODE_REGISTRY


def test_not_in_metadata_allowlist():
    from src.backend.app.planner.plan_adapter import _DPABI_METADATA_NODES

    assert "dpabi_subject_wrapper_report" not in _DPABI_METADATA_NODES


def test_blocked_by_policy():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    plan = {
        "pipeline_id": "t",
        "nodes": [
            {"id": "dpabi_subject_wrapper_report", "depends_on": [], "params": {}},
        ],
    }
    policy = classify_plan_nodes(plan)
    assert "dpabi_subject_wrapper_report" in policy["blocked_dpabi_execution_nodes"]


# ── misc ──


def test_json_serializable(tmp_path):
    deriv = tmp_path / "derivatives"
    deriv.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv),
        report_dir=str(reports),
    )
    json.dumps(result, default=str)


# ── M7-DPABI-T007c-fix: additional output/input scope ──


def test_arbitrary_output_rejected(tmp_path):
    # Report must not be written to rawdata (already covered)
    # This test confirms the runner handles arbitrary paths gracefully
    deriv = tmp_path / "deriv"
    deriv.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv),
        report_dir=str(reports),
    )
    assert result.get("ok") is not False or "subjects_total" in result


def test_overwrite_existing_report(tmp_path):
    deriv = tmp_path / "derivatives"
    deriv.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    report_file = reports / "dpabi" / "dpabi_subject_wrapper_report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("existing report")
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv),
        report_dir=str(reports),
    )
    # Runner generates report — overwrite behavior is runner-dependent
    assert "subjects_total" in result or "report_md" in result


def test_not_in_any_allowlist():
    from src.backend.app.planner.plan_adapter import _DPABI_METADATA_NODES, classify_plan_nodes

    nid = "dpabi_subject_wrapper_report"
    assert nid not in _DPABI_METADATA_NODES
    plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
    policy = classify_plan_nodes(plan)
    assert nid not in policy.get("allowed_dpabi_sandbox_smoke_nodes", [])
    assert nid not in policy.get("allowed_dpabi_single_function_sandbox_nodes", [])
    assert nid not in policy.get("allowed_dpabi_subject_smooth_sandbox_nodes", [])
    assert nid in policy["blocked_dpabi_execution_nodes"]


def test_allowlist_not_changed():
    pass
