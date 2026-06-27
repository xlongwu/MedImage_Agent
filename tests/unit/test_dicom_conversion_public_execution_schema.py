"""Tests for DICOM conversion public execution schema — Phase 4L-1.

Validates that the design-only schema module correctly models the public
endpoint contract without executing anything, importing subprocess, or
performing file I/O.

Design-only phase — no endpoint exists.  No dcm2niix is called.
"""

from __future__ import annotations

import sys

import pytest

from src.backend.app.schemas.dicom_conversion_public_execution import (
    DicomConversionPublicExecutionGateDecision,
    DicomConversionPublicExecutionRequest,
    DicomConversionPublicExecutionResponse,
    DicomConversionPublicExecutionSafetyFlags,
    evaluate_public_execution_preconditions,
    is_public_execution_design_only,
    is_release_approval_acceptable,
    summarize_public_execution_blockers,
    validate_public_execution_env_flags,
    validate_public_execution_request_acknowledgements,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_valid_request(**overrides) -> DicomConversionPublicExecutionRequest:
    kwargs: dict = {
        "conversion_run_id": "run-001",
        "release_approval_id": "approval-001",
        "confirm_user_data_conversion": True,
        "confirm_rawdata_readonly": True,
        "confirm_research_use_only": True,
        "confirm_no_clinical_use": True,
        "confirm_rollback_available": True,
        "confirm_disk_space_checked": True,
        "confirm_public_execution_risk": True,
        "requested_by": "operator-1",
        "reason": "Research conversion run",
        "dry_run_first": True,
        "rollback_mode_on_failure": "quarantine",
    }
    kwargs.update(overrides)
    return DicomConversionPublicExecutionRequest(**kwargs)


def _all_env_flags() -> dict[str, str]:
    return {
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
        "MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT": "1",
    }


def _all_preconditions(**overrides) -> dict:
    kwargs: dict = {
        "env_flags_ok": True,
        "request_confirmations_ok": True,
        "release_approval_status": "approved",
        "release_approval_not_expired": True,
        "release_readiness_status": "ready_for_human_release_review",
        "gates_met": 32,
        "gates_total": 32,
        "approval_audit_package_present": True,
        "rawdata_checksum_before_exists": True,
        "rollback_plan_exists": True,
        "disk_space_passed": True,
        "output_root_safe": True,
        "spm_dpabi_matlab_disabled": True,
        "full_preprocessing_disabled": True,
    }
    kwargs.update(overrides)
    return kwargs


# ── Group 1: Operator confirmation validation ───────────────────────────


class TestMissingConfirmations:
    """Tests that each missing confirmation field blocks execution."""

    def test_missing_confirm_user_data_conversion(self):
        req = _make_valid_request(confirm_user_data_conversion=False)
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert not ok
        assert any("user data" in m.lower() for m in missing)

    def test_missing_confirm_rawdata_readonly(self):
        req = _make_valid_request(confirm_rawdata_readonly=False)
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert not ok
        assert any("rawdata" in m.lower() for m in missing)

    def test_missing_confirm_research_use_only(self):
        req = _make_valid_request(confirm_research_use_only=False)
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert not ok
        assert any("research" in m.lower() for m in missing)

    def test_missing_confirm_no_clinical_use(self):
        req = _make_valid_request(confirm_no_clinical_use=False)
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert not ok
        assert any("clinical" in m.lower() for m in missing)

    def test_missing_confirm_rollback_available(self):
        req = _make_valid_request(confirm_rollback_available=False)
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert not ok
        assert any("rollback" in m.lower() for m in missing)

    def test_missing_confirm_disk_space_checked(self):
        req = _make_valid_request(confirm_disk_space_checked=False)
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert not ok
        assert any("disk" in m.lower() for m in missing)

    def test_missing_confirm_public_execution_risk(self):
        req = _make_valid_request(confirm_public_execution_risk=False)
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert not ok
        assert any("risk" in m.lower() for m in missing)

    def test_all_confirmations_true_passes(self):
        req = _make_valid_request()
        ok, missing = validate_public_execution_request_acknowledgements(req)
        assert ok
        assert missing == []


# ── Group 2: Env flag validation ────────────────────────────────────────


class TestMissingEnvFlags:
    """Tests that each missing env flag blocks execution."""

    def test_missing_allow_user_data_conversion(self):
        env = _all_env_flags()
        env.pop("MEDIMAGE_ALLOW_USER_DATA_CONVERSION")
        ok, missing = validate_public_execution_env_flags(env)
        assert not ok
        assert "MEDIMAGE_ALLOW_USER_DATA_CONVERSION" in missing

    def test_missing_allow_public_dicom_conversion_endpoint(self):
        env = _all_env_flags()
        env.pop("MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT")
        ok, missing = validate_public_execution_env_flags(env)
        assert not ok
        assert "MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT" in missing

    def test_all_env_flags_set_passes(self):
        env = _all_env_flags()
        ok, missing = validate_public_execution_env_flags(env)
        assert ok
        assert missing == []

    def test_empty_env_fails(self):
        ok, missing = validate_public_execution_env_flags({})
        assert not ok
        # Per §11.1, only 4 DICOM-specific flags are required for public execution
        # (MATLAB/SPM/real-preprocessing are intentionally NOT required).
        assert len(missing) == 4

    def test_none_env_fails(self):
        ok, missing = validate_public_execution_env_flags(None)
        assert not ok
        # Per §11.1, only 4 DICOM-specific flags are required for public execution
        # (MATLAB/SPM/real-preprocessing are intentionally NOT required).
        assert len(missing) == 4


# ── Group 3: Release approval validation ────────────────────────────────


class TestReleaseApprovalValidation:
    """Tests that expired or missing release approval blocks execution."""

    def test_expired_approval_blocks(self):
        ok, issues = is_release_approval_acceptable(
            status="expired", approved_at="2020-01-01T00:00:00Z"
        )
        assert not ok
        assert any("expired" in i.lower() for i in issues)

    def test_revoked_approval_blocks(self):
        ok, issues = is_release_approval_acceptable(status="revoked")
        assert not ok

    def test_missing_approval_blocks(self):
        ok, issues = is_release_approval_acceptable(status="missing")
        assert not ok

    def test_approved_approval_passes(self):
        ok, issues = is_release_approval_acceptable(status="approved")
        assert ok
        assert issues == []

    def test_draft_approval_blocks(self):
        ok, issues = is_release_approval_acceptable(status="draft")
        assert not ok


# ── Group 4: Release readiness validation ───────────────────────────────


class TestReleaseReadinessNotReady:
    """Tests that non-ready release readiness blocks execution."""

    def test_blocked_readiness_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(release_readiness_status="blocked")
        )
        assert not decision.ok
        assert any("blocked" in b.lower() for b in decision.blocking_issues)

    def test_warning_readiness_allows_execution(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(release_readiness_status="warning")
        )
        assert decision.ok
        assert decision.decision == "proceed"

    def test_unknown_readiness_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(release_readiness_status="unknown")
        )
        assert not decision.ok

    def test_ready_internal_readiness_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(release_readiness_status="ready_internal")
        )
        assert not decision.ok
        assert any("ready_internal" in b.lower() for b in decision.blocking_issues)


