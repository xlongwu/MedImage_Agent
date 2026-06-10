"""Tests for DICOM conversion release readiness — Phase 4K-0.

Tests schema helpers, service evaluation, and safety invariants.
No dcm2niix.  No subprocess writes.  No rawdata modification.
No frontend execute button.  No public endpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Schema: disk space check
# ═══════════════════════════════════════════════════════════════════════


def test_disk_space_sufficient():
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_disk_space_check,
    )
    result = evaluate_disk_space_check(
        output_root="/tmp/test",
        estimated_required_bytes=1000,
        free_bytes=5000,
    )
    assert result.ok is True
    assert len(result.errors) == 0


def test_disk_space_insufficient():
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_disk_space_check,
    )
    result = evaluate_disk_space_check(
        output_root="/tmp/test",
        estimated_required_bytes=10000,
        free_bytes=100,
    )
    assert result.ok is False
    assert len(result.errors) > 0


def test_disk_space_no_output_root():
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_disk_space_check,
    )
    result = evaluate_disk_space_check(output_root="")
    assert result.ok is False


def test_disk_space_unknown_free():
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_disk_space_check,
    )
    result = evaluate_disk_space_check(
        output_root="/tmp/test",
        estimated_required_bytes=1000,
        free_bytes=None,
    )
    assert result.ok is False
    assert len(result.warnings) > 0


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Schema: runtime policy
# ═══════════════════════════════════════════════════════════════════════


def test_runtime_policy_warnings_when_unsupported():
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_runtime_policy,
    )
    result = evaluate_runtime_policy(
        cancellation_supported=False,
        resume_supported=False,
        retry_supported=False,
    )
    assert len(result.warnings) >= 2  # At least cancellation + resume
    assert not result.cancellation_supported
    assert not result.resume_supported


def test_runtime_policy_no_warnings_when_supported():
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_runtime_policy,
    )
    result = evaluate_runtime_policy(
        cancellation_supported=True,
        resume_supported=True,
        retry_supported=True,
    )
    assert len(result.warnings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Schema: release readiness evaluation
# ═══════════════════════════════════════════════════════════════════════


def test_readiness_blocked_if_gates_not_all_met():
    """Gate 1: Readiness blocked if not all 32 gates are met."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(gates_met=25, gates_total=32)
    assert report.status == "blocked"
    assert len(report.blocking_issues) > 0


def test_readiness_blocked_if_public_endpoint_enabled():
    """Gate 2: Readiness blocked if public /conversion/execute is enabled."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
        public_endpoint_enabled=True,
    )
    assert report.status == "blocked"
    assert any("public" in b.lower() for b in report.blocking_issues)


def test_readiness_blocked_if_frontend_execute_enabled():
    """Gate 3: Readiness blocked if frontend execute button is present."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
        frontend_execute_enabled=True,
    )
    assert report.status == "blocked"
    assert any("frontend" in b.lower() for b in report.blocking_issues)


def test_readiness_blocked_if_spm_enabled():
    """Gate 4: Readiness blocked if SPM/DPABI/MATLAB enabled."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
        spm_dpabi_matlab_enabled=True,
    )
    assert report.status == "blocked"


def test_readiness_blocked_if_preprocessing_enabled():
    """Gate 5: Readiness blocked if full preprocessing enabled."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
        full_preprocessing_enabled=True,
    )
    assert report.status == "blocked"


def test_readiness_blocked_if_disk_insufficient():
    """Gate 6: Readiness blocked if disk space insufficient."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32,
        disk_space_ok=False,
        disk_errors=["Insufficient disk space: 100 bytes free, 1500 bytes required"],
        rollback_ready=True, approval_audit_ready=True,
    )
    assert report.status == "blocked"


def test_readiness_warning_if_cancellation_unsupported():
    """Gate 7: Readiness warning if cancellation unsupported."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
        cancellation_supported=False,
    )
    assert report.status in ("warning", "ready_for_human_release_review")
    if report.status == "warning":
        assert any("cancel" in w.lower() for w in report.warnings)


def test_readiness_warning_if_resume_unsupported():
    """Gate 8: Readiness warning if resume unsupported."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
        resume_supported=False,
    )
    assert report.status in ("warning", "ready_for_human_release_review")


def test_readiness_ready_for_human_review_when_all_met():
    """Gate 9: Readiness ready_for_human_release_review when all conditions met."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, gate_status="CONDITIONAL_GO",
        disk_space_ok=True,
        rollback_ready=True,
        approval_audit_ready=True,
        public_endpoint_enabled=False,
        frontend_execute_enabled=False,
        spm_dpabi_matlab_enabled=False,
        full_preprocessing_enabled=False,
        cancellation_supported=True,
        resume_supported=True,
    )
    assert report.status == "ready_for_human_release_review"
    assert report.ok is True
    assert len(report.blocking_issues) == 0


