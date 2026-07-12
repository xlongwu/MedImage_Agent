"""Tests for reviewed preprocessing orchestrator."""
from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def _setup_store(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    for module in (
        "src.backend.app.services.preprocessing_run",
        "src.backend.app.services.preprocessing_pipeline_report",
        "src.backend.app.services.preprocessing_pipeline_validation",
    ):
        monkeypatch.setattr(f"{module}.mock_store", store)
    return store


def _make_converted_bids(tmp_path: Path, subjects: int = 1) -> Path:
    root = tmp_path / "converted_bids"
    for index in range(1, subjects + 1):
        func = root / f"sub-{index:03d}" / "func"
        anat = root / f"sub-{index:03d}" / "anat"
        func.mkdir(parents=True)
        anat.mkdir(parents=True)
        nib.save(
            nib.Nifti1Image(np.ones((3, 3, 3, 12), dtype=np.float32), affine=np.eye(4)),
            str(func / f"sub-{index:03d}_task-rest_bold.nii.gz"),
        )
        (func / f"sub-{index:03d}_task-rest_bold.json").write_text(
            '{"RepetitionTime": 2.0, "SliceTiming": [0.0, 0.6, 1.2]}',
            encoding="utf-8",
        )
        nib.save(
            nib.Nifti1Image(np.ones((3, 3, 3), dtype=np.float32), affine=np.eye(4)),
            str(anat / f"sub-{index:03d}_T1w.nii.gz"),
        )
    return root


def _create_run(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run

    request = PreprocessingRunCreateRequest(preprocessing_input_dir=str(_make_converted_bids(tmp_path)))
    result = create_preprocessing_run("brain-tumor-study", request, project_dir=str(tmp_path))
    assert result.ok
    return result, store


def _confirmations() -> dict:
    return {
        "confirm_rawdata_readonly": True,
        "confirm_reviewed_execution": True,
        "confirm_research_use_only": True,
        "confirm_no_clinical_use": True,
    }


def test_reviewed_orchestrator_blocks_external_stage_without_approval(tmp_path, monkeypatch):
    created, store = _create_run(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_pipeline import PreprocessingPipelineExecuteRequest
    from src.backend.app.services.preprocessing_orchestrator import execute_reviewed_preprocessing_pipeline

    request = PreprocessingPipelineExecuteRequest(
        stages={"dummy_scan_removal": "disabled"},
        backend_policy={"motion_correction": "spm12"},
        confirmations=_confirmations(),
    )
    result = execute_reviewed_preprocessing_pipeline(
        "brain-tumor-study",
        created.preprocessing_run_id,
        request,
        project_dir=str(tmp_path),
        store=store,
    )

    assert result.status == "blocked"
    assert result.ok is False
    assert "realignment" in result.blocked_stages
    assert result.safety_flags["no_external_tools_executed"] is True
    assert Path(result.manifest_path).exists()
    realignment = next(item for item in result.stage_results if item.stage_id == "realignment")
    assert any("Approval Gate" in issue for issue in realignment.blocking_issues)


def test_reviewed_orchestrator_delegates_default_execution_to_native_full(tmp_path, monkeypatch):
    created, store = _create_run(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_pipeline import PreprocessingPipelineExecuteRequest
    from src.backend.app.services.preprocessing_orchestrator import execute_reviewed_preprocessing_pipeline

    request = PreprocessingPipelineExecuteRequest(
        pipeline_profile="fc_minimal",
        stages={"dummy_scan_removal": "disabled", "functional_connectivity": "disabled"},
        confirmations=_confirmations(),
    )
    result = execute_reviewed_preprocessing_pipeline(
        "brain-tumor-study",
        created.preprocessing_run_id,
        request,
        project_dir=str(tmp_path),
        store=store,
    )

    assert result.approval_gate["native_full_delegated"] is True
    assert result.safety_flags["reviewed_native_full_delegated"] is True
    assert result.safety_flags["no_external_tools_executed"] is True
    realignment = next(item for item in result.stage_results if item.stage_id == "realignment")
    assert realignment.node_id == "native_preproc_realignment"
    assert not any(item.node_id.startswith("spm_") for item in result.stage_results)


def test_reviewed_orchestrator_resume_reuses_registered_external_outputs(tmp_path, monkeypatch):
    created, store = _create_run(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_pipeline import PreprocessingPipelineExecuteRequest
    from src.backend.app.services.preprocessing_artifact_registry import append_stage_output_artifacts
    from src.backend.app.services.preprocessing_orchestrator import execute_reviewed_preprocessing_pipeline

    run_dir = Path(created.run_dir)
    func_dir = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    func_dir.mkdir(parents=True)
    realigned = func_dir / "rsub-001_bold.nii"
    motion = func_dir / "rp_sub-001.txt"
    fd = tmp_path / "derivatives" / "rsfmri_qc" / "sub-001" / "fd_timeseries.tsv"
    fd.parent.mkdir(parents=True)
    realigned.write_text("already reviewed realignment output", encoding="utf-8")
    motion.write_text("0 0 0 0 0 0\n", encoding="utf-8")
    fd.write_text("frame\tframewise_displacement\n0\t0.0\n", encoding="utf-8")
    append_stage_output_artifacts(
        registry_path=run_dir / "preprocessing_artifact_registry.json",
        project_id="brain-tumor-study",
        preprocessing_run_id=created.preprocessing_run_id,
        stage_id="realignment",
        output_paths_by_type={
            "realigned_bold": [realigned],
            "motion_parameters": [motion],
            "fd_timeseries": [fd],
        },
        project_dir=str(tmp_path),
        source_execution_id="reviewed-spm-existing",
        backend="spm12",
    )

    request = PreprocessingPipelineExecuteRequest(
        pipeline_profile="custom",
        stages={"realignment": "enabled"},
        backend_policy={"motion_correction": "spm12"},
        confirmations=_confirmations(),
    )
    result = execute_reviewed_preprocessing_pipeline(
        "brain-tumor-study",
        created.preprocessing_run_id,
        request,
        project_dir=str(tmp_path),
        store=store,
    )

    assert result.status == "succeeded"
    assert "realignment" in result.completed_stages
    realignment = next(item for item in result.stage_results if item.stage_id == "realignment")
    assert "Completion artifacts already registered" in realignment.skipped_reason
    assert result.safety_flags["no_external_tools_executed"] is True


def test_nuisance_blocks_when_realignment_motion_qc_is_missing(tmp_path, monkeypatch):
    created, store = _create_run(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_pipeline import PreprocessingPipelineExecuteRequest
    from src.backend.app.services.preprocessing_artifact_registry import append_stage_output_artifacts
    from src.backend.app.services.preprocessing_orchestrator import execute_reviewed_preprocessing_pipeline

    run_dir = Path(created.run_dir)
    func_dir = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    func_dir.mkdir(parents=True)
    realigned = func_dir / "rsub-001_bold.nii"
    motion = func_dir / "rp_sub-001.txt"
    realigned.write_text("already reviewed realignment output", encoding="utf-8")
    motion.write_text("0 0 0 0 0 0\n", encoding="utf-8")
    append_stage_output_artifacts(
        registry_path=run_dir / "preprocessing_artifact_registry.json",
        project_id="brain-tumor-study",
        preprocessing_run_id=created.preprocessing_run_id,
        stage_id="realignment",
        output_paths_by_type={"realigned_bold": [realigned], "motion_parameters": [motion]},
        project_dir=str(tmp_path),
        source_execution_id="reviewed-spm-existing",
        backend="spm12",
    )

    request = PreprocessingPipelineExecuteRequest(
        pipeline_profile="custom",
        stages={"nuisance_regression": "enabled"},
        confirmations=_confirmations(),
    )
    result = execute_reviewed_preprocessing_pipeline(
        "brain-tumor-study",
        created.preprocessing_run_id,
        request,
        project_dir=str(tmp_path),
        store=store,
    )

    nuisance = next(item for item in result.stage_results if item.stage_id == "nuisance_regression")
    assert nuisance.status == "blocked"
    assert any("fd_timeseries" in issue for issue in nuisance.blocking_issues)


def test_preview_limit_marks_computed_stage_preview_only(tmp_path, monkeypatch):
    created, store = _create_run(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_pipeline import PreprocessingPipelineExecuteRequest
    from src.backend.app.services.preprocessing_artifact_registry import append_stage_output_artifacts
    from src.backend.app.services.preprocessing_orchestrator import execute_reviewed_preprocessing_pipeline

    run_dir = Path(created.run_dir)
    func_dir = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func"
    qc_dir = tmp_path / "derivatives" / "rsfmri_qc" / "sub-001"
    func_dir.mkdir(parents=True)
    qc_dir.mkdir(parents=True)
    n_time = 8
    realigned = func_dir / "rsub-001_bold.nii"
    nib.save(
        nib.Nifti1Image(np.zeros((3, 3, 3, n_time), dtype=np.float32), affine=np.eye(4)),
        str(realigned),
    )
    motion = func_dir / "rp_sub-001.txt"
    motion.write_text("\n".join(["0 0 0 0 0 0"] * n_time) + "\n", encoding="utf-8")
    fd = qc_dir / "fd_timeseries.tsv"
    fd.write_text("frame\tframewise_displacement\n0\t0.0\n", encoding="utf-8")
    append_stage_output_artifacts(
        registry_path=run_dir / "preprocessing_artifact_registry.json",
        project_id="brain-tumor-study",
        preprocessing_run_id=created.preprocessing_run_id,
        stage_id="realignment",
        output_paths_by_type={
            "realigned_bold": [realigned],
            "motion_parameters": [motion],
            "fd_timeseries": [fd],
        },
        project_dir=str(tmp_path),
        source_execution_id="reviewed-spm-existing",
        backend="spm12",
    )

    request = PreprocessingPipelineExecuteRequest(
        pipeline_profile="custom",
        stages={"realignment": "enabled", "nuisance_regression": "enabled"},
        backend_policy={"motion_correction": "spm12"},
        execution_limits={"preview_limit": 1},
        confirmations=_confirmations(),
    )
    result = execute_reviewed_preprocessing_pipeline(
        "brain-tumor-study",
        created.preprocessing_run_id,
        request,
        project_dir=str(tmp_path),
        store=store,
    )

    nuisance = next(item for item in result.stage_results if item.stage_id == "nuisance_regression")
    assert nuisance.status == "preview_only"
    assert "nuisance_regression" in result.preview_only_stages
    assert nuisance.result["execution_scope"]["preview_only"] is True


def test_report_and_validation_include_orchestrator_blocked_status(tmp_path, monkeypatch):
    created, store = _create_run(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_pipeline import PreprocessingPipelineExecuteRequest
    from src.backend.app.services.preprocessing_orchestrator import execute_reviewed_preprocessing_pipeline
    from src.backend.app.services.preprocessing_pipeline_report import generate_pipeline_report
    from src.backend.app.services.preprocessing_pipeline_validation import validate_preprocessing_pipeline

    request = PreprocessingPipelineExecuteRequest(
        stages={"dummy_scan_removal": "disabled"},
        backend_policy={"motion_correction": "spm12"},
        confirmations=_confirmations(),
    )
    execute_reviewed_preprocessing_pipeline(
        "brain-tumor-study",
        created.preprocessing_run_id,
        request,
        project_dir=str(tmp_path),
        store=store,
    )

    report = generate_pipeline_report("brain-tumor-study", created.preprocessing_run_id, project_dir=str(tmp_path))
    validation = validate_preprocessing_pipeline("brain-tumor-study", created.preprocessing_run_id, project_dir=str(tmp_path))

    report_realignment = next(item for item in report.stage_statuses if item["stage_id"] == "realignment")
    validation_realignment = next(item for item in validation.stage_summary if item["stage_id"] == "realignment")
    assert report_realignment["status"] == "blocked"
    assert validation_realignment["status"] == "blocked"
    assert report_realignment["orchestrator_result"]["stage_id"] == "realignment"
    assert validation_realignment["orchestrator_result"]["stage_id"] == "realignment"


def test_reviewed_endpoint_is_registered(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.api.dependencies import get_project_store
    from src.backend.app.main import app
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "api.sqlite")
    project = store.get_project("brain-tumor-study")
    assert project is not None
    project.metadata = {**(project.metadata or {}), "project_dir": str(tmp_path)}
    store.add_project(project, health_status="Review", rawdata_dir=str(tmp_path / "rawdata"), overwrite=True)
    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    try:
        response = client.post(
            "/api/projects/brain-tumor-study/preprocessing/runs/missing-run/execute-reviewed",
            json={"confirmations": _confirmations()},
        )
    finally:
        app.dependency_overrides.pop(get_project_store, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
