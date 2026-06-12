"""Frontend source tests for Phase 5O-UIClosure — advanced preprocessing panel + dashboard polish."""
from __future__ import annotations
import os, re, pytest

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

def _read_bids_panel():
    path = os.path.join(os.getcwd(), "src/frontend/src/components/BidsValidationPanel.tsx")
    if not os.path.exists(path): pytest.skip("BidsValidationPanel not found")
    return open(path, encoding="utf-8").read()

def _read_app():
    path = os.path.join(os.getcwd(), "src/frontend/src/App.tsx")
    if not os.path.exists(path): pytest.skip("App.tsx not found")
    return open(path, encoding="utf-8").read()

def _read_api_client():
    path = os.path.join(os.getcwd(), "src/frontend/src/lib/api/client.ts")
    if not os.path.exists(path): pytest.skip("lib/api/client.ts not found")
    return open(path, encoding="utf-8").read()

def _read_projects_api():
    path = os.path.join(os.getcwd(), "src/frontend/src/lib/api/projects.ts")
    if not os.path.exists(path): pytest.skip("lib/api/projects.ts not found")
    return open(path, encoding="utf-8").read()

def _read_styles():
    path = os.path.join(os.getcwd(), "src/frontend/src/styles.css")
    if not os.path.exists(path): pytest.skip("styles.css not found")
    return open(path, encoding="utf-8").read()

# ═══════════════════════════════════════════════════════════════════════
# Panel existence
# ═══════════════════════════════════════════════════════════════════════

def test_advanced_panel_exists():
    content = _read_advanced_panel()
    assert "AdvancedPreprocessingPipelinePanel" in content, "Panel must export default component"

def test_mounted_once_in_preprocessing_workspace():
    app = _read_app()
    review = _read_review_panel()
    assert "PreprocessingWorkspace" in app, "Preprocessing workspace must exist"
    assert app.count("<AdvancedPreprocessingPipelinePanel") == 1, "Panel must be mounted exactly once in App composition"
    assert "AdvancedPreprocessingPipelinePanel" not in review, "Review panel must not mount preprocessing validation"

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

def test_preprocessing_empty_state_copy_exists():
    content = _read_advanced_panel()
    assert "Create a preprocessing run after conversion or BIDS registration to inspect the full pipeline." in content

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

# ═══════════════════════════════════════════════════════════════════════
# Phase 5 UX Refactor Tests
# ═══════════════════════════════════════════════════════════════════════

def test_project_state_helper_exists():
    app = _read_app()
    assert "deriveProjectWorkflowState" in app, "deriveProjectWorkflowState helper must exist"

def test_raw_dicom_state_exists():
    app = _read_app()
    assert "raw_dicom" in app, "raw_dicom state must exist"

def test_converted_bids_state_exists():
    app = _read_app()
    assert "converted_bids" in app, "converted_bids state must exist"

def test_default_tab_selection_logic_exists():
    app = _read_app()
    assert "setActiveWorkflow" in app, "Tab selection logic must set workflow state"
    assert "dataState" in app, "Tab selection must inspect dataState"

def test_created_project_is_optimistically_merged_into_sidebar():
    app = _read_app()
    assert "mergeCreatedProjectIntoList" in app, "Created projects must be mergeable into the sidebar list"
    assert "projectsBeforeReload" in app, "Upload flow must retain the pre-reload project list"
    assert "projects.setData(mergeCreatedProjectIntoList(result, listSource))" in app, (
        "Upload flow must show the created project in Recent projects immediately"
    )
    assert re.search(
        r"return\s+\[\s*createdProject,\s*\.\.\.projects\.filter\(\(item\)\s*=>\s*item\.id\s*!==\s*result\.project_id\)",
        app,
        re.S,
    ), "Created project must be placed before existing projects and de-duplicated"

