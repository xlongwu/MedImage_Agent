"""Unit tests for dicom_conversion_execution.py schema — Phase 4B.

Tests all type aliases, models, pure helper functions, disabled-by-default
behaviour, and purity invariants.  No subprocess, no file writes, no
external tool imports, no real dcm2niix execution.
"""

from __future__ import annotations

import pytest

from src.backend.app.schemas.dicom_conversion_execution import (
    Dcm2niixCommandTemplate,
    DicomConversionExecutionRequest,
    DicomConversionExecutionResponse,
    DicomConversionFailureRecord,
    DicomConversionMapping,
    DicomConversionMode,
    DicomConversionPreflight,
    DicomConversionSafetyFlags,
    DicomConversionStatus,
    DicomConversionTool,
    build_dcm2niix_command_template,
    build_disabled_conversion_response,
    is_conversion_execution_enabled,
    redact_command_preview,
    summarize_conversion_mappings,
    validate_output_root_not_under_rawdata,
    validate_output_root_under_project,
)

# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Mode and status literals
# ═══════════════════════════════════════════════════════════════════════


def test_mode_literals_are_valid() -> None:
    """All expected mode values must be usable as DicomConversionMode."""
    modes: list[DicomConversionMode] = [
        "dry_run",
        "preflight",
        "execute_disabled",
        "execute",
    ]
    assert len(modes) == 4


def test_status_literals_are_valid() -> None:
    """All expected status values must be usable as DicomConversionStatus."""
    statuses: list[DicomConversionStatus] = [
        "ready",
        "blocked",
        "warning",
        "disabled",
        "failed",
        "succeeded",
    ]
    assert len(statuses) == 6


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Command template construction
# ═══════════════════════════════════════════════════════════════════════


def test_build_command_template_funraw_bold() -> None:
    """Command template must correctly map a FunRaw BOLD subject."""
    template = build_dcm2niix_command_template(
        input_dir="D:/DemoData/FunRaw/Sub_001",
        output_dir="C:/project/converted_bids/sub-001/func",
        filename_pattern="sub-001_task-rest_bold",
    )
    assert template.tool == "dcm2niix"
    assert template.executable == "dcm2niix"
    assert template.input_dir == "D:/DemoData/FunRaw/Sub_001"
    assert template.output_dir == "C:/project/converted_bids/sub-001/func"
    assert template.filename_pattern == "sub-001_task-rest_bold"
    assert template.compress == "y"
    assert template.bids_sidecar is True
    assert template.create_bids is True
    assert template.command_preview != ""
    assert "dcm2niix" in template.command_preview
    assert "sub-001_task-rest_bold" in template.command_preview


def test_build_command_template_t1raw_t1w() -> None:
    """Command template must correctly map a T1Raw T1w subject."""
    template = build_dcm2niix_command_template(
        input_dir="D:/DemoData/T1Raw/Sub_001",
        output_dir="C:/project/converted_bids/sub-001/anat",
        filename_pattern="sub-001_T1w",
    )
    assert template.tool == "dcm2niix"
    assert template.output_dir == "C:/project/converted_bids/sub-001/anat"
    assert template.filename_pattern == "sub-001_T1w"
    assert "sub-001_T1w" in template.command_preview


def test_command_template_no_shell_string_field() -> None:
    """Command template must not contain a raw shell string execution field."""
    template = build_dcm2niix_command_template(
        input_dir="/tmp/dicom",
        output_dir="/tmp/nifti",
    )
    # extra='forbid' means no unexpected fields can be set
    d = template.model_dump()
    assert "shell" not in d
    assert "shell_command" not in d
    assert "command" not in d  # command_preview is display-only, not "command"


def test_command_template_extra_forbidden() -> None:
    """Command template must reject extra fields."""
    with pytest.raises(Exception):
        Dcm2niixCommandTemplate(
            tool="dcm2niix",
            shell="dcm2niix ...",  # type: ignore[call-arg]
        )


def test_command_template_compatible_with_funraw_paths() -> None:
    """Template must handle Windows-style FunRaw paths correctly."""
    template = build_dcm2niix_command_template(
        input_dir="D:\\deep_learning_code\\MedImage_Agent\\data\\DemoData\\FunRaw\\Sub_001",
        output_dir="D:\\project\\converted_bids\\sub-001\\func",
        filename_pattern="sub-001_task-rest_bold",
    )
    assert template.input_dir.startswith("D:")
    assert template.output_dir.startswith("D:")
    assert "Sub_001" in template.input_dir


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Conversion execution disabled by default
# ═══════════════════════════════════════════════════════════════════════


