"""Integration smoke for SPM sandbox Slice Timing + Realign — Phase 5E-Complete.

Skipped unless all env flags set and MATLAB/SPM available.
Never runs in CI by default.
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.integration
def test_sandbox_smoke_disabled_without_env():
    """Smoke test skipped when env flags missing."""
    required = [
        "MEDIMAGE_MATLAB_ENABLED",
        "MEDIMAGE_SPM_SMOKE_ENABLED",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
        "MEDIMAGE_ALLOW_SANDBOXED_SPM_PREPROCESSING",
    ]
    missing = [f for f in required if os.environ.get(f) != "1"]
    if missing:
        pytest.skip(f"Missing env flags: {missing}")


@pytest.mark.integration
def test_sandbox_smoke_end_to_end(tmp_path):
    """Full sandbox execution smoke — requires MATLAB/SPM and test data.

    Run manually with:
      MEDIMAGE_MATLAB_ENABLED=1 MEDIMAGE_SPM_SMOKE_ENABLED=1 ...
      MEDIMAGE_ALLOW_SANDBOXED_SPM_PREPROCESSING=1
      MEDIMAGE_SANDBOX_SMOKE_TEST_INPUT_DIR=/path/to/converted_bids
      pytest tests/integration/test_spm_sandbox_slice_timing_realign_smoke.py -s
    """
    required = [
        "MEDIMAGE_MATLAB_ENABLED",
        "MEDIMAGE_SPM_SMOKE_ENABLED",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
        "MEDIMAGE_ALLOW_SANDBOXED_SPM_PREPROCESSING",
    ]
    missing = [f for f in required if os.environ.get(f) != "1"]
    if missing:
        pytest.skip(f"Missing env flags: {missing}")

    test_input = os.environ.get("MEDIMAGE_SANDBOX_SMOKE_TEST_INPUT_DIR")
    if not test_input or not __import__("pathlib").Path(test_input).exists():
        pytest.skip("MEDIMAGE_SANDBOX_SMOKE_TEST_INPUT_DIR not set or not found")

    import shutil as _sh

    if not _sh.which("matlab"):
        pytest.skip("MATLAB not on PATH")

    # Run real sandbox execution
    from pathlib import Path

    from src.backend.app.schemas.preprocessing_spm_execution import SpmSandboxExecutionRequest
    from src.backend.app.services.preprocessing_spm_execution import run_sandbox_spm_execution

    # Create dry-run first
    dry_dir = tmp_path / "preprocessing_runs" / "pp-test" / "spm_dry_runs" / "dr-test"
    dry_dir.mkdir(parents=True)
    (dry_dir / "dry_run_manifest.json").write_text('{"status":"dry_run_preview"}')

    req = SpmSandboxExecutionRequest(
        dry_run_id="dr-test",
        preprocessing_input_dir=test_input,
        confirm_sandbox_copy=True,
        confirm_no_rawdata_modification=True,
        confirm_slice_timing_realign_only=True,
        confirm_no_full_preprocessing=True,
        confirm_research_use_only=True,
        timeout_seconds=300,
    )
    result = run_sandbox_spm_execution(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )

    assert result.execution_dir
    exec_dir = Path(result.execution_dir)
    assert exec_dir.exists()
    assert Path(result.stdout_log_path).exists()
    assert Path(result.stderr_log_path).exists()
    # Check outputs under sandbox_output
    sandbox_out = Path(result.sandbox_output_dir)
    assert sandbox_out.exists()

    # Verify no outputs leaked outside execution dir
    for p in exec_dir.parent.rglob("*"):
        if p.is_file() and p.suffix in (".nii", ".gz"):
            assert str(p).startswith(str(exec_dir)), f"Output leaked: {p}"
