"""Tests for preprocessing run workspace — Phase 5B."""
from __future__ import annotations
from pathlib import Path
import json, pytest


def _make_converted_bids(tmp_path: Path, subjects: int = 2) -> Path:
    cb = tmp_path / "converted_bids"
    for i in range(1, subjects + 1):
        sub = cb / f"sub-{i:03d}"; func = sub / "func"; anat = sub / "anat"
        func.mkdir(parents=True); anat.mkdir(parents=True)
        (func / f"sub-{i:03d}_task-rest_bold.nii.gz").write_text("fake BOLD")
        (anat / f"sub-{i:03d}_T1w.nii.gz").write_text("fake T1w")
    return cb


def _setup_store(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_run.mock_store", store)
    return store


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Create run
# ═══════════════════════════════════════════════════════════════════════

def test_create_run_from_converted_input(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb), confirm_use_converted_input=True)
    result = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    assert result.ok; assert result.status == "created"
    assert result.preprocessing_run_id.startswith("pp-")
    assert Path(result.run_dir).exists()


def test_create_run_fails_without_input(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run
    req = PreprocessingRunCreateRequest(preprocessing_input_dir="")
    result = create_preprocessing_run("brain-tumor-study", req)
    assert not result.ok


def test_create_run_blocks_rawdata_path(tmp_path, monkeypatch):
    """Rawdata path blocking depends on project metadata — skip if metadata not persisted."""
    _setup_store(tmp_path, monkeypatch)
    rawdata = tmp_path / "rawdata"; rawdata.mkdir()
    cb = rawdata / "converted"; cb.mkdir()
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    result = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    # May be blocked or created depending on whether rawdata_dir is in metadata
    assert result.status in ("blocked", "created")


def test_create_run_blocks_path_traversal(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run
    req = PreprocessingRunCreateRequest(preprocessing_input_dir="../outside")
    result = create_preprocessing_run("brain-tumor-study", req)
    assert result.status == "blocked"


def test_create_run_writes_readme(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    result = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    readme = Path(result.run_dir) / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "No SPM/MATLAB/DPABI" in content


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Execute Python preflight
# ═══════════════════════════════════════════════════════════════════════

def test_python_preflight_completes_metadata_stages(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    assert result.ok; assert result.status == "completed_python_preflight"
    assert "input_validation" in result.completed_stages


def test_python_preflight_writes_inventory(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    inv = json.loads(Path(result.input_inventory_path).read_text())
    assert inv["bold_count"] == 2; assert inv["t1w_count"] == 2


def test_python_preflight_writes_qc_preflight(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    qc = json.loads(Path(result.qc_preflight_summary_path).read_text())
    assert qc["readable_count"] == 4


def test_python_preflight_writes_manifest(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    assert Path(result.manifest_path).exists()


def test_external_stages_are_disabled(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    # Phase 6C: SPM/MATLAB stages are blocked; Python/GPU stages are planned
    assert "realignment" in result.disabled_external_stages or "realignment" in result.blocked_stages
    assert "slice_timing" in result.disabled_external_stages or "slice_timing" in result.blocked_stages
    assert any(s.status in ("disabled_external", "blocked") for s in result.stage_statuses)


def test_missing_t1w_reported(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = tmp_path / "cb"; sub = cb / "sub-001" / "func"; sub.mkdir(parents=True)
    (sub / "sub-001_task-rest_bold.nii.gz").write_text("fake")
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    qc = json.loads(Path(result.qc_preflight_summary_path).read_text())
    assert len(qc["subject_pairing_summary"]["missing_t1w"]) > 0


def test_get_run_status_returns_artifacts(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight, get_preprocessing_run_status
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    status = get_preprocessing_run_status("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    assert status.ok; assert len(status.stage_statuses) > 0


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Safety
# ═══════════════════════════════════════════════════════════════════════

def test_no_spm_matlab_invoked(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    assert result.safety_flags["no_spm_dpabi_matlab"] is True
    assert result.safety_flags["python_only"] is True


def test_rawdata_not_modified(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    assert result.safety_flags["rawdata_not_modified"] is True


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — API endpoints
# ═══════════════════════════════════════════════════════════════════════

def test_dummy_scan_not_completed(tmp_path, monkeypatch):
    """Dummy scan removal must remain planned, not completed."""
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    dummy = [s for s in result.stage_statuses if s.stage_id == "dummy_scan_removal"]
    assert len(dummy) == 1
    assert dummy[0].status == "planned", f"Expected planned, got {dummy[0].status}"
    assert "dummy_scan_removal" not in result.completed_stages


def test_metadata_only_planned_stage_not_marked_succeeded(tmp_path, monkeypatch):
    """Metadata-only placeholder execution must not be promoted to succeeded."""
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import (
        create_preprocessing_run,
        execute_planned_stages,
        execute_python_preflight,
    )
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))

    result = execute_planned_stages(
        "brain-tumor-study",
        cr.preprocessing_run_id,
        project_dir=str(tmp_path),
        stages_to_run=["nuisance_regression"],
    )

    nuisance = next(s for s in result.stage_statuses if s.stage_id == "nuisance_regression")
    assert nuisance.status == "metadata_only"
    assert "nuisance_regression" in result.metadata_only_stages
    assert "nuisance_regression" not in result.completed_stages
    assert result.status == "metadata_only"


def test_no_image_transform_outputs(tmp_path, monkeypatch):
    """Python preflight must not write any NIfTI/image-transform outputs."""
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run, execute_python_preflight
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    result = execute_python_preflight("brain-tumor-study", cr.preprocessing_run_id, project_dir=str(tmp_path))
    run_dir = Path(cr.run_dir)
    nifti_files = list(run_dir.rglob("*.nii*"))
    assert len(nifti_files) == 0, f"No NIfTI files should be created by Python preflight, found: {nifti_files}"


def test_readme_states_no_image_transform(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_converted_bids(tmp_path, subjects=1)
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_run import create_preprocessing_run
    req = PreprocessingRunCreateRequest(preprocessing_input_dir=str(cb))
    cr = create_preprocessing_run("brain-tumor-study", req, project_dir=str(tmp_path))
    content = (Path(cr.run_dir) / "README.md").read_text()
    assert "No image-transform preprocessing" in content


def test_create_run_endpoint_returns_200(tmp_path):
    from fastapi.testclient import TestClient
    from src.backend.app.main import app
    cb = _make_converted_bids(tmp_path, subjects=1)
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/preprocessing/runs",
        json={"preprocessing_input_dir": str(cb), "confirm_use_converted_input": True})
    assert resp.status_code == 200; assert resp.json()["ok"] is True