def test_recent_projects_can_be_removed_from_sidebar_without_file_delete():
    app = _read_app()
    projects_api = _read_projects_api()
    client_api = _read_api_client()
    styles = _read_styles()
    assert "deleteProject" in app, "Recent project delete handler must call the project delete API"
    assert "projectDeleteLoadingId" in app, "Recent project delete action must have a loading guard"
    assert "project-delete-button" in app and "project-delete-button" in styles, "Recent project rows need a delete control"
    assert "This will not delete rawdata or project files" in app, "Delete confirmation must preserve rawdata safety boundary"
    assert "Rawdata and project files were not deleted" in app, "Delete success copy must state files are untouched"
    assert "projects.setData(remainingProjects)" in app, "Sidebar must update immediately after deletion"
    assert "deleteJson" in client_api and 'method: "DELETE"' in client_api, "API client must support DELETE"
    assert 'deleteJson<ProjectDeleteResponse>(`/api/projects/${encodeURIComponent(projectId)}`)' in projects_api

def test_upload_uses_unique_project_names_and_no_silent_overwrite():
    app = _read_app()
    upload_block = app[app.index("async function handleUploadData"):app.index("async function handleDeleteProject")]
    assert "uniqueProjectName" in app, "Upload flow must have a project-name de-duplication helper"
    assert "getApiBaseUrl" in app and "setBaseUrl(url)" in app, "Upload flow must use the runtime backend URL"
    assert 'window.prompt("Project name"' not in upload_block, "Upload flow must not depend on a hidden project-name prompt"
    assert "Creating project from selected data directory" in upload_block, "Upload flow must show visible progress after directory selection"
    assert "overwrite: false" in upload_block, "Upload flow must not silently overwrite an existing project"
    assert "overwrite: true" not in upload_block, "Upload flow must not hide duplicate-name uploads by overwriting"
    assert "isProjectNameConflict" in upload_block, "Upload flow must handle duplicate-name conflicts"

def test_converted_project_copy():
    app = _read_app()
    assert "Check preprocessing validation" in app or "Create preprocessing run" in app

def test_raw_dicom_copy():
    app = _read_app()
    assert "Generate conversion dry-run" in app

def test_raw_dicom_preprocessing_placeholder():
    app = _read_app()
    assert "Convert DICOM to BIDS/NIfTI before preprocessing validation" in app

def test_tools_drawer_collapsed_by_default():
    app = _read_app()
    assert "drawerOpen" in app
    assert "useState(false)" in app or "useState<boolean>(false)" in app

def test_recent_activity_collapsed():
    app = _read_app()
    assert "details" in app or "details className=" in app, "Recent activity should use details block or collapse"

def test_no_train_classifier():
    for src in [_read_app(), _read_advanced_panel(), _read_api()]:
        assert "Train Classifier" not in src, "No Train Classifier"
        assert "train_classifier" not in src.lower(), "No train_classifier"

def test_no_backend_api_path_changes():
    api = _read_api()
    assert "/api/projects" in api
    assert "getPreprocessingPipelineValidation" in api
    assert "getPreprocessingPipelineReport" in api

# State consistency polish tests
def test_converted_bids_tab_routing():
    app = _read_app()
    assert '"preprocessing"' in app and '"converted_bids"' in app, "converted_bids must default to preprocessing"

def test_raw_dicom_tab_routing():
    app = _read_app()
    assert '"data"' in app and '"raw_dicom"' in app, "raw_dicom must default to data tab"

def test_converted_bids_data_conversion_not_primary():
    app = _read_app()
    assert "DICOM conversion is not the primary workflow" in app, "converted_bids must display primary workflow info"

def test_raw_dicom_bids_expected_before_conversion():
    bids = _read_bids_panel()
    assert "Expected before conversion" in bids, "raw_dicom must expect conversion"

def test_demo_data_like_raw_dicom_priority_source():
    """DICOM evidence with absent converted evidence must route to raw_dicom."""
    app = _read_app()
    assert "hasRawDicomEvidence" in app, "Classifier must have explicit raw DICOM evidence"
    assert "convertedDataAbsent" in app, "Classifier must check converted evidence absence"
    assert "dicom_file_count" in app and "dicom_series_count" in app, "DICOM count signals must be inspected"
    assert "raw_dicom_candidate_subjects" in app, "Raw DICOM candidate subject signal must be preserved"
    assert re.search(
        r"if\s*\(\s*hasRawDicomEvidence\s*&&\s*convertedDataAbsent\s*\)\s*\{\s*return\s+\"raw_dicom\";",
        app,
        re.S,
    ), "Raw DICOM evidence must take priority when NIfTI/BIDS evidence is absent"

