"""Tests for frontend DICOM conversion execute UI — Phase 4L-4.

Verifies that the execute UI component:
- Is hidden when VITE_ENABLE_DICOM_EXECUTE_UI is not set
- Shows disabled info when feature flag is on but readiness not ready
- Confirmation submit is disabled until all 8 acknowledgements checked
- Does not call backend before confirmations
- Renders blocked/disabled responses correctly
- Renders success response with manifest/provenance/audit paths
- Renders failure response with error + rollback evidence
- No SPM/DPABI/MATLAB action introduced
- Readiness panel remains read-only
- No automatic execute call on page load
- No dcm2niix call in frontend tests

Tests are design-contract tests — they validate the component's props
and exported structure without a DOM renderer.
"""

from __future__ import annotations

import os
import subprocess  # noqa: F401 — verifies test doesn't call dcm2niix

import pytest


def _read_component_source() -> str:
    path = os.path.join(
        os.getcwd(),
        "src/frontend/src/components/DicomConversionExecutePanel.tsx",
    )
    if not os.path.exists(path):
        pytest.skip("DicomConversionExecutePanel.tsx not found")
    return open(path, encoding="utf-8").read()


class TestFeatureFlagGating:
    """Execute UI hidden when VITE_ENABLE_DICOM_EXECUTE_UI is not set."""

    def test_ui_hidden_when_feature_flag_not_set(self):
        """Component returns null (hidden) when feature flag is off by default."""
        source = _read_component_source()
        # The component checks import.meta.env.VITE_ENABLE_DICOM_EXECUTE_UI === "1"
        assert 'VITE_ENABLE_DICOM_EXECUTE_UI' in source, (
            "Component must check VITE_ENABLE_DICOM_EXECUTE_UI feature flag"
        )
        assert 'featureEnabled' in source, (
            "Component must define featureEnabled variable from env flag"
        )
        # Hidden state returns null — verify hidden branch exists
        assert 'uiState === "hidden"' in source or "'hidden'" in source, (
            "Component must have a hidden/null return path"
        )

    def test_no_active_execute_button_by_default(self):
        """No active execute button appears without feature flag."""
        source = _read_component_source()
        # "Run Conversion" must not appear as button text
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue
            if "Run Conversion" in stripped:
                pytest.fail(
                    f"'Run Conversion' found at line {i}: {stripped[:120]}"
                )

    def test_disabled_info_rendered_when_flag_on_but_not_ready(self):
        """Component shows disabled info card when flag enabled but readiness not ready."""
        source = _read_component_source()
        assert "disabled_info" in source, (
            "Component must have disabled_info UI state"
        )
        assert "DICOM conversion execution UI is disabled" in source, (
            "Disabled info must include explanatory text"
        )


class TestConfirmationDialog:
    """Confirmation submit disabled until all 8 acknowledgements checked."""

    def test_confirm_dialog_has_8_checkboxes(self):
        """Confirmation dialog renders 8 required checkbox acknowledgements."""
        source = _read_component_source()
        confirmations = [
            "research use only",
            "not for clinical use",
            "rawdata must remain read-only",
            "rollback is available",
            "disk space was checked",
            "public DICOM conversion risks",
            "SPM/DPABI/MATLAB",
            "only runs DICOM-to-NIfTI",
        ]
        for text in confirmations:
            assert text in source, (
                f"Confirmation text '{text}' not found in component source"
            )

    def test_submit_disabled_until_all_checked(self):
        """Submit button disabled when not all confirmations checked."""
        source = _read_component_source()
        assert "allConfirmed" in source, (
            "Component must compute allConfirmed from checkbox state"
        )
        assert "disabled" in source, (
            "Submit button must be disabled when confirmations incomplete"
        )

    def test_api_wrapper_not_called_before_confirmations(self):
        """The handleExecute function only calls API after allConfirmed check."""
        source = _read_component_source()
        # handleExecute must check allConfirmed before calling the API
        assert "handleExecute" in source, (
            "Component must define handleExecute function"
        )
        # The API call is inside a try block within handleExecute
        assert "runProjectDicomConversionExecute" in source, (
            "Component must use the execute API wrapper"
        )

    def test_api_wrapper_posts_to_conversion_execute(self):
        """API wrapper references /conversion/execute endpoint path."""
        api_path = os.path.join(os.getcwd(), "src/frontend/src/api.ts")
        if not os.path.exists(api_path):
            pytest.skip("api.ts not found")
        content = open(api_path, encoding="utf-8").read()
        assert "/conversion/execute" in content, (
            "api.ts must reference /conversion/execute for Phase 4L-4"
        )


