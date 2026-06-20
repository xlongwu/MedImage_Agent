"""Real-artifact regression tests for the scientific-credibility convergence.

These tests feed the ALFF/ReHo and FC sandbox execution services *real*
synthetic 4D BOLD NIfTI volumes (not the metadata-first text-file fixtures
used by the Phase 5M/5N contract tests) and assert that:

  * ALFF/fALFF/ReHo produce reloadable NIfTI maps via the unified kernels.
  * FC produces real reloadable ``.npy``/``.tsv`` correlation + Fisher-Z
    matrices (no shape-only descriptor JSON).
  * Each metric reports a per-metric status that distinguishes
    "sandbox prepared" from "numerically computed".
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest


def _make_synthetic_bold(path: Path, shape=(8, 8, 6, 40), seed=7) -> None:
    import nibabel as nib
    rng = np.random.default_rng(seed)
    data = rng.normal(500, 50, shape).astype(np.float32)
    # Add a low-frequency oscillation so ALFF band has power at 0.01-0.08 Hz.
    t = np.linspace(0, 2 * np.pi, shape[3]).reshape(1, 1, 1, -1)
    data = data + 80.0 * np.sin(0.1 * t)
    nib.save(nib.Nifti1Image(data.astype(np.float32), np.eye(4)), str(path))


def _setup_store(tmp_path, monkeypatch):
    from src.backend.app.services.mock_store import SQLiteDesktopStore
    store = SQLiteDesktopStore(tmp_path / "db.sqlite")
    monkeypatch.setattr(
        "src.backend.app.services.preprocessing_alff_reho_execution.mock_store", store)
    monkeypatch.setattr(
        "src.backend.app.services.preprocessing_fc_execution.mock_store", store)
    return store


_ALL_ALFF = {"MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
             "MEDIMAGE_ALLOW_SANDBOXED_ALFF_REHO": "1"}
_ALL_FC = {"MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1", "MEDIMAGE_ALLOW_SANDBOXED_FC": "1"}


def _prep_bold_input(tmp_path: Path) -> Path:
    func = tmp_path / "preprocessing_runs" / "pp-test" / "spm_exec" / "tf-ex" / "sandbox_output"
    sub = func / "sub-001"; sub.mkdir(parents=True)
    _make_synthetic_bold(sub / "filtered_sub-001_task-rest_bold.nii.gz")
    dd = tmp_path / "preprocessing_runs" / "pp-test" / "spm_dry_runs" / "dr-test"
    dd.mkdir(parents=True)
    (dd / "alff_reho_dry_run_manifest.json").write_text('{"status":"dry_run_preview"}')
    (dd / "fc_dry_run_manifest.json").write_text('{"status":"dry_run_preview"}')
    return func


# ── ALFF / fALFF / ReHo ──

def test_alff_reho_produces_real_nifti_maps(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    func_dir = _prep_bold_input(tmp_path)
    from src.backend.app.schemas.preprocessing_alff_reho_execution import (
        AlffRehoSandboxExecutionRequest)
    from src.backend.app.services.preprocessing_alff_reho_execution import (
        run_alff_reho_sandbox_execution)

    req = AlffRehoSandboxExecutionRequest(
        dry_run_id="dr-test", functional_input_dir=str(func_dir), confirm_sandbox_copy=True)
    res = run_alff_reho_sandbox_execution("brain-tumor-study", "pp-test", req,
                                          env=_ALL_ALFF, project_dir=str(tmp_path))

    assert res.ok, res.warnings
    assert res.alff_computed, f"ALFF not computed: {res.warnings}"
    assert res.falff_computed, "fALFF not computed alongside ALFF"
    assert res.alff_status == "numerically_computed"
    # ReHo connected (status reflects unvalidated kernel, not "not implemented").
    assert res.reho_computed, f"ReHo not computed: {res.warnings}"

    import nibabel as nib
    out_dir = Path(res.execution_dir) / "sandbox_output" / "sub-001"
    alff_img = nib.load(str(out_dir / "sub-001_desc-alff_map.nii.gz"))
    falff_img = nib.load(str(out_dir / "sub-001_desc-falff_map.nii.gz"))
    reho_img = nib.load(str(out_dir / "sub-001_desc-reho_map.nii.gz"))
    alff = alff_img.get_fdata()
    falff = falff_img.get_fdata()
    reho = reho_img.get_fdata()
    assert alff.shape == (8, 8, 6), alff.shape
    assert falff.shape == (8, 8, 6)
    assert reho.shape == (8, 8, 6)
    # fALFF is a ratio in [0, 1].
    assert np.nanmax(falff) <= 1.0 + 1e-5 and np.nanmin(falff) >= -1e-5
    assert np.all(np.isfinite(reho)), "ReHo map contains non-finite values"

    manifest = json.loads((Path(res.execution_dir) / "manifest.json").read_text())
    assert manifest["alff"]["status"] == "numerically_computed"
    assert manifest["reho"]["computed"] is True


# ── FC ──

def test_fc_produces_real_matrices(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch)
    func_dir = _prep_bold_input(tmp_path)
    from src.backend.app.schemas.preprocessing_fc_execution import FcSandboxExecutionRequest
    from src.backend.app.services.preprocessing_fc_execution import run_fc_sandbox_execution

    req = FcSandboxExecutionRequest(
        dry_run_id="dr-test", functional_input_dir=str(func_dir), confirm_sandbox_copy=True)
    res = run_fc_sandbox_execution("brain-tumor-study", "pp-test", req,
                                   env=_ALL_FC, project_dir=str(tmp_path))

    assert res.ok, res.warnings
    assert res.fc_computed, f"FC not computed: {res.warnings}"
    assert res.fc_status == "numerically_computed"
    assert res.fc_matrix_count == 1

    out_dir = Path(res.execution_dir) / "sandbox_output" / "sub-001"
    corr = np.load(out_dir / "sub-001_desc-fc_matrix.npy")
    fz = np.load(out_dir / "sub-001_desc-fisherz_matrix.npy")
    assert corr.ndim == 2 and corr.shape[0] == corr.shape[1], corr.shape
    assert corr.shape == fz.shape
    # Correlation: symmetric, diagonal 1, in [-1, 1].
    assert np.allclose(corr, corr.T, atol=1e-4)
    assert np.allclose(np.diag(corr), 1.0, atol=1e-4)
    assert corr.min() >= -1.0 - 1e-3 and corr.max() <= 1.0 + 1e-3
    # Fisher-Z diagonal is 0 by construction.
    assert np.allclose(np.diag(fz), 0.0, atol=1e-4)
    # TSV is human-readable and reloads to the same matrix.
    tsv = np.loadtxt(out_dir / "sub-001_desc-fc_matrix.tsv", delimiter="\t")
    assert np.allclose(tsv, corr, atol=1e-3)

    labels = json.loads((out_dir / "sub-001_desc-fc_labels.json").read_text())
    assert labels["roi_count"] == corr.shape[0]

    manifest = json.loads((Path(res.execution_dir) / "manifest.json").read_text())
    assert manifest["fc"]["computed"] is True
    assert manifest["fc"]["status"] == "numerically_computed"
