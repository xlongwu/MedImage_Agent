"""Tests for dpabi_subject_wrapper_report safety (M7-DPABI-T007b)."""

from __future__ import annotations

import json, subprocess
from pathlib import Path
import pytest
from src.backend.app.tools.dpabi_subject_wrapper_report import write_dpabi_subject_wrapper_report


# ── Python-only ──

def test_no_subprocess(monkeypatch):
    called = []
    def _track(*a, **kw): called.append(1); return subprocess.CompletedProcess([], 0)
    monkeypatch.setattr(subprocess, "run", _track)
    write_dpabi_subject_wrapper_report(derivatives_dir="/tmp/x", report_dir="/tmp/y")
    assert len(called) == 0


# ── input/output scope ──

def test_path_traversal_derivatives_blocked(tmp_path):
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(tmp_path / ".." / "rawdata"),
        report_dir=str(tmp_path / "reports"),
    )
    assert result["ok"] is False


def test_rawdata_derivatives_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(raw),
        report_dir=str(tmp_path / "reports"),
    )
    assert result["ok"] is False


def test_rawdata_report_blocked(tmp_path):
    raw = tmp_path / "rawdata"; raw.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(tmp_path / "derivatives"),
        report_dir=str(raw),
    )
    assert result["ok"] is False


def test_safe_paths_reach_scan(tmp_path):
    deriv = tmp_path / "derivatives"; deriv.mkdir()
    reports = tmp_path / "reports"; reports.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv), report_dir=str(reports),
    )
    # Empty scan → 0 subjects, report generated
    assert "subjects_total" in result or "report_md" in result


# ── misc ──

def test_json_serializable(tmp_path):
    deriv = tmp_path / "derivatives"; deriv.mkdir()
    reports = tmp_path / "reports"; reports.mkdir()
    result = write_dpabi_subject_wrapper_report(
        derivatives_dir=str(deriv), report_dir=str(reports),
    )
    json.dumps(result, default=str)