def test_metadata_only_does_not_prove_converted_bids():
    app = _read_app()
    assert "isMetadataOnlySignal" in app, "Metadata-only signals must be detected separately"
    assert re.search(
        r"const\s+hasConvertedSubjectEvidence\s*=\s*!metadataOnly",
        app,
    ), "Metadata-only inventory must not count as converted subject evidence"
    assert "metadataOnlyNiftiInventory" in app, "Metadata-only state should be carried as a display note"

def test_raw_dicom_primary_action_not_preprocessing_validation():
    app = _read_app()
    primary_block = app[app.index("const primary ="):app.index("const explanation =")]
    raw_branch = primary_block.split(': inventory.dataState === "converted_bids"')[0]
    assert "Generate conversion dry-run" in raw_branch, "raw_dicom primary action must be conversion dry-run"
    assert "Check preprocessing validation" not in raw_branch, "raw_dicom primary action must not be preprocessing validation"

def test_nifti_metric_stays_numeric_when_metadata_only():
    app = _read_app()
    bids = _read_bids_panel()
    app_metric = app[app.index('label="NIfTI files"'):app.index('label="NIfTI files"') + 280]
    bids_metric = bids[bids.index('label="NIfTI files"'):bids.index('label="NIfTI files"') + 220]
    assert "Metadata-" not in app_metric and "Metadata-" not in bids_metric
    assert "Metadata-only inventory" not in app
    assert "Metadata-only inventory" not in bids
    assert "NIfTI inventory: metadata only" in app
    assert "NIfTI inventory: metadata only" in bids

def test_real_converted_bids_evidence_still_classifies_converted():
    app = _read_app()
    assert "const hasRealConvertedData" in app
    assert "niftiCount > 0 || hasRealBidsRoots || hasConvertedSubjectEvidence" in app
    assert re.search(
        r"if\s*\(\s*hasRealConvertedData\s*\)\s*\{\s*return\s+\"converted_bids\";",
        app,
        re.S,
    ), "Real NIfTI/BIDS evidence must still route to converted_bids"

def test_empty_project_recommended_action():
    app = _read_app()
    assert "Import dataset" in app or "Import a BIDS/NIfTI dataset" in app, "empty projects must recommend import"

# ═══════════════════════════════════════════════════════════════════════
# Phase 5O Dashboard Polish Tests
# ═══════════════════════════════════════════════════════════════════════

def test_generate_conversion_dry_run_wording():
    """'Generate conversion dry-run' must remain the primary recommended action for raw DICOM."""
    app = _read_app()
    assert "Generate conversion dry-run" in app, "Generate conversion dry-run must be present"

def test_review_conversion_readiness_wording():
    """'Review conversion readiness' must remain as secondary action wording."""
    app = _read_app()
    assert "Review conversion readiness" in app, "Review conversion readiness must be present"

def test_no_run_dicom_to_bids_conversion_unsafe_wording():
    """'Run DICOM-to-BIDS conversion' must not appear as a user-facing action button."""
    app = _read_app()
    review = _read_review_panel()
    # This exact unsafe phrase must not appear as standalone action text
    assert "Run DICOM-to-BIDS conversion" not in app, "Unsafe 'Run DICOM-to-BIDS conversion' must not appear in App.tsx"
    assert "Run DICOM-to-BIDS conversion" not in review, "Unsafe wording must not appear in review panel"

def test_show_technical_details_toggle_exists():
    """'Show technical details' toggle must exist in the review panel and App."""
    review = _read_review_panel()
    app = _read_app()
    assert "Show technical details" in review or "technical details" in review.lower(), \
        "Technical details toggle must exist in review panel"
    assert "Show technical details" in app, "Show technical details must appear in App"

