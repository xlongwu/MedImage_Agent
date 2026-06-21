"""Tests for ReHo execution vs validation status separation.

Per the AGENTS Scientific Computing Contract, execution status (what the
current run produced) must be kept separate from validation status (what
level of scientific confidence the algorithm implementation has reached).
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import nibabel as nib
import pytest

_ALL = {"MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_ALFF_REHO": "1"}


def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr(
        "src.backend.app.services.preprocessing_alff_reho_execution.mock_store", store,
    )
    return store


def _make_bold(func_dir, subject="sub-001", tr=2.0):
    sub_dir = func_dir / subject / "func"
    sub_dir.mkdir(parents=True)
    data = np.random.default_rng(42).random((8, 8, 8, 120)).astype(np.float32)
    img = nib.Nifti1Image(data, np.eye(4))
    nii_path = sub_dir / f"{subject}_task-rest_bold.nii.gz"
    nib.save(img, str(nii_path))
    (sub_dir / f"{subject}_task-rest_bold.json").write_text(
        json.dumps({"RepetitionTime": tr, "TaskName": "rest"})
    )
    return nii_path


def _make_dry_run(tmp_path):
    dd = tmp_path / "preprocessing_runs" / "pp-test" / "spm_dry_runs" / "dr-test"
    dd.mkdir(parents=True)
    (dd / "alff_reho_dry_run_manifest.json").write_text(
        json.dumps({"status": "dry_run_preview", "files": []})
    )


class TestRehoStatusSeparation:
    """Execution status and validation status are independent dimensions."""

    def test_all_succeed_uses_numerically_computed(self, tmp_path, monkeypatch):
        """All ReHo subjects succeed → execution status = numerically_computed."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup(tmp_path, monkeypatch)
        func_dir = tmp_path / "func"; func_dir.mkdir()
        for i in range(1, 4):
            _make_bold(func_dir, subject=f"sub-{i:03d}")
        _make_dry_run(tmp_path)
        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj", "pp-test", req, env=_ALL, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.reho_computed is True
        assert result.reho_status == "numerically_computed", \
            f"Expected numerically_computed, got {result.reho_status}"
        assert result.reho_validation_status == "golden_validated"
        assert result.reho_backend == "cpu-numpy"

    def test_partial_subjects_use_partially_computed(self, tmp_path, monkeypatch):
        """Some ReHo subjects fail → execution status = partially_computed."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup(tmp_path, monkeypatch)
        func_dir = tmp_path / "func"; func_dir.mkdir()
        for i in range(1, 6):
            _make_bold(func_dir, subject=f"sub-{i:03d}")
        _make_dry_run(tmp_path)

        # Mock ReHo kernel to fail for all subjects → 0 succeed
        def mock_fail(*a, **kw):
            return {"ok": False, "errors": ["mocked failure"]}
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_backend", mock_fail,
        )

        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj", "pp-test", req, env=_ALL, project_dir=str(tmp_path),
        )
        assert result.ok
        # ReHo computed flag is False since no ReHo succeeded
        assert result.reho_computed is False
        assert result.reho_status == "metadata_only", \
            f"Expected metadata_only when 0 succeed, got {result.reho_status}"
        assert result.reho_backend == "none"

    def test_manifest_has_separate_status_dimensions(self, tmp_path, monkeypatch):
        """manifest.json reho section separates execution/validation/backend."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup(tmp_path, monkeypatch)
        func_dir = tmp_path / "func"; func_dir.mkdir()
        _make_bold(func_dir, subject="sub-001")
        _make_dry_run(tmp_path)
        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj", "pp-test", req, env=_ALL, project_dir=str(tmp_path),
        )
        assert result.ok

        mf = json.loads(Path(result.manifest_path).read_text())
        reho = mf["reho"]
        assert reho["computed"] is True
        # Execution status: what this run produced
        assert reho["execution_status"] == "numerically_computed", \
            f"Expected numerically_computed in manifest, got {reho.get('execution_status')}"
        # Validation status: scientific confidence level of the implementation
        assert reho["validation_status"] == "golden_validated"
        assert reho["backend"] == "cpu-numpy"
        assert "external_reference_validated" in reho
        assert reho["external_reference_validated"] is False
        assert "gpu_validated" in reho
        assert reho["gpu_validated"] is False
        # Old key "status" should NOT exist
        assert "status" not in reho, \
            "Legacy 'status' key should not exist in manifest.reho"

    def test_validation_status_unchanged_when_reho_fails(self, tmp_path, monkeypatch):
        """When no ReHo succeeds, validation_status stays 'unvalidated'."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup(tmp_path, monkeypatch)
        func_dir = tmp_path / "func"; func_dir.mkdir()
        _make_bold(func_dir, subject="sub-001")
        _make_dry_run(tmp_path)

        def mock_fail(*a, **kw):
            return {"ok": False, "errors": ["mock"]}
        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_backend", mock_fail,
        )

        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj", "pp-test", req, env=_ALL, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.reho_computed is False
        assert result.reho_status == "metadata_only"
        assert result.reho_validation_status == "unvalidated"
        assert result.reho_backend == "none"
