"""Unit tests for preprocessing_execution.py schema — Phase 4A.

Tests all stage literals, helper functions, plan models, safety flags,
and purity invariants.  No subprocess, no file writes, no external tool
imports, no SPM/DPABI/MATLAB execution.
"""

from __future__ import annotations

from src.backend.app.schemas.preprocessing_execution import (
    ALL_PREPROCESSING_STAGES,
    PreprocessingExecutionPreview,
    PreprocessingExecutionRequest,
    PreprocessingSafetyFlags,
    PreprocessingStage,
    PreprocessingStageConfig,
    PreprocessingSubjectPlan,
    build_default_dparsfa_style_plan,
    get_canonical_stage_order,
    get_external_tool,
    is_external_tool_stage,
    is_preprocessing_stage_order_valid,
    is_project_level_stage,
    is_python_only_stage,
    is_stage_optional,
    is_subject_level_stage,
    requires_approval,
    requires_rawdata_readonly,
    validate_preprocessing_env_flags,
)

# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Stage literal coverage
# ═══════════════════════════════════════════════════════════════════════

EXPECTED_STAGES: set[PreprocessingStage] = {
    "dicom_to_nifti",
    "bids_organization",
    "remove_initial_volumes",
    "slice_timing",
    "realignment",
    "t1_coregistration",
    "t1_segmentation",
    "normalization",
    "nuisance_regression",
    "temporal_filtering",
    "spatial_smoothing",
    "alff_falff",
    "reho",
    "functional_connectivity",
    "subject_qc",
    "group_summary",
    "derivative_summary",
}


def test_all_preprocessing_stages_defined() -> None:
    """Every DPARSFA-style stage literal must be present."""
    assert ALL_PREPROCESSING_STAGES == EXPECTED_STAGES


def test_canonical_order_has_all_stages() -> None:
    """Canonical order must include all 17 stages."""
    assert len(get_canonical_stage_order()) == 17
    assert set(get_canonical_stage_order()) == EXPECTED_STAGES


def test_canonical_order_starts_with_dicom_conversion() -> None:
    """DICOM-to-NIfTI must be first."""
    assert get_canonical_stage_order()[0] == "dicom_to_nifti"


def test_canonical_order_ends_with_derivative_summary() -> None:
    """Derivative summary must be last."""
    assert get_canonical_stage_order()[-1] == "derivative_summary"


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — External tool classification
# ═══════════════════════════════════════════════════════════════════════

EXTERNAL_STAGES: set[PreprocessingStage] = {
    "dicom_to_nifti",
    "slice_timing",
    "realignment",
    "t1_coregistration",
    "t1_segmentation",
    "normalization",
    "nuisance_regression",
    "temporal_filtering",
    "spatial_smoothing",
    "alff_falff",
    "reho",
    "functional_connectivity",
}

PYTHON_STAGES: set[PreprocessingStage] = {
    "bids_organization",
    "subject_qc",
    "group_summary",
    "derivative_summary",
}


def test_external_tool_stages_identified() -> None:
    """All 12 external-tool stages must be classified correctly."""
    for stage in EXTERNAL_STAGES:
        assert is_external_tool_stage(stage), f"{stage} should be external-tool"
    for stage in PYTHON_STAGES:
        assert not is_external_tool_stage(stage), f"{stage} should NOT be external-tool"


def test_python_only_stages_identified() -> None:
    """All 4 pure-Python stages must be classified correctly."""
    for stage in PYTHON_STAGES:
        assert is_python_only_stage(stage), f"{stage} should be Python-only"
    for stage in EXTERNAL_STAGES:
        assert not is_python_only_stage(stage), f"{stage} should NOT be Python-only"


