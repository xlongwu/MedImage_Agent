from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.orchestrator.validation import validate_stage_result_artifacts
from src.backend.app.native_preproc.stages.reho import run_reho


def _save(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), np.eye(4)), str(path))
    return path


def test_reho_outputs_kendall_w_map_for_synchronized_neighborhood(tmp_path: Path) -> None:
    timepoints = 10
    base = np.linspace(-1.0, 1.0, timepoints, dtype=np.float32)
    data = np.zeros((5, 5, 5, timepoints), dtype=np.float32)
    data[1:4, 1:4, 1:4, :] = base
    bold = _save(tmp_path / "sub-01_desc-filtered_bold.nii.gz", data)

    result = run_reho(bold, tmp_path / "native", neighborhood=27)

    assert result.status == "succeeded"
    assert result.capability_level == "numerically_implemented"
    assert validate_stage_result_artifacts(result) == []
    output = np.asanyarray(nib.load(result.output_artifacts[0].path).dataobj)
    assert output.shape == data.shape[:3]
    assert output[2, 2, 2] > 0.99
    assert result.qc.metrics["kendall_w_ties_handling"] == "average_ranks_with_tie_correction"


def test_reho_blocks_invalid_neighborhood(tmp_path: Path) -> None:
    bold = _save(tmp_path / "bold.nii.gz", np.zeros((5, 5, 5, 8), dtype=np.float32))

    result = run_reho(bold, tmp_path / "native", neighborhood=9)

    assert result.status == "blocked"
    assert "7, 19, or 27" in result.errors[0]