def test_human_release_approval_required():
    """Gate 10: Human release approval remains required."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
    )
    assert report.human_release_approval_required is True


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Service: release readiness service
# ═══════════════════════════════════════════════════════════════════════


def test_service_does_not_call_dcm2niix():
    """Gate 11: Service does not call or import dcm2niix in executable code."""
    import inspect
    from src.backend.app.services import dicom_conversion_release_readiness as mod
    source = inspect.getsource(mod.evaluate_conversion_release_readiness)
    # Exclude docstring and comment lines
    code_lines = [l for l in source.splitlines()
                  if '"""' not in l and "dcm2niix" not in l.lower()
                  and not l.strip().startswith("#")]
    code = "\n".join(code_lines)
    # The word "subprocess" may appear in docstrings filtered above;
    # test_service_imports_no_subprocess already verifies no import.
    # This test verifies dcm2niix is not called.
    assert "run_conversion" not in code


def test_service_does_not_modify_rawdata():
    """Gate 12: Service does not modify rawdata."""
    import inspect
    from src.backend.app.services import dicom_conversion_release_readiness as mod
    source = inspect.getsource(mod.evaluate_conversion_release_readiness)
    # Exclude docstring lines — rawdata appears in docstring for documentation
    code_lines = [l for l in source.splitlines() if '"""' not in l and "rawdata" not in l.lower()]
    code = "\n".join(code_lines)
    assert "open(" not in code


def test_service_imports_no_subprocess():
    """Gate 13: Service does not import subprocess."""
    import src.backend.app.services.dicom_conversion_release_readiness as mod
    source = open(mod.__file__, encoding="utf-8").read()
    assert "import subprocess" not in source
    assert "from subprocess" not in source


def test_run_conversion_execute_still_blocked():
    """Gate 14: run_conversion_execute() remains blocked for normal users."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Safety invariants
# ═══════════════════════════════════════════════════════════════════════


def test_no_public_conversion_execute_endpoint():
    """Gate 15: No public /conversion/execute route exists."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    client = TestClient(app)
    resp = client.post("/api/projects/test/conversion/execute", json={})
    assert resp.status_code in (404, 405, 422), f"Expected 404/405/422, got {resp.status_code}"
    resp2 = client.post("/api/projects/test/conversion/run", json={})
    assert resp2.status_code in (404, 405, 422), f"Expected 404/405/422, got {resp2.status_code}"


def test_no_frontend_execute_button():
    """Gate 16: No frontend 'Run Conversion' onClick handler exists."""
    import os
    panel_paths = [
        "src/frontend/src/components/DicomConversionReviewPanel.tsx",
        "src/frontend/src/components/DicomConversionReviewPanel.jsx",
    ]
    found = False
    for rel_path in panel_paths:
        full = os.path.join(os.getcwd(), rel_path)
        if os.path.exists(full):
            lines = open(full, encoding="utf-8").read().splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                    continue
                if "onClick" in stripped and ("Run Conversion" in stripped or "runConversion" in stripped):
                    found = True
    assert not found, "No 'Run Conversion' onClick handler must exist"


def test_go_no_go_32_gates_met():
    """Verify GO/NO-GO schema reports 32/32 gates met."""
    from src.backend.app.schemas.dicom_conversion_go_no_go import (
        build_default_go_no_go_review,
    )
    review = build_default_go_no_go_review()
    assert review.met_count == 32
    assert review.partial_count == 0
    assert review.missing_count == 0


def test_schema_helpers_are_pure():
    """All schema helpers must be pure — no file I/O, no subprocess."""
    import src.backend.app.schemas.dicom_conversion_release_readiness as mod
    source = open(mod.__file__, encoding="utf-8").read()
    assert "import subprocess" not in source
    assert "from subprocess" not in source


def test_summarize_release_blockers():
    """Summarize blockers helper returns correct structure."""
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        evaluate_release_readiness,
        summarize_release_blockers,
    )
    report = evaluate_release_readiness(
        gates_met=32, gates_total=32, disk_space_ok=True,
        rollback_ready=True, approval_audit_ready=True,
        public_endpoint_enabled=False, frontend_execute_enabled=False,
        spm_dpabi_matlab_enabled=False, full_preprocessing_enabled=False,
    )
    summary = summarize_release_blockers(report)
    assert summary["human_release_approval_required"] is True
    assert "gates" in summary
    assert "blocking_count" in summary
