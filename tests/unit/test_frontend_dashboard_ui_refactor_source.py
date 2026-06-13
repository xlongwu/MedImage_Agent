from __future__ import annotations

import os


ROOT = os.getcwd()


def _read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def test_apple_style_dashboard_structure_exists():
    app = _read("src/frontend/src/App.tsx")
    chrome = _read("src/frontend/src/features/dashboard/DashboardChrome.tsx")
    styles = _read("src/frontend/src/styles.css")
    # Components in App.tsx (workspace-level and lazy-loaded panels)
    app_components = [
        "DataConversionWorkspace",
        "PreprocessingWorkspace",
        "QCReportsWorkspace",
        "SecondaryToolsDrawer",
        "CompactTaskLog",
    ]
    # Components in DashboardChrome.tsx (sidebar and hero components)
    chrome_components = [
        "ProjectHeroPanel",
        "ProjectList",
        "RecommendedNextStepCard",
        "ReadinessStatusStrip",
        "WorkflowTabs",
        "ProjectInventorySummary",
    ]
    for component in app_components:
        assert component in app
    for component in chrome_components:
        assert component in chrome
    assert "Recommended Next Step" in (app + chrome)
    assert "readiness-status-strip" in styles
    assert "workflow-tabs" in styles
    assert "workflow-workspace" in styles


def test_advanced_preprocessing_placeholder_text_exists():
    panel = _read("src/frontend/src/components/AdvancedPreprocessingPipelinePanel.tsx")
    assert "Preprocessing validation" in panel
    assert "Create a preprocessing run after conversion or BIDS registration to inspect the full pipeline." in panel


def test_raw_dicom_and_bids_expected_wording_exists():
    app = _read("src/frontend/src/App.tsx")
    data_readiness = _read("src/frontend/src/components/DataReadinessPanel.tsx")
    bids = _read("src/frontend/src/components/BidsValidationPanel.tsx")
    nifti = _read("src/frontend/src/components/NiftiQcSnapshotPanel.tsx")
    assert "Raw DICOM candidates" in app
    assert "Raw DICOM candidates" in data_readiness
    assert "Converted subjects" in app
    assert "BIDS validation is expected to be incomplete before DICOM-to-NIfTI conversion." in bids
    assert "NIfTI QC is not applicable until DICOM data is converted." in nifti


def test_next_actions_cleanup_helper_exists():
    helper = _read("src/frontend/src/components/dashboardUi.tsx")
    assert "cleanupNextActions" in helper
    assert "normalizeActionText" in helper
    assert "rawDicomPriority" in helper


def test_default_dashboard_does_not_render_planning_tools_as_full_cards():
    app = _read("src/frontend/src/App.tsx")
    start = app.index('<main className="workflow-main">')
    end = app.index("<SecondaryToolsDrawer", start)
    default_main = app[start:end]
    assert "DashboardGroup" not in default_main
    assert "SpmRealignDryRunPanel" not in default_main
    assert "SpmRealignWrapperSkeletonPanel" not in default_main
    assert "EnvironmentHealthPanel" not in default_main


def test_advanced_preprocessing_mounts_once_and_not_in_review_panel():
    app = _read("src/frontend/src/App.tsx")
    review = _read("src/frontend/src/components/DicomConversionReviewPanel.tsx")
    assert app.count("<AdvancedPreprocessingPipelinePanel") == 1
    assert "AdvancedPreprocessingPipelinePanel" not in review


def test_no_forbidden_execution_or_classification_text():
    checked_paths = [
        "src/frontend/src/App.tsx",
        "src/frontend/src/components/AdvancedPreprocessingPipelinePanel.tsx",
        "src/frontend/src/components/dashboardUi.tsx",
        "src/frontend/src/lib/api/legacy.ts",
    ]
    forbidden = [
        "Run Full Preprocessing",
        "Run DPABI",
        "Run Group Statistics",
        "Run Classification",
        "Train Classifier",
        "Clinical Diagnosis",
    ]
    for path in checked_paths:
        content = _read(path)
        for text in forbidden:
            assert text not in content, f"{text!r} found in {path}"


def test_api_paths_remain_present():
    paths_to_check = [
        "src/frontend/src/lib/api/dicom.ts",
        "src/frontend/src/lib/api/preprocessing.ts",
        "src/frontend/src/lib/api/legacy_re_exports.ts",
    ]
    combined = ""
    for p in paths_to_check:
        combined += _read(p)
    expected_paths = [
        "/api/projects/${encodeURIComponent(projectId)}/data-readiness",
        "/api/projects/${encodeURIComponent(projectId)}/bids-validation",
        "/api/projects/${encodeURIComponent(projectId)}/conversion/dry-run",
        "/api/projects/${encodeURIComponent(projectId)}/conversion/preflight",
    ]
    for path in expected_paths:
        assert path in combined, f"{path} not found in API source files"


def test_no_advanced_panel_auto_execution():
    panel = _read("src/frontend/src/components/AdvancedPreprocessingPipelinePanel.tsx")
    assert "useEffect" not in panel
    assert "handleValidation();" not in panel
    assert "handleReport();" not in panel
