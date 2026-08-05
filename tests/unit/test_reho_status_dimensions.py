"""Tests for ReHo execution vs validation status separation.

Per the AGENTS Scientific Computing Contract, execution status (what the
current run produced) must be kept separate from validation status (what
level of scientific confidence the algorithm implementation has reached).
Validation status is a property of the algorithm, not of this run's outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

_ALL = {"MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_ALFF_REHO": "1"}


def _setup(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr(
        "src.backend.app.services.preprocessing_alff_reho_execution.mock_store",
        store,
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
        func_dir = tmp_path / "func"
        func_dir.mkdir()
        for i in range(1, 4):
            _make_bold(func_dir, subject=f"sub-{i:03d}")
        _make_dry_run(tmp_path)
        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test",
            functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj",
            "pp-test",
            req,
            env=_ALL,
            project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.reho_computed is True
        assert result.reho_status == "numerically_computed", (
            f"Expected numerically_computed, got {result.reho_status}"
        )
        # Validation status: property of the algorithm, independent of run success
        assert result.reho_validation_status == "golden_validated"
        assert result.reho_backend == "cpu-numpy"

    def test_zero_subjects_use_metadata_only(self, tmp_path, monkeypatch):
        """All ReHo subjects fail → execution status = metadata_only.
        Validation status remains golden_validated (algorithm property)."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup(tmp_path, monkeypatch)
        func_dir = tmp_path / "func"
        func_dir.mkdir()
        for i in range(1, 6):
            _make_bold(func_dir, subject=f"sub-{i:03d}")
        _make_dry_run(tmp_path)

        # Mock ReHo kernel to fail for all subjects
        def mock_fail(*a, **kw):
            return {"ok": False, "errors": ["mocked failure"]}

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_backend",
            mock_fail,
        )

        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test",
            functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj",
            "pp-test",
            req,
            env=_ALL,
            project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.reho_computed is False
        assert result.reho_status == "metadata_only", (
            f"Expected metadata_only when 0 succeed, got {result.reho_status}"
        )
        # Backend was never successfully used
        assert result.reho_backend == "none"
        # Validation status is a property of the configured algorithm,
        # not of this run's outcome. The CPU ReHo implementation IS golden-validated.
        assert result.reho_validation_status == "golden_validated", (
            "Validation status must be 'golden_validated' even when all subjects fail: "
            "it describes the algorithm, not the run outcome."
        )

    def test_partial_subjects_use_partially_computed(self, tmp_path, monkeypatch):
        """Some ReHo subjects succeed, some fail → execution status = partially_computed."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup(tmp_path, monkeypatch)
        func_dir = tmp_path / "func"
        func_dir.mkdir()
        for i in range(1, 6):
            _make_bold(func_dir, subject=f"sub-{i:03d}")
        _make_dry_run(tmp_path)

        # Alternating mock: first 2 succeed, rest fail
        calls = 0

        def mock_partial(*a, **kw):
            nonlocal calls
            calls += 1
            if calls <= 2:
                return {
                    "ok": True,
                    "backend": "cpu-numpy",
                    "reho": np.zeros((8, 8, 8), dtype=np.float32),
                    "valid_voxel_count": 100,
                    "skipped_voxel_count": 0,
                    "warnings": [],
                    "errors": [],
                    "runtime_seconds": 0.1,
                }
            return {"ok": False, "errors": ["mock failure"]}

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_backend",
            mock_partial,
        )

        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test",
            functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj",
            "pp-test",
            req,
            env=_ALL,
            project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.reho_computed is True, (
            "reho_computed should be True when at least one subject succeeds"
        )
        assert result.reho_status == "partially_computed", (
            f"Expected partially_computed (2/5 succeed), got {result.reho_status}"
        )
        assert result.reho_validation_status == "golden_validated"
        assert result.reho_backend == "cpu-numpy"

    def test_validation_status_independent_of_runtime_success(self, tmp_path, monkeypatch):
        """Validation status is always 'golden_validated' even when all ReHo fail.
        The validation level describes the algorithm, not this run's artifacts."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup(tmp_path, monkeypatch)
        func_dir = tmp_path / "func"
        func_dir.mkdir()
        _make_bold(func_dir, subject="sub-001")
        _make_dry_run(tmp_path)

        def mock_fail(*a, **kw):
            return {"ok": False, "errors": ["mock"]}

        monkeypatch.setattr(
            "src.backend.app.tools.reho_compute.compute_reho_backend",
            mock_fail,
        )

        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test",
            functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj",
            "pp-test",
            req,
            env=_ALL,
            project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.reho_computed is False
        assert result.reho_status == "metadata_only"
        # The key assertion: validation status is independent of runtime outcome
        assert result.reho_validation_status == "golden_validated", (
            "reho_validation_status must be 'golden_validated' regardless of "
            "whether this run succeeded. It describes the algorithm implementation, "
            "not the runtime outcome."
        )
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
        func_dir = tmp_path / "func"
        func_dir.mkdir()
        _make_bold(func_dir, subject="sub-001")
        _make_dry_run(tmp_path)
        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-test",
            functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj",
            "pp-test",
            req,
            env=_ALL,
            project_dir=str(tmp_path),
        )
        assert result.ok

        mf = json.loads(Path(result.manifest_path).read_text())
        reho = mf["reho"]
        assert reho["computed"] is True
        # Execution status: what this run produced
        assert reho["execution_status"] == "numerically_computed", (
            f"Expected numerically_computed in manifest, got {reho.get('execution_status')}"
        )
        # Validation status: scientific confidence level of the implementation
        assert reho["validation_status"] == "golden_validated"
        assert reho["backend"] == "cpu-numpy"
        assert "external_reference_validated" in reho
        assert reho["external_reference_validated"] is False
        assert "gpu_validated" in reho
        assert reho["gpu_validated"] is False
        # Old key "status" should NOT exist
        assert "status" not in reho, "Legacy 'status' key should not exist in manifest.reho"
