"""Unit guard tests for internal-only user-data conversion prototype — Phase 4I-0.

Tests env flag gating, approval package requirements, path safety, and
subprocess guardrails WITHOUT calling real dcm2niix on user data.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Missing env flags
# ═══════════════════════════════════════════════════════════════════════


def test_missing_internal_flag_returns_blocked():
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test",
        "conv-test",
        env={},
    )
    assert result.status == "disabled"
    assert result.safety_flags.conversion_disabled_by_default is True


def test_native_internal_conversion_uses_only_dicom_specific_flags():
    from src.backend.app.services.dicom_conversion_execution import (
        _is_internal_conversion_enabled,
    )

    minimal = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
    assert _is_internal_conversion_enabled(minimal) == (True, [])
    for flag in minimal:
        candidate = dict(minimal)
        candidate.pop(flag)
        enabled, missing = _is_internal_conversion_enabled(candidate)
        assert enabled is False
        assert missing == [flag]


def test_missing_flags_no_subprocess(monkeypatch):
    """Ensure no subprocess when flags are missing."""
    import subprocess as sp

    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    called = []

    def fake_run(*args, **kwargs):
        called.append(args)
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(sp, "run", fake_run)
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test",
        "conv-test",
        env={},
    )
    assert result.status == "disabled"
    assert len(called) == 0


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Missing approval package
# ═══════════════════════════════════════════════════════════════════════


def test_missing_package_blocks(tmp_path):
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    env = _all_internal_flags()
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test",
        "nonexistent",
        env=env,
        project_dir=str(tmp_path),
    )
    assert result.status == "blocked"


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Output root safety
# ═══════════════════════════════════════════════════════════════════════


def test_output_root_under_rawdata_blocks(tmp_path):
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    rawdata = tmp_path / "rawdata"
    rawdata.mkdir()
    run_dir = rawdata / "conversion_runs" / "conv-test"
    run_dir.mkdir(parents=True)

    env = _all_internal_flags()
    result = run_internal_user_dicom_conversion_from_persisted_package(
        "test",
        "conv-test",
        env=env,
        project_dir=str(tmp_path),
        rawdata_dir=str(rawdata),
    )
    assert result.status == "blocked"


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Existing safety
# ═══════════════════════════════════════════════════════════════════════


def test_user_conversion_still_disabled():
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )

    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True


def test_no_shell_true_in_internal_function():
    import inspect

    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    source = inspect.getsource(run_internal_user_dicom_conversion_from_persisted_package)
    lines = [line for line in source.splitlines() if '"""' not in line]
    code = "\n".join(lines)
    assert "shell=True" not in code


def test_spm_dpabi_matlab_still_disabled():
    import inspect

    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    source = inspect.getsource(run_internal_user_dicom_conversion_from_persisted_package)
    assert "import spm" not in source.lower()
    assert "import matlab" not in source.lower()
    assert "import dpabi" not in source.lower()


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _all_internal_flags() -> dict[str, str]:
    return {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE": "1",
        "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE": "1",
        "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION": "1",
        "MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE": "1",
        "MEDIMAGE_ALLOW_INTERNAL_USER_DICOM_CONVERSION_PROTOTYPE": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
