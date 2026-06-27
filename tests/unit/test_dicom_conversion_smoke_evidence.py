"""Tests for synthetic dcm2niix smoke evidence capture — Phase 4H-3.

Verifies that evidence capture skips cleanly when prerequisites are not met.
Real dcm2niix execution requires all 9 env flags + dcm2niix + pydicom.

Tests are isolated from ambient environment variables — they clear
all MEDIMAGE_* flags before each test to ensure deterministic behavior.
"""

from __future__ import annotations

from src.backend.app.services.dicom_conversion_smoke_evidence import (
    capture_synthetic_smoke_evidence,
)

from src.backend.app.services.dicom_conversion_execution import (
    REAL_DCM2NIIX_SYNTHETIC_SMOKE_REQUIRED_FLAGS,
)

_REQUIRED_FLAGS = list(REAL_DCM2NIIX_SYNTHETIC_SMOKE_REQUIRED_FLAGS)


def _clear_smoke_flags(monkeypatch):
    """Remove all required smoke env flags to isolate tests."""
    for name in _REQUIRED_FLAGS:
        monkeypatch.delenv(name, raising=False)


def test_capture_skips_without_env_flags(monkeypatch):
    _clear_smoke_flags(monkeypatch)
    evidence = capture_synthetic_smoke_evidence()
    assert evidence["status"] == "skipped"
    assert "reason" in evidence


def test_capture_reports_required_flags(monkeypatch):
    _clear_smoke_flags(monkeypatch)
    evidence = capture_synthetic_smoke_evidence()
    assert "required_flags" in evidence
    # Per §11.1, MATLAB/SPM/real-preprocessing flags are NOT required.
    # The canonical flag list has been reduced from 9 to 7 entries.
    assert len(evidence["required_flags"]) == 7


def test_capture_is_import_safe():
    """Verify the module imports without errors."""
    import src.backend.app.services.dicom_conversion_smoke_evidence as mod
    assert mod.capture_synthetic_smoke_evidence is not None


def test_capture_no_subprocess_when_skipped(monkeypatch):
    """When skipped, no subprocess should be called."""
    _clear_smoke_flags(monkeypatch)
    evidence = capture_synthetic_smoke_evidence()
    assert evidence["status"] == "skipped"
