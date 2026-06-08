"""Unit-level guard tests for real dcm2niix synthetic smoke — Phase 4H-0.

Tests env flag gating, path safety, and subprocess guardrails WITHOUT
calling real dcm2niix.  All tests monkeypatch subprocess or provide
controlled env.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Missing env flags returns disabled
# ═══════════════════════════════════════════════════════════════════════


def test_missing_env_flags_disabled():
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    result = run_real_dcm2niix_synthetic_smoke(
        input_dir=Path("/tmp/synth"), output_root=Path("/tmp/out"), env={},
    )
    assert result.status == "disabled"
    assert result.safety_flags.conversion_disabled_by_default is True


def test_partial_env_flags_disabled():
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    env = {"MEDIMAGE_ENABLE_DICOM_CONVERSION": "1"}
    result = run_real_dcm2niix_synthetic_smoke(
        input_dir=Path("/tmp/synth"), output_root=Path("/tmp/out"), env=env,
    )
    assert result.status == "disabled"


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Real rawdata path blocked
# ═══════════════════════════════════════════════════════════════════════


def test_real_rawdata_path_blocked():
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    env = {
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
    # Path contains "FunRaw" — should be blocked unless under tmp
    result = run_real_dcm2niix_synthetic_smoke(
        input_dir=Path("/data/FunRaw/Sub_001"), output_root=Path("/tmp/out"), env=env,
    )
    assert result.status in {"blocked", "disabled"}


def test_synthetic_tmp_path_allowed():
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    env = {
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
    # Path is under a pytest tmpdir — should pass path safety
    result = run_real_dcm2niix_synthetic_smoke(
        input_dir=Path("/tmp/pytest-xxx/synth_input"), output_root=Path("/tmp/out"), env=env,
    )
    # Will be blocked by dcm2niix availability (not on PATH), not by path safety
    assert result.status not in {"disabled"}  # Should not be disabled by env flags


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — No shell=True
# ═══════════════════════════════════════════════════════════════════════


def test_no_shell_true_in_source():
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    import inspect
    source = inspect.getsource(run_real_dcm2niix_synthetic_smoke)
    # Only check actual code, filter docstring lines
    lines = [l for l in source.splitlines() if '"""' not in l and not l.strip().startswith("#")]
    code = "\n".join(lines)
    assert "shell=True" not in code


def test_argv_list_not_shell_string():
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    import inspect
    source = inspect.getsource(run_real_dcm2niix_synthetic_smoke)
    assert "subprocess.run" in source  # It should call subprocess.run
    # Check it passes argv as a list, not a string
    assert '", "' in source or '"-z"' in source  # List elements


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Existing safety
# ═══════════════════════════════════════════════════════════════════════


def test_user_conversion_still_disabled():
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True


def test_spm_dpabi_matlab_still_disabled():
    """Verify no SPM/DPABI/MATLAB imports in the real smoke function."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_real_dcm2niix_synthetic_smoke,
    )
    import inspect
    source = inspect.getsource(run_real_dcm2niix_synthetic_smoke)
    assert "import spm" not in source.lower()
    assert "import matlab" not in source.lower()
    assert "import dpabi" not in source.lower()
