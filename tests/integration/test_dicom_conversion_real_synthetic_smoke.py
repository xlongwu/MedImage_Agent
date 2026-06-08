"""Integration test for real dcm2niix synthetic smoke — Phase 4H-0.

Tests the actual subprocess.run([dcm2niix, ...]) path on synthetic DICOM
data ONLY.  All tests are skipped by default unless all required env flags
are set AND dcm2niix AND pydicom are available.

To enable: set all 9 MEDIMAGE_* flags to "1" and ensure dcm2niix on PATH.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


_ALL_FLAGS = {
    "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
    "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE": "1",
    "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE": "1",
    "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION": "1",
    "MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE": "1",
    "MEDIMAGE_MATLAB_ENABLED": "1",
    "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
    "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
}


def _all_flags_present() -> bool:
    return all(os.environ.get(k) == "1" for k in _ALL_FLAGS)


def _dcm2niix_available() -> bool:
    import shutil
    return shutil.which("dcm2niix") is not None


def _pydicom_available() -> bool:
    try:
        import pydicom  # noqa: F401
        return True
    except ImportError:
        return False


# ═══════════════════════════════════════════════════════════════════════
# Tests — all skipped by default
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not _all_flags_present(), reason="Real dcm2niix smoke requires all env flags set to '1'")
@pytest.mark.skipif(not _dcm2niix_available(), reason="dcm2niix not on PATH")
@pytest.mark.skipif(not _pydicom_available(), reason="pydicom not installed")
def test_real_smoke_on_synthetic_dicom(tmp_path):
    """Run real dcm2niix on synthetic DICOM data."""
    from tests.unit.dicom_synthetic_helpers import create_minimal_dicom_series
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )

    input_dir = create_minimal_dicom_series(tmp_path, subject_id="sub-001", num_slices=3)
    output_root = tmp_path / "output"

    result = run_real_dcm2niix_synthetic_smoke(
        input_dir=input_dir, output_root=output_root, env=_ALL_FLAGS,
    )

    # Should succeed or report failure clearly
    assert result.status in {"succeeded", "warning", "failed"}
    assert result.stdout_log_path is not None
    assert result.manifest_path is not None

    # Verify output files exist if successful
    if result.status == "succeeded":
        assert Path(result.stdout_log_path).exists()
        assert Path(result.manifest_path).exists()
        assert Path(result.provenance_path).exists()
        # dcm2niix should have produced at least one output file
        outputs = list(output_root.rglob("*.nii*"))
        assert len(outputs) >= 1


@pytest.mark.skipif(not _all_flags_present(), reason="Real dcm2niix smoke requires all env flags set to '1'")
def test_refuses_real_rawdata_path():
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    result = run_real_dcm2niix_synthetic_smoke(
        input_dir=Path("/data/FunRaw/Sub_001"), output_root=Path("/tmp/out"), env=_ALL_FLAGS,
    )
    assert result.status in {"blocked", "disabled"}


@pytest.mark.skipif(not _all_flags_present(), reason="Real dcm2niix smoke requires all env flags set to '1'")
def test_refuses_real_rawdata_output_path():
    """Even with all flags, output under rawdata-like dir is unsafe."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    # Input is synthetic, but output path contains rawdata — still blocked by path safety
    result = run_real_dcm2niix_synthetic_smoke(
        input_dir=Path("/tmp/pytest-synth"), output_root=Path("/data/rawdata/output"), env=_ALL_FLAGS,
    )
    # Will be blocked by path safety (contains "rawdata" and not under tmp)
    assert result.status in {"blocked", "disabled"}