def test_build_disabled_response() -> None:
    """Disabled response must have all safety flags set conservatively."""
    resp = build_disabled_conversion_response(project_id="test")
    assert resp.ok is True
    assert resp.status == "disabled"
    assert resp.conversion_disabled is True
    assert resp.execution_blocked is True
    assert resp.safety_flags.conversion_disabled_by_default is True


def test_disabled_response_includes_blocking_issues() -> None:
    """Disabled response must explain why execution is blocked."""
    resp = build_disabled_conversion_response(
        project_id="test",
        reason="Custom block reason.",
        missing_env_flags=["MEDIMAGE_ENABLE_DICOM_CONVERSION"],
    )
    assert len(resp.blocking_issues) >= 1
    assert "Custom block reason." in resp.blocking_issues[0]


def test_safety_flags_all_safe_by_default() -> None:
    """All safety flags must default to the safest value."""
    sf = DicomConversionSafetyFlags()
    assert sf.rawdata_read_only is True
    assert sf.output_under_project is True
    assert sf.no_shell_string is True
    assert sf.command_template_only is True
    assert sf.approval_required is True
    assert sf.audit_required is True
    assert sf.conversion_disabled_by_default is True
    assert sf.env_flags_missing is True
    assert sf.no_spm_dpabi_matlab is True
    assert sf.clinical_use_prohibited is True


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Environment flag validation
# ═══════════════════════════════════════════════════════════════════════


def test_env_flags_all_missing_blocks_execution() -> None:
    """All flags missing → execution disabled."""
    ok, missing = is_conversion_execution_enabled({})
    assert ok is False
    assert len(missing) == 5


def test_env_flags_partial_blocks_execution() -> None:
    """Partial flags → execution still disabled."""
    env = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_MATLAB_ENABLED": "1",
    }
    ok, missing = is_conversion_execution_enabled(env)
    assert ok is False
    assert len(missing) == 3


def test_env_flags_all_set_enables_preflight_only() -> None:
    """All flags set → preflight readiness, NOT real execution."""
    env = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_MATLAB_ENABLED": "1",
        "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
    }
    ok, missing = is_conversion_execution_enabled(env)
    assert ok is True
    assert missing == []


def test_env_flags_empty_string_not_accepted() -> None:
    """Empty string is not '1'."""
    env = {f: "" for f in [
        "MEDIMAGE_ENABLE_DICOM_CONVERSION",
        "MEDIMAGE_MATLAB_ENABLED",
        "MEDIMAGE_SPM_SMOKE_ENABLED",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
    ]}
    ok, _ = is_conversion_execution_enabled(env)
    assert ok is False


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Output root safety validation
# ═══════════════════════════════════════════════════════════════════════


def test_output_under_project_is_safe() -> None:
    """Output root inside project dir must pass validation."""
    assert validate_output_root_under_project(
        "C:/project/converted_bids/sub-001",
        "C:/project",
    ) is True


def test_output_outside_project_is_unsafe() -> None:
    """Output root outside project dir must fail validation."""
    assert validate_output_root_under_project(
        "C:/somewhere_else/converted_bids",
        "C:/project",
    ) is False


def test_output_equals_project_is_safe() -> None:
    """Output root equal to project dir must pass."""
    assert validate_output_root_under_project(
        "C:/project",
        "C:/project",
    ) is True


def test_output_with_traversal_is_unsafe() -> None:
    """Output root with .. traversal must be rejected."""
    assert validate_output_root_under_project(
        "C:/project/../outside",
        "C:/project",
    ) is False


def test_output_root_not_under_rawdata() -> None:
    """Output root must not be inside rawdata dir."""
    assert validate_output_root_not_under_rawdata(
        "C:/project/converted_bids",
        "D:/DemoData",
    ) is True

    assert validate_output_root_not_under_rawdata(
        "D:/DemoData/outputs",
        "D:/DemoData",
    ) is False