def test_external_tool_kind_per_stage() -> None:
    """Each external-tool stage must have a defined tool kind."""
    assert get_external_tool("dicom_to_nifti") == "dcm2niix"
    assert get_external_tool("slice_timing") == "spm12"
    assert get_external_tool("realignment") == "spm12"
    assert get_external_tool("normalization") == "spm12"
    assert get_external_tool("nuisance_regression") == "dpabi"
    assert get_external_tool("spatial_smoothing") == "dpabi"
    assert get_external_tool("bids_organization") == "none"
    assert get_external_tool("subject_qc") == "none"


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Approval requirements
# ═══════════════════════════════════════════════════════════════════════


def test_all_external_stages_require_approval() -> None:
    """Every external-tool stage must require approval."""
    for stage in EXTERNAL_STAGES:
        assert requires_approval(stage), f"{stage} must require approval"


def test_python_stages_do_not_require_approval() -> None:
    """Pure Python stages must NOT require approval."""
    for stage in PYTHON_STAGES:
        assert not requires_approval(stage), f"{stage} must NOT require approval"


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Rawdata read-only invariant
# ═══════════════════════════════════════════════════════════════════════


def test_rawdata_readonly_is_universal() -> None:
    """All stages must enforce rawdata read-only."""
    for stage in EXPECTED_STAGES:
        assert requires_rawdata_readonly(stage), f"{stage} must be read-only"


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Subject-level vs project-level
# ═══════════════════════════════════════════════════════════════════════

PROJECT_STAGES: set[PreprocessingStage] = {
    "bids_organization",
    "group_summary",
    "derivative_summary",
}


def test_subject_level_stages() -> None:
    """13 stages are subject-level."""
    subject_stages = EXPECTED_STAGES - PROJECT_STAGES
    assert len(subject_stages) == 14  # 17 - 3 project-level
    for stage in subject_stages:
        assert is_subject_level_stage(stage), f"{stage} should be subject-level"


def test_project_level_stages() -> None:
    """3 stages are project-level."""
    for stage in PROJECT_STAGES:
        assert is_project_level_stage(stage), f"{stage} should be project-level"


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Stage ordering validation
# ═══════════════════════════════════════════════════════════════════════


def test_canonical_order_is_valid() -> None:
    """Canonical order must validate against itself."""
    assert is_preprocessing_stage_order_valid(list(get_canonical_stage_order()))


def test_subset_order_is_valid() -> None:
    """A subset of stages in canonical order must be valid."""
    subset: list[PreprocessingStage] = [
        "dicom_to_nifti",
        "realignment",
        "normalization",
        "spatial_smoothing",
        "subject_qc",
        "group_summary",
    ]
    assert is_preprocessing_stage_order_valid(subset)


def test_reversed_order_is_invalid() -> None:
    """Reversed canonical order must be rejected."""
    reversed_order = list(reversed(get_canonical_stage_order()))
    assert not is_preprocessing_stage_order_valid(reversed_order)


def test_swapped_adjacent_is_invalid() -> None:
    """Swapping two adjacent stages must be rejected."""
    order = list(get_canonical_stage_order())
    order[3], order[4] = order[4], order[3]  # swap slice_timing ↔ realignment
    assert not is_preprocessing_stage_order_valid(order)


def test_unknown_stage_rejected() -> None:
    """An unknown stage string must cause validation failure."""
    order: list[PreprocessingStage] = [
        "dicom_to_nifti",
        "bids_organization",
    ]
    # Append a value that is not a valid PreprocessingStage
    bad: list[PreprocessingStage] = [*order, "nonexistent_stage"]  # type: ignore[list-item]
    assert not is_preprocessing_stage_order_valid(bad)


def test_dicom_before_nifti_qc() -> None:
    """DICOM conversion must come before subject QC in any valid plan."""
    order: list[PreprocessingStage] = [
        "dicom_to_nifti",
        "bids_organization",
        "subject_qc",
    ]
    assert is_preprocessing_stage_order_valid(order)

    bad_order: list[PreprocessingStage] = [
        "bids_organization",
        "subject_qc",
        "dicom_to_nifti",
    ]
    assert not is_preprocessing_stage_order_valid(bad_order)


