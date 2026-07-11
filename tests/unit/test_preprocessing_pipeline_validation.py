"""Tests for pipeline validation — Phase 5O."""
from __future__ import annotations
from pathlib import Path
import json, pytest
import nibabel as nib
import numpy as np

def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_pipeline_validation.mock_store", store)
    return store

from src.backend.app.services.preprocessing_pipeline_validation import validate_preprocessing_pipeline
from src.backend.app.services.preprocessing_pipeline_validation import _RELOAD_REQUIRED_TYPES

def test_not_started_for_missing_run(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.status == "not_started"

def test_detects_partial_pipeline(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    rd = tmp_path / "preprocessing_runs" / "pp-test"; rd.mkdir(parents=True)
    (rd / "reports").mkdir()
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.status in ("warning", "ready_for_review")

def test_includes_stage_summary(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    rd = tmp_path / "preprocessing_runs" / "pp-test"; rd.mkdir(parents=True)
    (rd / "spm_dry_runs").mkdir(); (rd / "spm_exec").mkdir(); (rd / "reports").mkdir()
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert len(result.stage_summary) > 0

def test_no_dpabi_in_safety_flags(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    rd = tmp_path / "preprocessing_runs" / "pp-test"; rd.mkdir(parents=True)
    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))
    assert result.safety_flags["no_dpabi_execution"] is True

def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app; client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/preprocessing/runs/pp-test/validation")
    assert resp.status_code == 200


def test_reload_required_types_include_metric_maps_and_atlas():
    assert {"alff_map", "falff_map", "reho_map", "atlas"} <= _RELOAD_REQUIRED_TYPES


def test_validation_reloads_metric_maps_and_atlas(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    run_dir = tmp_path / "preprocessing_runs" / "pp-test"
    run_dir.mkdir(parents=True)
    (run_dir / "reports").mkdir()
    exec_dir = run_dir / "spm_exec" / "existing"
    exec_dir.mkdir(parents=True)
    (exec_dir / "manifest.json").write_text(json.dumps({"status": "succeeded"}), encoding="utf-8")

    derivatives = tmp_path / "derivatives"
    derivatives.mkdir()
    affine = np.eye(4)
    alff = derivatives / "sub-001_desc-alff_map.nii.gz"
    falff = derivatives / "sub-001_desc-falff_map.nii.gz"
    reho = derivatives / "sub-001_desc-reho_map.nii.gz"
    atlas = derivatives / "aal_atlas_sha256-test.nii"
    for path in (alff, falff, reho, atlas):
        nib.save(nib.Nifti1Image(np.ones((3,3,3), dtype=np.float32), affine), str(path))

    registry = {
        "artifacts": [
            {"artifact_id": "a1", "stage_id": "alff_falff", "artifact_type": "alff_map", "path": str(alff), "path_kind": "local_runtime"},
            {"artifact_id": "a2", "stage_id": "alff_falff", "artifact_type": "falff_map", "path": str(falff), "path_kind": "local_runtime"},
            {"artifact_id": "r1", "stage_id": "reho", "artifact_type": "reho_map", "path": str(reho), "path_kind": "local_runtime"},
            {"artifact_id": "t1", "stage_id": "functional_connectivity", "artifact_type": "atlas", "path": str(atlas), "path_kind": "local_runtime"},
        ]
    }
    (run_dir / "preprocessing_artifact_registry.json").write_text(json.dumps(registry), encoding="utf-8")

    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))

    by_stage = {item["stage_id"]: item for item in result.stage_summary}
    alff_checks = by_stage["alff_falff"]["reload_checks"]
    reho_checks = by_stage["reho"]["reload_checks"]
    fc_checks = by_stage["functional_connectivity"]["reload_checks"]
    assert {item["artifact_type"] for item in alff_checks} == {"alff_map", "falff_map"}
    assert {item["artifact_type"] for item in reho_checks} == {"reho_map"}
    assert {item["artifact_type"] for item in fc_checks} == {"atlas"}
    assert all(item["ok"] for item in [*alff_checks, *reho_checks, *fc_checks])


def test_validation_preview_or_metadata_status_is_not_ready(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    run_dir = tmp_path / "preprocessing_runs" / "pp-test"
    run_dir.mkdir(parents=True)
    (run_dir / "reports").mkdir()
    exec_dir = run_dir / "spm_exec" / "existing"
    exec_dir.mkdir(parents=True)
    (exec_dir / "manifest.json").write_text(json.dumps({"status": "succeeded"}), encoding="utf-8")
    (run_dir / "preprocessing_run_manifest.json").write_text(
        json.dumps({
            "stage_statuses": [
                {
                    "stage_id": "functional_connectivity",
                    "status": "preview_only",
                    "output_manifest": {"result": {"preview_only": True}},
                },
                {
                    "stage_id": "alff_falff",
                    "status": "metadata_only",
                    "output_manifest": {"result": {"metadata_only": True}},
                },
            ]
        }),
        encoding="utf-8",
    )

    result = validate_preprocessing_pipeline("brain-tumor-study", "pp-test", project_dir=str(tmp_path))

    assert result.status == "warning"
    assert "functional_connectivity" in result.preview_only_stages
    assert "alff_falff" in result.metadata_only_stages
    assert any("Preview-only stages" in warning for warning in result.warnings)
    assert any("Metadata-only stages" in warning for warning in result.warnings)