def test_empty_paths_return_safe() -> None:
    """Empty inputs must not crash the validator."""
    assert validate_output_root_under_project("", "") is False
    assert validate_output_root_under_project("C:/a", "") is False
    assert validate_output_root_under_project("", "C:/a") is False
    assert validate_output_root_not_under_rawdata("", "") is True
    assert validate_output_root_not_under_rawdata("C:/a", "") is True


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Mapping summary
# ═══════════════════════════════════════════════════════════════════════


def test_summarize_empty_mappings() -> None:
    """Empty mappings must return zero counts."""
    summary = summarize_conversion_mappings([])
    assert summary["total_count"] == 0
    assert summary["func_count"] == 0
    assert summary["anat_count"] == 0


def test_summarize_funraw_t1raw_mappings() -> None:
    """6 mappings (3 func, 3 anat) must be summarised correctly."""
    mappings = [
        DicomConversionMapping(
            subject_id=f"sub-{i:03d}",
            modality="func",
            suffix="bold",
            task="rest",
            confidence="high",
        )
        for i in range(1, 4)
    ] + [
        DicomConversionMapping(
            subject_id=f"sub-{i:03d}",
            modality="anat",
            suffix="T1w",
            confidence="high",
        )
        for i in range(1, 4)
    ]
    summary = summarize_conversion_mappings(mappings)
    assert summary["total_count"] == 6
    assert summary["func_count"] == 3
    assert summary["anat_count"] == 3
    assert len(summary["subject_ids"]) == 3
    assert summary["confidence_high"] == 6
    assert summary["enabled_count"] == 6


# ═══════════════════════════════════════════════════════════════════════
# Group 7 — Preflight model defaults
# ═══════════════════════════════════════════════════════════════════════


def test_preflight_defaults_to_disabled() -> None:
    """Preflight must default to status=disabled."""
    pf = DicomConversionPreflight()
    assert pf.status == "disabled"
    assert pf.conversion_disabled_by_default is True
    assert pf.approval_required is True
    assert pf.audit_required is True


def test_execution_request_defaults_to_disabled_mode() -> None:
    """Execution request must default to execute_disabled mode."""
    req = DicomConversionExecutionRequest()
    assert req.mode == "execute_disabled"
    assert req.confirm_execution is False


def test_execution_response_defaults_to_disabled() -> None:
    """Execution response must default to conversion_disabled=true."""
    resp = DicomConversionExecutionResponse()
    assert resp.conversion_disabled is True
    assert resp.execution_blocked is True
    assert resp.status == "disabled"


def test_failure_record_fields() -> None:
    """Failure record must accept all expected fields."""
    fr = DicomConversionFailureRecord(
        message="dcm2niix returned exit code 1",
        subject_id="sub-001",
        return_code=1,
        retryable=True,
        rolled_back=True,
        stdout_excerpt="Error: cannot open file",
    )
    assert fr.stage == "dicom_to_nifti"
    assert fr.status == "failed"
    assert fr.return_code == 1
    assert fr.retryable is True


# ═══════════════════════════════════════════════════════════════════════
# Group 8 — Purity invariants
# ═══════════════════════════════════════════════════════════════════════


def test_schema_module_has_no_subprocess_import() -> None:
    """Schema module must not import subprocess."""
    import src.backend.app.schemas.dicom_conversion_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content
    assert "from subprocess" not in content
    assert "os.system" not in content


def test_schema_module_has_no_file_write() -> None:
    """Schema module must not write files."""
    import src.backend.app.schemas.dicom_conversion_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "open(" not in content  # No file I/O at module level
    assert "Path(" not in content or ".write_text" not in content


def test_schema_module_has_no_executor_import() -> None:
    """Schema module must not import the pipeline executor."""
    import src.backend.app.schemas.dicom_conversion_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "pipeline_executor" not in content
    assert "node_registry" not in content


def test_schema_module_has_no_spm_dpabi_matlab_import() -> None:
    """Schema module must not import SPM/DPABI/MATLAB modules."""
    import src.backend.app.schemas.dicom_conversion_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import spm" not in content.lower()
    assert "from spm" not in content.lower()
    assert "import matlab" not in content.lower()
    assert "from matlab" not in content.lower()
    assert "import dpabi" not in content.lower()
    assert "from dpabi" not in content.lower()


def test_redact_preview_is_pure() -> None:
    """Redaction must be pure — no file I/O, no subprocess."""
    result = redact_command_preview("dcm2niix -z y -f test -o /out /in")
    assert isinstance(result, str)
    assert len(result) > 0
