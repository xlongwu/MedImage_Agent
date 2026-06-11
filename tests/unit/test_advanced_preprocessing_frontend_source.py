"""Frontend source tests for Phase 5O-UIClosure — advanced preprocessing panel."""
from __future__ import annotations
import os, pytest

def _read_api():
    path = os.path.join(os.getcwd(), "src/frontend/src/api.ts")
    if not os.path.exists(path): pytest.skip("api.ts not found")
    return open(path, encoding="utf-8").read()

def _read_advanced_panel():
    path = os.path.join(os.getcwd(), "src/frontend/src/components/AdvancedPreprocessingPipelinePanel.tsx")
    if not os.path.exists(path): pytest.skip("AdvancedPreprocessingPipelinePanel not found")
    return open(path, encoding="utf-8").read()

def _read_review_panel():
    path = os.path.join(os.getcwd(), "src/frontend/src/components/DicomConversionReviewPanel.tsx")
    if not os.path.exists(path): pytest.skip("Review panel not found")
    return open(path, encoding="utf-8").read()

# ═══════════════════════════════════════════════════════════════════════
# Panel existence
# ═══════════════════════════════════════════════════════════════════════

def test_advanced_panel_exists():
    content = _read_advanced_panel()
    assert "AdvancedPreprocessingPipelinePanel" in content, "Panel must export default component"

def test_mounted_in_review_panel():
    content = _read_review_panel()
    assert "AdvancedPreprocessingPipelinePanel" in content, "Panel must be mounted in review panel"

# ═══════════════════════════════════════════════════════════════════════
# API wrappers
# ═══════════════════════════════════════════════════════════════════════

def test_validation_api_wrapper_exists():
    content = _read_api()
    assert "getPreprocessingPipelineValidation" in content, "Validation API wrapper must exist"

def test_report_api_wrapper_exists():
    content = _read_api()
    assert "getPreprocessingPipelineReport" in content, "Report API wrapper must exist"

# ═══════════════════════════════════════════════════════════════════════
# UI text
# ═══════════════════════════════════════════════════════════════════════

def test_check_pipeline_validation_button_exists():
    content = _read_advanced_panel()
    assert "Check pipeline validation" in content, "Validation button text must exist"

def test_export_report_button_exists():
    content = _read_advanced_panel()
    assert "Export preprocessing pipeline report" in content, "Report export button must exist"

def test_stage_names_in_panel():
    content = _read_advanced_panel()
    stages = ["Slice Timing", "Coregistration", "Smoothing", "Nuisance Regression",
              "Temporal Filtering", "ALFF/ReHo", "Functional Connectivity"]
    for s in stages:
        assert s in content, f"Stage '{s}' must be referenced in panel"

def test_safety_copy_exists():
    content = _read_advanced_panel()
    assert "rawdata" in content.lower(), "Rawdata safety copy must exist"
    assert "no preprocessing is executed" in content.lower() or "metadata-only" in content.lower(), "No execution statement must exist"

# ═══════════════════════════════════════════════════════════════════════
# Forbidden text
# ═══════════════════════════════════════════════════════════════════════

def test_no_run_full_preprocessing():
    content = _read_advanced_panel()
    assert "Run Full Preprocessing" not in content, "No Run Full Preprocessing"

def test_no_run_dpabi():
    content = _read_advanced_panel()
    assert "Run DPABI" not in content, "No Run DPABI"

def test_no_run_group_statistics():
    for src in [_read_advanced_panel(), _read_api()]:
        assert "Run Group Statistics" not in src, "No Run Group Statistics"

def test_no_run_classification():
    for src in [_read_advanced_panel(), _read_api()]:
        assert "Run Classification" not in src, "No Run Classification"

def test_no_clinical_diagnosis():
    content = _read_advanced_panel()
    assert "Clinical Diagnosis" not in content, "No Clinical Diagnosis"
    assert "clinical diagnosis" not in content.lower(), "No clinical diagnosis"

def test_no_shell_true():
    content = _read_advanced_panel()
    assert "shell=True" not in content, "No shell=True"

def test_no_auto_execution():
    """Verify no useEffect/auto-call triggers execution."""
    content = _read_advanced_panel()
    assert "useEffect" not in content, "No auto-execution on mount (useEffect)"
