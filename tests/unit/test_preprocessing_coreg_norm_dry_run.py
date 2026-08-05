"""Tests for coregistration + normalization dry-run - Phase 5G."""

from __future__ import annotations

from pathlib import Path


def _setup_store(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr(
        "src.backend.app.services.preprocessing_coreg_norm_dry_run.mock_store", store
    )
    return store


def _make_func_input(tmp_path):
    sandbox = tmp_path / "ppr" / "pp-test" / "spm_exec" / "ex-1" / "sandbox_output"
    sub = sandbox / "sub-001"
    sub.mkdir(parents=True)
    (sub / "rasub-001_task-rest_bold.nii").write_text("func")
    (sub / "meansub-001_task-rest_bold.nii").write_text("mean")
    (sub / "rp_sub-001.txt").write_text("motion")
    return sandbox


def _make_t1w(tmp_path):
    cb = tmp_path / "cb"
    sub = cb / "sub-001" / "anat"
    sub.mkdir(parents=True)
    (sub / "sub-001_T1w.nii.gz").write_text("t1w")
    return cb


from src.backend.app.schemas.preprocessing_coreg_norm_dry_run import (  # noqa: E402
    CoregNormDryRunRequest,  # noqa: E402
)
from src.backend.app.services.preprocessing_coreg_norm_dry_run import (  # noqa: E402
    run_coreg_norm_dry_run,  # noqa: E402
)


def test_blocks_no_func_input(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    result = run_coreg_norm_dry_run(
        "brain-tumor-study", "pp-test", CoregNormDryRunRequest(), project_dir=str(tmp_path)
    )
    assert result.status == "blocked"


def test_dry_run_succeeds(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch)
    sandbox = _make_func_input(tmp_path)
    t1w_dir = _make_t1w(tmp_path)
    proj = store.get_project("brain-tumor-study")
    if not isinstance(proj.metadata, dict):
        proj.metadata = {}
    proj.metadata["current_functional_input_dir"] = str(sandbox)
    proj.metadata["preprocessing_input_dir"] = str(t1w_dir)
    result = run_coreg_norm_dry_run(
        "brain-tumor-study",
        "pp-test",
        CoregNormDryRunRequest(functional_input_dir=str(sandbox), confirm_dry_run_only=True),
        project_dir=str(tmp_path),
    )
    assert result.ok and result.functional_input_count >= 1


def test_warns_missing_t1w(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch)
    sandbox = _make_func_input(tmp_path)
    proj = store.get_project("brain-tumor-study")
    if not isinstance(proj.metadata, dict):
        proj.metadata = {}
    proj.metadata["current_functional_input_dir"] = str(sandbox)
    result = run_coreg_norm_dry_run(
        "brain-tumor-study",
        "pp-test",
        CoregNormDryRunRequest(functional_input_dir=str(sandbox), confirm_dry_run_only=True),
        project_dir=str(tmp_path),
    )
    assert any("T1w" in w for w in result.warnings)


def test_writes_batch(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch)
    sandbox = _make_func_input(tmp_path)
    t1w_dir = _make_t1w(tmp_path)
    proj = store.get_project("brain-tumor-study")
    if not isinstance(proj.metadata, dict):
        proj.metadata = {}
    proj.metadata["current_functional_input_dir"] = str(sandbox)
    proj.metadata["preprocessing_input_dir"] = str(t1w_dir)
    result = run_coreg_norm_dry_run(
        "brain-tumor-study",
        "pp-test",
        CoregNormDryRunRequest(functional_input_dir=str(sandbox), confirm_dry_run_only=True),
        project_dir=str(tmp_path),
    )
    assert len(result.batch_preview_paths) > 0
    assert "COREG_NORM_DRY_RUN_ONLY" in Path(result.batch_preview_paths[0]).read_text()


def test_no_nifti_in_dry_dir(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch)
    sandbox = _make_func_input(tmp_path)
    t1w_dir = _make_t1w(tmp_path)
    proj = store.get_project("brain-tumor-study")
    if not isinstance(proj.metadata, dict):
        proj.metadata = {}
    proj.metadata["current_functional_input_dir"] = str(sandbox)
    proj.metadata["preprocessing_input_dir"] = str(t1w_dir)
    result = run_coreg_norm_dry_run(
        "brain-tumor-study",
        "pp-test",
        CoregNormDryRunRequest(functional_input_dir=str(sandbox), confirm_dry_run_only=True),
        project_dir=str(tmp_path),
    )
    if result.dry_run_dir:
        assert len(list(Path(result.dry_run_dir).rglob("*.nii*"))) == 0


def test_endpoint_200(tmp_path):
    from fastapi.testclient import TestClient

    from src.backend.app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/projects/brain-tumor-study/preprocessing/runs/pp-test/spm/coreg-normalize/dry-run",
        json={"confirm_dry_run_only": True},
    )
    assert resp.status_code == 200
