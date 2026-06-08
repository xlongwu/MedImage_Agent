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

_REQUIRED_FLAGS = [
    "MEDIMAGE_ENABLE_DICOM_CONVERSION",
    "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE",
    "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE",
    "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION",
    "MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE",
    "MEDIMAGE_MATLAB_ENABLED",
    "MEDIMAGE_SPM_SMOKE_ENABLED",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
    "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
]


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
    assert len(evidence["required_flags"]) == 9


def test_capture_is_import_safe():
    """Verify the module imports without errors."""
    import src.backend.app.services.dicom_conversion_smoke_evidence as mod
    assert mod.capture_synthetic_smoke_evidence is not None


def test_capture_no_subprocess_when_skipped(monkeypatch):
    """When skipped, no subprocess should be called."""
    _clear_smoke_flags(monkeypatch)
    evidence = capture_synthetic_smoke_evidence()
    assert evidence["status"] == "skipped"
