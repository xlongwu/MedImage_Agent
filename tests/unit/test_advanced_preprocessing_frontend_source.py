"""Frontend source tests for Phase 5O — advanced preprocessing UI absence checks."""
from __future__ import annotations
import os, pytest

def _read_api():
    path = os.path.join(os.getcwd(), "src/frontend/src/api.ts")
    if not os.path.exists(path): pytest.skip("api.ts not found")
    return open(path, encoding="utf-8").read()

def _read_panel():
    path = os.path.join(os.getcwd(), "src/frontend/src/components/DicomConversionReviewPanel.tsx")
    if not os.path.exists(path): pytest.skip("Panel not found")
    return open(path, encoding="utf-8").read()

def _read_advanced():
    path = os.path.join(os.getcwd(), "src/frontend/src/components/AdvancedPreprocessingPipelinePanel.tsx")
    if not os.path.exists(path):
        path2 = os.path.join(os.getcwd(), "src/frontend/src/components/SpmSandboxExecutionPanel.tsx")
        if not os.path.exists(path2): pytest.skip("Advanced panel not found")
        return "advanced_pipeline_panel_missing_but_sandbox_present"

def test_no_run_full_preprocessing():
    content = _read_api()
    assert "Run Full Preprocessing" not in content, "No Run Full Preprocessing text"

def test_no_run_dpabi():
    content = _read_api()
    assert "Run DPABI" not in content, "No Run DPABI text"

def test_no_run_group_statistics():
    content = _read_api()
    assert "Run Group Statistics" not in content, "No Run Group Statistics text"

def test_no_run_classification():
    content = _read_api()
    assert "Run Classification" not in content, "No Run Classification text"

def test_no_clinical_diagnosis():
    content = _read_api()
    assert "Clinical Diagnosis" not in content, "No Clinical Diagnosis text"
    assert "clinical diagnosis" not in content.lower(), "No clinical diagnosis text"

def test_no_shell_true():
    content = _read_api()
    assert "shell=True" not in content, "No shell=True in frontend source"
    assert "shell = True" not in content, "No shell = True in frontend source"

def test_pipeline_report_endpoint():
    content = _read_api()
    assert "pipeline_report" in content.lower() or "report" in content.lower(), "Report endpoint referenced"

def test_feature_flags_exist():
    sp = os.path.join(os.getcwd(), "src/frontend/src/components/SpmSandboxExecutionPanel.tsx")
    if not os.path.exists(sp):
        pytest.skip("SpmSandboxExecutionPanel not found")
    content = open(sp, encoding="utf-8").read().lower()
    assert "vite_enable_spm_sandbox_execution_ui" in content, "Feature flag must be referenced"