def test_expandable_approval_requirements():
    """Approval requirements must be behind an expandable/collapsible control."""
    review = _read_review_panel()
    # Approval checklist must be inside a CollapsibleDetails or <details>
    assert "APPROVAL_CHECKLIST" in review or "approval" in review.lower(), "Approval checklist must exist"
    # Ensure it is not bare (it should be inside collapsible)
    assert "CollapsibleDetails" in review or "<details" in review, \
        "Approval requirements must be in a collapsible component"

def test_expandable_env_flags():
    """Env flags / missing_env_flags must be behind technical details toggle, not default-visible."""
    review = _read_review_panel()
    assert "missing_env_flags" in review, "Env flags must be referenced"
    assert "showTechDetails" in review, "Env flags must be behind tech details gate"

def test_expandable_mapping_preview():
    """DICOM mapping preview must be behind a collapsible."""
    review = _read_review_panel()
    assert "DICOM mapping preview" in review, "Mapping preview must exist"
    assert "CollapsibleDetails" in review or "<details" in review, \
        "Mapping preview must be in a collapsible component"

def test_sidebar_project_name_truncation():
    """Project names in sidebar must use a truncating CSS class or title attribute."""
    app = _read_app()
    # title attribute for full name on hover
    assert 'title={item.name}' in app, "project-pill must expose full name via title attribute"
    # CSS class for truncation
    assert "project-pill-name" in app, "project-pill-name class must be used for truncation"

def test_sidebar_project_name_css_truncation():
    """CSS must define truncation for project pill names."""
    styles = _read_styles()
    assert "project-pill-name" in styles, "CSS must define project-pill-name truncation"
    assert "text-overflow: ellipsis" in styles, "CSS must use ellipsis truncation"

def test_viewer_height_reduced():
    """Viewer card min-height must be at most 400px (reduced from 430px)."""
    styles = _read_styles()
    # Find the viewer-card block and check its min-height
    import re
    match = re.search(r'\.viewer-card\s*\{[^}]*min-height:\s*(\d+)px', styles)
    assert match is not None, "viewer-card must have a min-height"
    height = int(match.group(1))
    assert height <= 400, f"viewer-card min-height should be ≤400px for compact view, got {height}px"

def test_blocked_conversion_calm_styling():
    """Blocked state must use amber/warning tone, not large red panel."""
    review = _read_review_panel()
    # Must say blocked by safety gates (calmer wording)
    assert "blocked by safety gates" in review, "Must use calmer 'blocked by safety gates' wording"
    # Must NOT use the old full red background style as the primary visible element
    # (the old version had rgba(255, 241, 240, 0.94) as the outer div background)
    # The new version uses amber/warning color scheme
    assert "#925400" in review or "rgba(255, 248, 236" in review, \
        "Blocked state must use amber/warning tone instead of full red"

def test_no_auto_execution_useeffect_in_app():
    """App.tsx must not add auto-execution useEffect calls."""
    app = _read_app()
    # Check that useEffect doesn't call execution endpoints directly
    # (preflight auto-run is OK, but not run/execute endpoints)
    assert "runProjectDicomConversion(" not in app, "No direct conversion execution in App.tsx useEffect"

def test_conversion_blocked_count_visible():
    """Blocked state must show prerequisite count visibly."""
    review = _read_review_panel()
    assert "blocking_issues.length" in review, "Must show blocking issue count"
    assert "prerequisite(s) missing" in review, "Must show 'prerequisite(s) missing' text"

def test_review_persist_requires_preflight_mappings():
    """Review package persistence must not save an empty mapping package."""
    review = _read_review_panel()
    assert "canPersistReview" in review, "Review panel must compute whether mappings are available"
    assert "data.mapping_count > 0" in review, "Persistence must require at least one mapping"
    assert "disabled={persisting || !canPersistReview}" in review, \
        "Persist review package button must be disabled when mappings are absent"
    assert "Run conversion preflight and review at least one mapping before saving." in review, \
        "Empty mapping persistence guard must explain the next step"

def test_review_panel_has_no_mojibake_markers():
    """Visible review text must not contain Windows mojibake markers."""
    review = _read_review_panel()
    for marker in ("璺", "鈿", "鈥", "閳", "路", "\ufffd"):
        assert marker not in review, f"Mojibake marker {marker!r} must not appear in review panel"