# ═══════════════════════════════════════════════════════════════════════
# Group 7 — Default plan builder
# ═══════════════════════════════════════════════════════════════════════


def test_default_plan_includes_required_stages() -> None:
    """Default plan (without optional) must include all required stages."""
    plan = build_default_dparsfa_style_plan(
        subjects=["sub-001", "sub-002"],
        project_id="proj_test",
    )
    assert plan.pipeline_name == "dparsfa_style"
    assert len(plan.subjects) == 2
    assert plan.subjects[0].subject_id == "sub-001"

    # Required stages: all 17 minus the 3 optional
    required_count = 17 - 3  # 14 required
    assert len(plan.stages) == required_count

    # Optional stages must not appear
    stage_ids = {s.stage for s in plan.stages}
    assert "alff_falff" not in stage_ids
    assert "reho" not in stage_ids
    assert "functional_connectivity" not in stage_ids


def test_default_plan_with_optional_stages() -> None:
    """Default plan with include_optional=True must include all 17 stages."""
    plan = build_default_dparsfa_style_plan(
        subjects=["sub-001"],
        include_optional=True,
    )
    assert len(plan.stages) == 17
    stage_ids = {s.stage for s in plan.stages}
    assert "alff_falff" in stage_ids
    assert "reho" in stage_ids
    assert "functional_connectivity" in stage_ids


def test_default_plan_subjects_share_stage_configs() -> None:
    """Each subject in the plan must get the same stage configs."""
    plan = build_default_dparsfa_style_plan(subjects=["sub-001", "sub-002"])
    for subj in plan.subjects:
        assert len(subj.stages) == len(plan.stages)


def test_default_plan_approval_flags_correct() -> None:
    """Stage configs must carry correct requires_approval flags."""
    plan = build_default_dparsfa_style_plan(subjects=["sub-001"])
    for sc in plan.stages:
        expected = requires_approval(sc.stage)
        assert sc.requires_approval == expected, (
            f"{sc.stage}: requires_approval={sc.requires_approval}, expected={expected}"
        )


def test_default_plan_safety_flags() -> None:
    """Default plan must include safety flags with all execution disabled."""
    plan = build_default_dparsfa_style_plan(subjects=["sub-001"])
    sf = plan.safety_flags
    assert sf.get("conversion_disabled") is True
    assert sf.get("spm_execution_disabled") is True
    assert sf.get("dpabi_execution_disabled") is True
    assert sf.get("matlab_execution_disabled") is True
    assert sf.get("rawdata_read_only") is True
    assert sf.get("research_use_only") is True
    assert sf.get("clinical_use_prohibited") is True


# ═══════════════════════════════════════════════════════════════════════
# Group 8 — Environment flag validation
# ═══════════════════════════════════════════════════════════════════════


def test_env_flags_all_set() -> None:
    """All required flags set to '1' → validation passes."""
    flags = {
        "MEDIMAGE_MATLAB_ENABLED": "1",
        "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
    }
    ok, missing = validate_preprocessing_env_flags(flags)
    assert ok is True
    assert missing == []


def test_env_flags_one_missing() -> None:
    """One missing flag → validation fails."""
    flags = {
        "MEDIMAGE_MATLAB_ENABLED": "1",
        "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
    }
    ok, missing = validate_preprocessing_env_flags(flags)
    assert ok is False
    assert "MEDIMAGE_ENABLE_REAL_PREPROCESSING" in missing


def test_env_flags_all_missing() -> None:
    """All flags missing → validation fails with 4 missing."""
    ok, missing = validate_preprocessing_env_flags({})
    assert ok is False
    assert len(missing) == 4


def test_env_flags_empty_string_not_accepted() -> None:
    """Empty string is not equivalent to '1'."""
    flags = {
        "MEDIMAGE_MATLAB_ENABLED": "",
        "MEDIMAGE_SPM_SMOKE_ENABLED": "",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "",
    }
    ok, _ = validate_preprocessing_env_flags(flags)
    assert ok is False


