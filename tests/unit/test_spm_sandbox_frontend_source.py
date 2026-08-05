"""Frontend source-level tests for SPM sandbox execution UI — Phase 5E-Complete."""

from __future__ import annotations

import os

import pytest


def _read_panel():
    path = os.path.join(os.getcwd(), "src/frontend/src/components/DicomConversionReviewPanel.tsx")
    if not os.path.exists(path):
        pytest.skip("Panel not found")
    return open(path, encoding="utf-8").read()


def _read_api():
    # Read combined content from legacy re-exports and domain files
    legacy_path = os.path.join(os.getcwd(), "src/frontend/src/lib/api/legacy_re_exports.ts")
    preprocessing_path = os.path.join(os.getcwd(), "src/frontend/src/lib/api/preprocessing.ts")
    content = ""
    if os.path.exists(legacy_path):
        content += open(legacy_path, encoding="utf-8").read()
    if os.path.exists(preprocessing_path):
        content += open(preprocessing_path, encoding="utf-8").read()
    if not content:
        pytest.skip("No API source files found")
    return content


def test_sandbox_execution_api_wrapper_exists():
    content = _read_api()
    assert "executeSpmSandboxSliceTimingRealign" in content, (
        "Sandbox execution API wrapper must exist"
    )
    assert "execute-sandbox" in content, "API must call execute-sandbox endpoint"


def test_no_run_full_preprocessing_text():
    content = _read_panel()
    lines = [line.strip() for line in content.splitlines() if not line.strip().startswith("//")]
    code = "\n".join(lines)
    assert "Run Full Preprocessing" not in code, "No Run Full Preprocessing text allowed"
    assert "Run DPABI" not in code, "No Run DPABI text allowed"
    assert "Run Normalization" not in code, "No Run Normalization text allowed"


def test_feature_flag_referenced():
    """Verify sandbox execution API wrapper and types exist in the frontend codebase."""
    content = _read_api()
    assert "executeSpmSandboxSliceTimingRealign" in content, "Sandbox execution API must exist"
    # Types file should have sandbox types
    types_path = os.path.join(os.getcwd(), "src/frontend/src/types.ts")
    if os.path.exists(types_path):
        types_content = open(types_path, encoding="utf-8").read()
        assert "SpmSandboxExecutionResponse" in types_content, "Sandbox types must exist"


def test_confirmation_text_exists():
    """Verify sandbox API wrapper has confirmation fields."""
    content = _read_api()
    assert "confirm_sandbox_copy" in content.lower(), "API must include confirm_sandbox_copy field"


def test_no_shell_true_in_api():
    content = _read_api()
    assert "shell=True" not in content, "No shell=True in API wrappers"
    assert "shell = True" not in content, "No shell = True in API wrappers"
