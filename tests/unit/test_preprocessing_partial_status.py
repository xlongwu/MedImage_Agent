"""Regression tests for partial/preview status in ALFF/ReHo and FC sandbox execution.

Ensures that:
- ALFF/ReHo only returns 'partial' for an explicit preview_limit.
- FC returns 'partial' when some selected files fail to produce matrices.
"""
from __future__ import annotations
from pathlib import Path
import json, pytest
import numpy as np
import nibabel as nib


# ── ALFF/ReHo helpers ──

_ALL_AR = {"MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_ALFF_REHO": "1"}

def _setup_ar(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db_ar.sqlite")
    monkeypatch.setattr(
        "src.backend.app.services.preprocessing_alff_reho_execution.mock_store", store,
    )
    return store


def _make_synth_bold_ar(func_dir, subject="sub-001", tr=2.0, with_sidecar=True):
    """Create a synthetic 4D BOLD NIfTI for ALFF/ReHo testing."""
    sub_dir = func_dir / subject / "func"
    sub_dir.mkdir(parents=True)
    data = np.random.default_rng(42).random((8, 8, 8, 120)).astype(np.float32)
    img = nib.Nifti1Image(data, np.eye(4))
    nii_path = sub_dir / f"{subject}_task-rest_bold.nii.gz"
    nib.save(img, str(nii_path))
    if with_sidecar:
        (sub_dir / f"{subject}_task-rest_bold.json").write_text(
            json.dumps({"RepetitionTime": tr, "TaskName": "rest"})
        )
    return nii_path


def _make_dry_run_ar(tmp_path, run_id="pp-test", dry_id="dr-synth"):
    dd = tmp_path / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id
    dd.mkdir(parents=True)
    (dd / "alff_reho_dry_run_manifest.json").write_text(
        json.dumps({"status": "dry_run_preview", "files": []})
    )


class TestAlffRehoPartialStatus:
    """ALFF/ReHo: explicit preview mode returns 'partial'."""

    def test_more_than_10_files_default_processes_all_and_succeeds(self, tmp_path, monkeypatch):
        """Processing >10 discovered BOLD files defaults to full dataset."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup_ar(tmp_path, monkeypatch)
        func_dir = tmp_path / "func_input"
        func_dir.mkdir()

        # Create 15 subjects. ALFF/ReHo no longer defaults to first-10 preview.
        for i in range(1, 16):
            _make_synth_bold_ar(func_dir, subject=f"sub-{i:03d}", tr=2.0, with_sidecar=True)

        _make_dry_run_ar(tmp_path)
        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-synth", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj", "pp-test", req, env=_ALL_AR, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.status == "succeeded", \
            f"Expected succeeded for default full-dataset ALFF/ReHo, got {result.status}: {result.warnings}"
        assert result.files_discovered == 15
        assert result.files_selected == 15
        assert result.dataset_complete

    def test_explicit_preview_limit_returns_partial(self, tmp_path, monkeypatch):
        """Explicit preview_limit < discovered files → status='partial'."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup_ar(tmp_path, monkeypatch)
        func_dir = tmp_path / "func_input"
        func_dir.mkdir()

        for i in range(1, 16):
            _make_synth_bold_ar(func_dir, subject=f"sub-{i:03d}", tr=2.0, with_sidecar=True)

        _make_dry_run_ar(tmp_path)
        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-synth", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True, preview_limit=10,
        )
        result = run_alff_reho_sandbox_execution(
            "proj", "pp-test", req, env=_ALL_AR, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.status == "partial", \
            f"Expected partial for explicit preview limit, got {result.status}: {result.warnings}"
        assert result.files_discovered == 15
        assert result.files_selected == 10
        assert not result.dataset_complete
        preview_warnings = [w for w in result.warnings if "preview" in w.lower()
                           or "only" in w.lower()]
        assert len(preview_warnings) >= 1, \
            f"Expected explicit preview warning, got warnings: {result.warnings}"

    def test_10_or_fewer_files_all_succeed_returns_succeeded(self, tmp_path, monkeypatch):
        """10 or fewer files with all metrics succeeding → status='succeeded'."""
        from src.backend.app.schemas.preprocessing_alff_reho_execution import (
            AlffRehoSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_alff_reho_execution import (
            run_alff_reho_sandbox_execution,
        )

        _setup_ar(tmp_path, monkeypatch)
        func_dir = tmp_path / "func_input"
        func_dir.mkdir()

        for i in range(1, 4):
            _make_synth_bold_ar(func_dir, subject=f"sub-{i:03d}", tr=2.0, with_sidecar=True)

        _make_dry_run_ar(tmp_path)
        req = AlffRehoSandboxExecutionRequest(
            dry_run_id="dr-synth", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_alff_reho_sandbox_execution(
            "proj", "pp-test", req, env=_ALL_AR, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.status == "succeeded", \
            f"Expected succeeded for 3 files, got {result.status}: {result.warnings}"
        assert result.dataset_complete
        assert result.files_discovered == 3
        assert result.files_selected == 3


# ── FC helpers ──

_ALL_FC = {"MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_FC": "1"}

def _setup_fc(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db_fc.sqlite")
    monkeypatch.setattr(
        "src.backend.app.services.preprocessing_fc_execution.mock_store", store,
    )
    return store


def _make_synth_bold_fc(func_dir, subject="sub-001", shape=(10, 10, 10, 80)):
    """Create a synthetic 4D BOLD NIfTI for FC testing."""
    sub_dir = func_dir / subject / "func"
    sub_dir.mkdir(parents=True)
    data = np.random.default_rng(99).random(shape).astype(np.float32)
    img = nib.Nifti1Image(data, np.eye(4))
    nii_path = sub_dir / f"{subject}_task-rest_bold.nii.gz"
    nib.save(img, str(nii_path))
    return nii_path


def _make_dry_run_fc(tmp_path, run_id="pp-test", dry_id="dr-fc"):
    dd = tmp_path / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id
    dd.mkdir(parents=True)
    (dd / "fc_dry_run_manifest.json").write_text(
        json.dumps({"status": "dry_run_preview", "files": []})
    )


class TestFcPartialStatus:
    """FC: preview mode and partial file failures return 'partial'."""

    def test_more_than_10_files_returns_partial(self, tmp_path, monkeypatch):
        """Processing >10 discovered BOLD files → status='partial' (preview)."""
        from src.backend.app.schemas.preprocessing_fc_execution import (
            FcSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_fc_execution import (
            run_fc_sandbox_execution,
        )

        _setup_fc(tmp_path, monkeypatch)
        func_dir = tmp_path / "func_input"
        func_dir.mkdir()

        for i in range(1, 16):
            _make_synth_bold_fc(func_dir, subject=f"sub-{i:03d}")

        _make_dry_run_fc(tmp_path)
        req = FcSandboxExecutionRequest(
            dry_run_id="dr-fc", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_fc_sandbox_execution(
            "proj", "pp-test", req, env=_ALL_FC, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.status == "partial", \
            f"Expected partial for >10 FC files, got {result.status}: {result.warnings}"
        assert result.files_discovered == 15
        assert result.files_selected == 10
        assert not result.dataset_complete

    def test_selected_file_failures_return_partial(self, tmp_path, monkeypatch):
        """Some selected files fail → status='partial' (not 'succeeded')."""
        from src.backend.app.schemas.preprocessing_fc_execution import (
            FcSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_fc_execution import (
            run_fc_sandbox_execution,
        )

        _setup_fc(tmp_path, monkeypatch)
        func_dir = tmp_path / "func_input"
        func_dir.mkdir()

        # Create 5 subjects; make subject 3 have too few timepoints (will fail)
        for i in range(1, 6):
            if i == 3:
                # Too few timepoints → skipped
                _make_synth_bold_fc(func_dir, subject=f"sub-{i:03d}", shape=(10, 10, 10, 5))
            else:
                _make_synth_bold_fc(func_dir, subject=f"sub-{i:03d}")

        _make_dry_run_fc(tmp_path)
        req = FcSandboxExecutionRequest(
            dry_run_id="dr-fc", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_fc_sandbox_execution(
            "proj", "pp-test", req, env=_ALL_FC, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.status == "partial", \
            f"Expected partial when some files fail, got {result.status}: {result.warnings}"
        assert result.subjects_succeeded == 4, \
            f"Expected 4 succeeded (sub-003 too few timepoints), got {result.subjects_succeeded}"
        assert result.subjects_failed == 1
        fail_warnings = [w for w in result.warnings if "too few timepoints" in w.lower()]
        assert len(fail_warnings) >= 1, \
            f"Expected timepoint warning, got: {result.warnings}"

    def test_all_files_succeed_returns_succeeded(self, tmp_path, monkeypatch):
        """All files succeed → status='succeeded'."""
        from src.backend.app.schemas.preprocessing_fc_execution import (
            FcSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_fc_execution import (
            run_fc_sandbox_execution,
        )

        _setup_fc(tmp_path, monkeypatch)
        func_dir = tmp_path / "func_input"
        func_dir.mkdir()

        for i in range(1, 4):
            _make_synth_bold_fc(func_dir, subject=f"sub-{i:03d}")

        _make_dry_run_fc(tmp_path)
        req = FcSandboxExecutionRequest(
            dry_run_id="dr-fc", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_fc_sandbox_execution(
            "proj", "pp-test", req, env=_ALL_FC, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.status == "succeeded", \
            f"Expected succeeded, got {result.status}: {result.warnings}"
        assert result.subjects_succeeded == 3
        assert result.subjects_failed == 0
        assert result.subjects_partial == 0

    def test_all_files_fail_returns_warning(self, tmp_path, monkeypatch):
        """All files fail → status='warning' (not 'partial' or 'succeeded')."""
        from src.backend.app.schemas.preprocessing_fc_execution import (
            FcSandboxExecutionRequest,
        )
        from src.backend.app.services.preprocessing_fc_execution import (
            run_fc_sandbox_execution,
        )

        _setup_fc(tmp_path, monkeypatch)
        func_dir = tmp_path / "func_input"
        func_dir.mkdir()

        # All subjects have too few timepoints
        for i in range(1, 4):
            _make_synth_bold_fc(func_dir, subject=f"sub-{i:03d}", shape=(10, 10, 10, 5))

        _make_dry_run_fc(tmp_path)
        req = FcSandboxExecutionRequest(
            dry_run_id="dr-fc", functional_input_dir=str(func_dir),
            confirm_sandbox_copy=True,
        )
        result = run_fc_sandbox_execution(
            "proj", "pp-test", req, env=_ALL_FC, project_dir=str(tmp_path),
        )
        assert result.ok
        assert result.status == "warning", \
            f"Expected warning when all fail, got {result.status}: {result.warnings}"
        assert result.subjects_succeeded == 0
        assert result.subjects_failed == 3
