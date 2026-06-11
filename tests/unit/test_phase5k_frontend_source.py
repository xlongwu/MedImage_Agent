"""Frontend source tests for Phase 5K — nuisance filtering UI absence checks."""
from __future__ import annotations
import os, pytest

def _read_api():
    path = os.path.join(os.getcwd(), "src/frontend/src/api.ts")
    if not os.path.exists(path): pytest.skip("api.ts not found")
    return open(path, encoding="utf-8").read()

def _read_types():
    path = os.path.join(os.getcwd(), "src/frontend/src/types.ts")
    if not os.path.exists(path): pytest.skip("types.ts not found")
    return open(path, encoding="utf-8").read()

def test_nuisance_api_wrapper_exists():
    content = _read_api()
    assert "executeNuisanceRegressionSandbox" in content, "Nuisance execution API must exist"
    assert "nuisance-regression/execute-sandbox" in content, "API must call nuisance execute endpoint"

def test_filtering_api_wrapper_exists():
    content = _read_api()
    assert "runFilteringDryRun" in content, "Filtering dry-run API must exist"
    assert "temporal-filtering/dry-run" in content, "API must call filtering dry-run endpoint"

def test_nuisance_types_exist():
    content = _read_types()
    assert "NuisanceSandboxExecutionResponse" in content, "Nuisance execution type must exist"
    assert "FilteringDryRunResponse" in content, "Filtering dry-run type must exist"

def test_no_forbidden_buttons_in_api():
    content = _read_api()
    assert "Run Full Preprocessing" not in content, "No Run Full Preprocessing text"
    assert "Run DPABI" not in content, "No Run DPABI text"
    assert "shell=True" not in content, "No shell=True in API wrappers"

def test_no_run_temporal_filtering():
    content = _read_api()
    assert "Run Temporal Filtering" not in content, "No Run Temporal Filtering action"
    assert "Run ALFF" not in content, "No Run ALFF action"
