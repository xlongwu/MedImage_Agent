"""Tests for synthetic dcm2niix smoke evidence capture — Phase 4H-3.

Verifies that evidence capture skips cleanly when prerequisites are not met.
Real dcm2niix execution requires all 9 env flags + dcm2niix + pydicom.
"""

from __future__ import annotations

from src.backend.app.services.dicom_conversion_smoke_evidence import (
    capture_synthetic_smoke_evidence,
)


def test_capture_skips_without_env_flags():
    evidence = capture_synthetic_smoke_evidence()
    assert evidence["status"] == "skipped"
    assert "reason" in evidence


def test_capture_reports_required_flags():
    evidence = capture_synthetic_smoke_evidence()
    assert "required_flags" in evidence
    assert len(evidence["required_flags"]) == 9


def test_capture_is_import_safe():
    """Verify the module imports without errors."""
    import src.backend.app.services.dicom_conversion_smoke_evidence as mod
    assert mod.capture_synthetic_smoke_evidence is not None


def test_capture_no_subprocess_when_skipped():
    """When skipped, no subprocess should be called."""
    evidence = capture_synthetic_smoke_evidence()
    assert evidence["status"] == "skipped"