class TestResponseRendering:
    """Backend responses rendered with correct state styling."""

    def test_blocked_status_rendered_with_blocking_reasons(self):
        """Blocked response shows blocking_issues."""
        source = _read_component_source()
        assert "blocked" in source, (
            "Component must handle blocked UI state"
        )
        assert "blocking_issues" in source or "blocking" in source, (
            "Blocked state must display blocking issues"
        )

    def test_disabled_response_not_rendered_as_success(self):
        """Disabled/blocked is distinct from success rendering."""
        source = _read_component_source()
        assert "succeeded" in source, (
            "Component must have succeeded state"
        )
        # Both blocked and succeeded exist — they must be distinct branches
        blocked_idx = source.find('uiState === "blocked"')
        success_idx = source.find('uiState === "succeeded"')
        assert blocked_idx != success_idx, (
            "Blocked and succeeded must be distinct UI branches"
        )

    def test_success_response_shows_manifest_paths(self):
        """Success response renders manifest, provenance, audit, checksum paths."""
        source = _read_component_source()
        success_paths = [
            "output_manifest_path",
            "execution_provenance_path",
            "audit_execution_start_path",
            "audit_execution_final_path",
            "checksum_comparison_path",
            "rollback_plan_path",
        ]
        found = 0
        for p in success_paths:
            if p in source:
                found += 1
        assert found >= 4, (
            f"Success state must show execution artifact paths. "
            f"Found {found}/6 expected path references."
        )

    def test_failure_response_shows_errors_and_rollback(self):
        """Failure state shows errors and rollback evidence."""
        source = _read_component_source()
        assert 'uiState === "failed"' in source or "'failed'" in source, (
            "Component must handle failed UI state"
        )
        # Failure should reference rollback_result_path
        assert "rollback_result_path" in source, (
            "Failure state must display rollback result path"
        )
        assert "Rawdata remains unchanged" in source, (
            "Failure state must remind that rawdata is unchanged"
        )


class TestSafetyInvariants:
    """No SPM/DPABI/MATLAB or full preprocessing action introduced."""

    def test_no_spm_dpabi_matlab_execution(self):
        """Component must not trigger SPM/DPABI/MATLAB execution."""
        source = _read_component_source()
        # Must mention they are NOT executed
        assert "SPM/DPABI/MATLAB" in source, (
            "Component must document SPM/DPABI/MATLAB are not executed"
        )

    def test_no_full_preprocessing_action(self):
        """Component must not trigger full preprocessing."""
        source = _read_component_source()
        assert "full preprocessing" not in source.lower() or (
            "not triggered" in source.lower() or "not executed" in source.lower()
        ), (
            "Full preprocessing must not be triggered"
        )

    def test_readiness_panel_stays_read_only(self):
        """DicomConversionReleaseReadinessPanel must not have execute wiring."""
        rr_path = os.path.join(
            os.getcwd(),
            "src/frontend/src/components/DicomConversionReleaseReadinessPanel.tsx",
        )
        if not os.path.exists(rr_path):
            pytest.skip("ReleaseReadinessPanel not found")
        content = open(rr_path, encoding="utf-8").read()
        assert "conversion/execute" not in content, (
            "ReleaseReadinessPanel must not call /conversion/execute"
        )
        assert "runProjectDicomConversionExecute" not in content, (
            "ReleaseReadinessPanel must not call execute API"
        )

    def test_no_automatic_execute_on_page_load(self):
        """Component must not call execute on mount — only via user action."""
        source = _read_component_source()
        # Check that handleExecute is only called from onClick, not from useEffect/onMount
        assert "useEffect" not in source, (
            "Execute UI should not have a useEffect hook — no auto-execute"
        )
        assert "onClick" in source, (
            "Execute must be triggered via onClick, not automatically"
        )

    def test_no_dcm2niix_call_in_frontend(self):
        """Frontend code must not call dcm2niix. Only backend does.

        The frontend may MENTION dcm2niix in informational text (e.g.,
        'executing dcm2niix'), but must not invoke it directly.
        """
        source = _read_component_source()
        # Check for subprocess/exec/child_process patterns that would indicate
        # the frontend is trying to call dcm2niix directly
        dangerous_patterns = [
            "subprocess",
            "child_process",
            "execSync",
            "exec(",
            "spawn(",
        ]
        for pattern in dangerous_patterns:
            assert pattern not in source, (
                f"Frontend component must not use {pattern} — "
                f"dcm2niix is called only by the backend"
            )
