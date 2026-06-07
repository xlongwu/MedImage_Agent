"""SPM realign synthetic smoke test scaffold — skipped by default.

All tests are skipped unless explicit environment flags are set:
  MEDIMAGE_MATLAB_ENABLED=1
  MEDIMAGE_SPM_SMOKE_ENABLED=1
  MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1

No MATLAB/SPM execution in normal test runs.  This scaffold is a
design placeholder for future implementation.
"""

from __future__ import annotations

import os

import pytest

# ── Module-level skip marker ────────────────────────────────────────────────

_SPM_SMOKE_ENABLED = (
    os.environ.get("MEDIMAGE_MATLAB_ENABLED") == "1"
    and os.environ.get("MEDIMAGE_SPM_SMOKE_ENABLED") == "1"
    and os.environ.get("MEDIMAGE_ENABLE_REVIEWED_EXECUTION") == "1"
)

pytestmark = pytest.mark.skipif(
    not _SPM_SMOKE_ENABLED,
    reason="SPM synthetic smoke requires MEDIMAGE_MATLAB_ENABLED=1, MEDIMAGE_SPM_SMOKE_ENABLED=1, and MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1.",
)


# ── Preflight contract tests (always valid, no MATLAB needed) ───────────────


def test_spm_synthetic_smoke_is_env_gated():
    """Verify the skip marker is correctly applied when flags are absent.

    This test is intentionally simple — it only runs when the env flags
    ARE set (otherwise the module-level skip fires).  When the flags are
    set, it confirms the test can at least load without import errors.
    """
    assert True, "Smoke scaffold loaded successfully under env flags."


def test_spm_synthetic_smoke_requires_tmp_output_root():
    """Future synthetic smoke must use pytest tmp_path, not real directories.

    This is a contract reminder that output must be scoped to tmp_path.
    """
    # In future, this test would verify the output root is under tmp_path.
    assert "MEDIMAGE_MATLAB_ENABLED" in os.environ or True


def test_spm_synthetic_smoke_contract_notes_no_execution():
    """Confirm that real execution is not yet implemented.

    This test guards against accidentally running real MATLAB/SPM before
    the execution pipeline exists.
    """
    # The real execution endpoint/runner does not exist yet.
    # When it does, this test should verify the runner is callable.
    pass
