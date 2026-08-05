"""Tests for SPM slice timing and realign dry-run - Phase 5D."""

from __future__ import annotations

import json
from pathlib import Path


def _make_bold_input(tmp_path: Path, subjects: int = 2) -> Path:
    cb = tmp_path / "converted_bids"
    for i in range(1, subjects + 1):
        sub = cb / f"sub-{i:03d}" / "func"
        sub.mkdir(parents=True)
        (sub / f"sub-{i:03d}_task-rest_bold.nii.gz").write_text("fake BOLD")
        (sub / f"sub-{i:03d}_task-rest_bold.json").write_text('{"RepetitionTime":2.0}')
    return cb


def _setup_store(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr("src.backend.app.services.preprocessing_spm_dry_run.mock_store", store)
    return store


from src.backend.app.schemas.preprocessing_spm_dry_run import (  # noqa: E402
    SliceTimingRealignDryRunRequest,  # noqa: E402
)
from src.backend.app.services.preprocessing_spm_dry_run import (  # noqa: E402
    run_slice_timing_realign_dry_run,  # noqa: E402
)


def test_dry_run_succeeds_with_bold_files(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_bold_input(tmp_path)
    req = SliceTimingRealignDryRunRequest(
        tr=2.0, preprocessing_input_dir=str(cb), confirm_dry_run_only=True
    )
    result = run_slice_timing_realign_dry_run(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )
    assert result.ok
    assert result.bold_count == 2
    assert len(result.batch_preview_paths) == 2


def test_dry_run_blocks_zero_bold(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    empty = tmp_path / "empty"
    empty.mkdir()
    req = SliceTimingRealignDryRunRequest(preprocessing_input_dir=str(empty))
    result = run_slice_timing_realign_dry_run(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )
    assert result.status == "blocked"


def test_dry_run_warns_missing_tr(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_bold_input(tmp_path)
    for jf in cb.rglob("*.json"):
        jf.unlink()
    req = SliceTimingRealignDryRunRequest(
        preprocessing_input_dir=str(cb), confirm_dry_run_only=True
    )
    result = run_slice_timing_realign_dry_run(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )
    assert any("TR" in w for w in result.warnings)


def test_dry_run_blocks_invalid_tr(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_bold_input(tmp_path, subjects=1)
    req = SliceTimingRealignDryRunRequest(tr=-1.0, preprocessing_input_dir=str(cb))
    result = run_slice_timing_realign_dry_run("brain-tumor-study", "pp-test", req)
    assert result.status == "blocked"


def test_dry_run_writes_batch_preview(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_bold_input(tmp_path, subjects=1)
    req = SliceTimingRealignDryRunRequest(
        tr=2.0, preprocessing_input_dir=str(cb), confirm_dry_run_only=True
    )
    result = run_slice_timing_realign_dry_run(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )
    batch = Path(result.batch_preview_paths[0]).read_text(encoding="utf-8")
    assert "DRY_RUN_ONLY" in batch
    assert "NOT EXECUTED" in batch


def test_dry_run_writes_manifest(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_bold_input(tmp_path, subjects=1)
    req = SliceTimingRealignDryRunRequest(
        tr=2.0, preprocessing_input_dir=str(cb), confirm_dry_run_only=True
    )
    result = run_slice_timing_realign_dry_run(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )
    mf = Path(result.dry_run_dir) / "dry_run_manifest.json"
    assert mf.exists()
    assert json.loads(mf.read_text())["status"] == "dry_run_preview"


def test_dry_run_no_nifti_outputs(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_bold_input(tmp_path, subjects=1)
    req = SliceTimingRealignDryRunRequest(
        tr=2.0, preprocessing_input_dir=str(cb), confirm_dry_run_only=True
    )
    result = run_slice_timing_realign_dry_run(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )
    if result.dry_run_dir:
        assert len(list(Path(result.dry_run_dir).rglob("*.nii*"))) == 0


def test_dry_run_safety_flags(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    cb = _make_bold_input(tmp_path, subjects=1)
    req = SliceTimingRealignDryRunRequest(
        tr=2.0, preprocessing_input_dir=str(cb), confirm_dry_run_only=True
    )
    result = run_slice_timing_realign_dry_run(
        "brain-tumor-study", "pp-test", req, project_dir=str(tmp_path)
    )
    assert result.safety_flags["no_spm_executed"] is True
    assert result.safety_flags["no_image_outputs_written"] is True


def test_dry_run_endpoint_returns_200(tmp_path):
    from fastapi.testclient import TestClient

    from src.backend.app.main import app

    cb = _make_bold_input(tmp_path, subjects=1)
    client = TestClient(app)
    resp = client.post(
        "/api/projects/brain-tumor-study/preprocessing/runs/pp-test/spm/slice-timing-realign/dry-run",
        json={"tr": 2.0, "preprocessing_input_dir": str(cb), "confirm_dry_run_only": True},
    )
    assert resp.status_code == 200