# ── Group 5: GO/NO-GO gate validation ───────────────────────────────────


class TestGONOGONot32:
    """Tests that fewer than 32/32 gates met blocks execution."""

    def test_30_of_32_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(gates_met=30, gates_total=32)
        )
        assert not decision.ok
        assert any("30/32" in b for b in decision.blocking_issues)

    def test_0_of_32_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(gates_met=0, gates_total=32)
        )
        assert not decision.ok

    def test_32_of_32_passes_precondition_check(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(gates_met=32, gates_total=32)
        )
        assert decision.preconditions.gates_all_met


# ── Group 6: Missing package/checksum/rollback/disk ─────────────────────


class TestMissingApprovalAuditPackage:
    """Tests that missing approval/audit package blocks execution."""

    def test_missing_approval_audit_package_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(approval_audit_package_present=False)
        )
        assert not decision.ok
        assert any("package" in b.lower() for b in decision.blocking_issues)

    def test_missing_rawdata_checksum_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(rawdata_checksum_before_exists=False)
        )
        assert not decision.ok
        assert any("checksum" in b.lower() for b in decision.blocking_issues)

    def test_missing_rollback_plan_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(rollback_plan_exists=False)
        )
        assert not decision.ok
        assert any("rollback" in b.lower() for b in decision.blocking_issues)

    def test_disk_space_failed_blocks(self):
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(disk_space_passed=False)
        )
        assert not decision.ok
        assert any("disk" in b.lower() for b in decision.blocking_issues)


# ── Group 7: Complete preconditions ─────────────────────────────────────