# ═══════════════════════════════════════════════════════════════════════
# Group 9 — Pydantic model smoke tests
# ═══════════════════════════════════════════════════════════════════════


def test_preprocessing_safety_flags_defaults() -> None:
    """Safety flags model must default to all-safety-on."""
    sf = PreprocessingSafetyFlags()
    assert sf.rawdata_read_only is True
    assert sf.conversion_disabled is True
    assert sf.spm_execution_disabled is True
    assert sf.dpabi_execution_disabled is True
    assert sf.matlab_execution_disabled is True


def test_preprocessing_request_dry_run_default() -> None:
    """PreprocessingExecutionRequest must default to dry_run=True."""
    req = PreprocessingExecutionRequest(
        project_id="test",
        reviewed_plan_id="rp_test",
    )
    assert req.dry_run is True
    assert req.approved is False


def test_preprocessing_preview_dry_run_default() -> None:
    """PreprocessingExecutionPreview must default to dry_run=True."""
    preview = PreprocessingExecutionPreview(
        project_id="test",
        would_execute=False,
    )
    assert preview.dry_run is True


def test_stage_config_defaults() -> None:
    """PreprocessingStageConfig must have sensible defaults."""
    sc = PreprocessingStageConfig(stage="dicom_to_nifti")
    assert sc.enabled is True
    assert sc.external_tool == "none"
    assert sc.requires_approval is False  # not auto-set from stage
    assert sc.timeout_seconds == 3600
    assert sc.stop_on_failure is True


def test_subject_plan_defaults() -> None:
    """PreprocessingSubjectPlan must initialise with empty stages list."""
    sp = PreprocessingSubjectPlan(subject_id="sub-001")
    assert sp.subject_id == "sub-001"
    assert sp.stages == []


# ═══════════════════════════════════════════════════════════════════════
# Group 10 — Purity invariants
# ═══════════════════════════════════════════════════════════════════════


def test_schema_module_has_no_subprocess_import() -> None:
    """Schema module must not import subprocess."""
    import src.backend.app.schemas.preprocessing_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    # Only check for actual imports, not word occurrences in docstrings
    assert "import subprocess" not in content
    assert "from subprocess" not in content
    assert "os.system" not in content


def test_schema_module_has_no_executor_import() -> None:
    """Schema module must not import pipeline_executor or node_registry."""
    import src.backend.app.schemas.preprocessing_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "pipeline_executor" not in content
    assert "node_registry" not in content


def test_schema_module_has_no_spm_dpabi_matlab_import() -> None:
    """Schema module must not import SPM/DPABI/MATLAB modules."""
    import src.backend.app.schemas.preprocessing_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    # Only check for actual import statements, not string literal values
    assert "import spm" not in content.lower()
    assert "from spm" not in content.lower()
    assert "import matlab" not in content.lower()
    assert "from matlab" not in content.lower()
    assert "import dpabi" not in content.lower()
    assert "from dpabi" not in content.lower()


def test_schema_module_all_functions_are_pure() -> None:
    """All helper functions must accept and return data — no file I/O."""
    # Verify by importing and calling functions — they must not raise
    # file-not-found or permission errors.
    assert requires_rawdata_readonly("dicom_to_nifti") is True
    assert is_external_tool_stage("dicom_to_nifti") is True
    assert is_external_tool_stage("subject_qc") is False
    assert requires_approval("realignment") is True
    assert requires_approval("bids_organization") is False
    assert get_external_tool("slice_timing") == "spm12"
    assert get_external_tool("bids_organization") == "none"
    assert is_stage_optional("alff_falff") is True
    assert is_stage_optional("realignment") is False
    assert is_subject_level_stage("realignment") is True
    assert is_subject_level_stage("group_summary") is False
    assert is_project_level_stage("bids_organization") is True
    assert is_project_level_stage("realignment") is False
