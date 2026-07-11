"""Tests for preprocessing input handoff — Phase 5A."""
from __future__ import annotations
from pathlib import Path
import pytest


def _make_converted_bids(tmp_path: Path, subjects: int = 3) -> Path:
    cb = tmp_path / "converted_bids"
    for i in range(1, subjects + 1):
        sub = cb / f"sub-{i:03d}"
        func = sub / "func"; anat = sub / "anat"
        func.mkdir(parents=True); anat.mkdir(parents=True)
        (func / f"sub-{i:03d}_task-rest_bold.nii.gz").write_text("fake BOLD")
        (func / f"sub-{i:03d}_task-rest_bold.json").write_text('{"TaskName":"rest"}')
        (anat / f"sub-{i:03d}_T1w.nii.gz").write_text("fake T1w")
        (anat / f"sub-{i:03d}_T1w.json").write_text("{}")
    return cb


def _make_converted_with_missing_t1w(tmp_path: Path) -> Path:
    cb = tmp_path / "converted_missing"
    for i in range(1, 4):
        sub = cb / f"sub-{i:03d}" / "func"; sub.mkdir(parents=True)
        (sub / f"sub-{i:03d}_task-rest_bold.nii.gz").write_text("fake")
    return cb


def _setup_store(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_handoff.mock_store", store)
    return store


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Registration
# ═══════════════════════════════════════════════════════════════════════

def test_register_converted_bids_counts_correctly(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path)
    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import register_converted_bids_as_preprocessing_input
    req = PreprocessingInputRegistrationRequest(conversion_run_id="conv-test", converted_bids_dir=str(cb), confirm_rawdata_readonly=True, confirm_use_converted_outputs=True)
    result = register_converted_bids_as_preprocessing_input("brain-tumor-study", req)
    assert result.ok; assert result.bold_count == 3; assert result.t1w_count == 3
    assert result.nifti_count == 6; assert result.subject_count == 3


def test_register_fails_when_conversion_run_missing(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import register_converted_bids_as_preprocessing_input
    req = PreprocessingInputRegistrationRequest(conversion_run_id="")
    result = register_converted_bids_as_preprocessing_input("brain-tumor-study", req)
    assert not result.ok; assert result.status == "blocked"


def test_register_fails_when_dir_missing(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import register_converted_bids_as_preprocessing_input
    req = PreprocessingInputRegistrationRequest(conversion_run_id="conv-test", converted_bids_dir=str(tmp_path / "nonexistent"))
    result = register_converted_bids_as_preprocessing_input("brain-tumor-study", req)
    assert result.status == "blocked"


def test_register_blocks_path_traversal(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import register_converted_bids_as_preprocessing_input
    req = PreprocessingInputRegistrationRequest(conversion_run_id="conv-test", converted_bids_dir="../outside/converted")
    result = register_converted_bids_as_preprocessing_input("brain-tumor-study", req)
    assert result.status == "blocked"
    assert any("traversal" in b.lower() for b in result.blocking_issues)


def test_register_reports_missing_t1w(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_with_missing_t1w(tmp_path)
    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import register_converted_bids_as_preprocessing_input
    req = PreprocessingInputRegistrationRequest(conversion_run_id="conv-test", converted_bids_dir=str(cb))
    result = register_converted_bids_as_preprocessing_input("brain-tumor-study", req)
    assert len(result.missing_t1w_subjects) > 0


def test_register_writes_metadata(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import register_converted_bids_as_preprocessing_input
    req = PreprocessingInputRegistrationRequest(conversion_run_id="conv-test", converted_bids_dir=str(cb))
    result = register_converted_bids_as_preprocessing_input("brain-tumor-study", req)
    assert result.ok
    assert result.preprocessing_input_dir == str(cb)


def test_register_does_not_execute_preprocessing(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import register_converted_bids_as_preprocessing_input
    req = PreprocessingInputRegistrationRequest(conversion_run_id="conv-test", converted_bids_dir=str(cb))
    result = register_converted_bids_as_preprocessing_input("brain-tumor-study", req)
    assert result.safety_flags.get("no_preprocessing_executed") is True
    assert result.safety_flags.get("rawdata_not_modified") is True


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Plan preview
# ═══════════════════════════════════════════════════════════════════════

def test_plan_preview_returns_dparsfa_stages():
    from src.backend.app.schemas.preprocessing_handoff import build_default_dparsfa_style_plan
    plan = build_default_dparsfa_style_plan("test-project", input_registered=True)
    assert plan.ok; assert plan.status == "preview_only"
    assert plan.stage_count == 15; assert plan.execution_disabled is True
    assert plan.preprocessing_input_registered is True
    native_stages = [s for s in plan.stages if s.backend == "native_python"]
    external_stages = [s for s in plan.stages if s.requires_external_tool]
    assert len(native_stages) == 11
    assert len(external_stages) == 0
    for stage_id in (
        "slice_timing",
        "realignment",
        "nuisance_regression",
        "temporal_filtering",
        "alff_falff",
        "reho",
        "functional_connectivity",
    ):
        stage = next(s for s in plan.stages if s.stage_id == stage_id)
        assert stage.backend == "native_python"
        assert not stage.requires_external_tool
    realignment = next(s for s in plan.stages if s.stage_id == "realignment")
    assert "spm12" in realignment.supported_backends
    fc = next(s for s in plan.stages if s.stage_id == "functional_connectivity")
    assert fc.required_for_fc is True
    assert fc.optional is False


def test_plan_preview_warns_when_input_not_registered():
    from src.backend.app.schemas.preprocessing_handoff import build_default_dparsfa_style_plan
    plan = build_default_dparsfa_style_plan("test-project", input_registered=False)
    assert not plan.preprocessing_input_registered
    assert any("not been registered" in w.lower() for w in plan.warnings)


def test_plan_preview_is_preview_only():
    from src.backend.app.schemas.preprocessing_handoff import build_default_dparsfa_style_plan
    plan = build_default_dparsfa_style_plan()
    assert plan.safety_flags.get("preview_only") is True
    assert plan.safety_flags.get("no_preprocessing_executed") is True
    assert plan.safety_flags.get("native_backend_default") is True
    assert plan.safety_flags.get("spm_dpabi_matlab_disabled") is True


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — API endpoints
# ═══════════════════════════════════════════════════════════════════════

def test_register_endpoint_returns_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    cb = _make_converted_bids(tmp_path, subjects=1)
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/input/register-converted", json={"conversion_run_id": "conv-test", "converted_bids_dir": str(cb)})
    assert resp.status_code == 200


def test_plan_preview_endpoint_returns_200():
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/plan/preview")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "preview_only"
    assert payload["execution_disabled"] is True


def test_register_endpoint_404_for_missing_project():
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    client = TestClient(app)
    resp = client.post("/api/projects/nonexistent/preprocessing/input/register-converted", json={"conversion_run_id": "conv-test"})
    assert resp.status_code == 404