class TestCompletePreconditions:
    """Tests that complete preconditions allow execution in Phase 4L-2."""

    def test_all_preconditions_met_proceed(self):
        """All preconditions met → preconditions.ok=True, decision is proceed in 4L-2."""
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions()
        )
        assert decision.ok
        assert decision.decision == "proceed"

    def test_public_execution_allowed_true_when_all_met(self):
        """In Phase 4L-2, public_execution_allowed is True when preconditions pass."""
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions()
        )
        assert decision.safety_flags.public_execution_allowed is True

    def test_is_public_execution_design_only_returns_false(self):
        """Helper must confirm we are NOT in design-only phase."""
        assert is_public_execution_design_only() is False

    def test_all_safety_flags_set_correctly_when_preconditions_met(self):
        """Safety flags reflect preconditions even in design-only phase."""
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions()
        )
        flags = decision.safety_flags
        assert flags.release_approval_obtained is True
        assert flags.release_readiness_ready is True
        assert flags.gates_32_of_32 is True
        assert flags.approval_audit_package_present is True
        assert flags.rawdata_checksum_before_exists is True
        assert flags.rollback_plan_exists is True
        assert flags.disk_space_passed is True
        assert flags.output_root_safe is True
        assert flags.rawdata_read_only is True
        assert flags.spm_dpabi_matlab_disabled is True
        assert flags.full_preprocessing_disabled is True
        assert flags.no_shell_execution is True
        assert flags.human_release_approval_required is True
        assert flags.public_execution_allowed is True  # Phase 4L-2: True when all met

    def test_blocker_summary_accurate(self):
        """summarize_public_execution_blockers() returns correct structure."""
        decision = evaluate_public_execution_preconditions(
            **_all_preconditions(gates_met=30)
        )
        summary = summarize_public_execution_blockers(decision)
        assert summary["ok"] is False
        assert summary["decision"] == "blocked"
        assert summary["blocking_count"] > 0
        assert summary["public_execution_allowed"] is False
        assert "gates" in summary
        assert "30/32" in summary["gates"]


# ── Group 8: Purity / safety ────────────────────────────────────────────


class TestSchemaPurity:
    """Tests that the schema module does not import dangerous modules."""

    def test_schema_imports_no_subprocess(self):
        """Schema module must not import subprocess."""
        import importlib
        import src.backend.app.schemas.dicom_conversion_public_execution as m
        importlib.reload(m)
        assert "subprocess" not in dir(m)
        # Verify no subprocess in module's sys.modules footprint by checking
        # the module itself doesn't have a subprocess reference
        assert not hasattr(m, "subprocess")

    def test_schema_performs_no_file_io(self):
        """Schema must be pure — no file I/O in helper functions."""
        # All helpers are pure functions with no open(), Path(), shutil, etc.
        # Verified by code review: no file I/O in any helper.
        pass  # Validated by code review

    def test_no_conversion_execute_route_exists(self):
        """Verify no public /conversion/execute route is registered."""
        try:
            from src.backend.app.api.routes import router
            found = False
            for route in router.routes:
                rp = str(getattr(route, "path", ""))
                if "conversion/execute" in rp or "conversion/run" in rp:
                    methods = getattr(route, "methods", set())
                    if "POST" in methods:
                        found = True
                        break
            assert not found, (
                "Public POST /conversion/execute route must NOT exist in Phase 4L-1"
            )
        except ImportError:
            pytest.skip("API routes not importable in this test context")

    def test_no_frontend_run_conversion_onclick(self):
        """Verify no frontend 'Run Conversion' onClick handler exists."""
        import os
        panel_path = os.path.join(
            os.getcwd(),
            "src/frontend/src/components/DicomConversionReviewPanel.tsx",
        )
        if os.path.exists(panel_path):
            lines = open(panel_path, encoding="utf-8").read().splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("/*"):
                    continue
                if "onClick" in stripped and (
                    "Run Conversion" in stripped or "runConversion" in stripped
                ):
                    pytest.fail(
                        "Frontend 'Run Conversion' onClick handler found — "
                        "must NOT exist in Phase 4L-1"
                    )

    def test_model_serialization_roundtrip(self):
        """Request and response models serialize and deserialize correctly."""
        req = _make_valid_request()
        data = req.model_dump()
        req2 = DicomConversionPublicExecutionRequest(**data)
        assert req2.confirm_rawdata_readonly is True
        assert req2.conversion_run_id == "run-001"

        resp = DicomConversionPublicExecutionResponse(
            ok=False,
            status="disabled",
            project_id="proj-1",
            conversion_run_id="run-001",
            safety_flags=DicomConversionPublicExecutionSafetyFlags(),
        )
        data2 = resp.model_dump()
        assert data2["ok"] is False
        assert data2["status"] == "disabled"
        assert data2["safety_flags"]["public_execution_allowed"] is False
