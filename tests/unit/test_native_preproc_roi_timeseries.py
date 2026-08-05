from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.stages.roi_timeseries import run_roi_timeseries  # noqa: E402


def _save(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), np.eye(4)), str(path))
    return path


def test_roi_timeseries_outputs_tsv_labels_and_empty_roi_warning(tmp_path: Path) -> None:
    timepoints = 12
    times = np.linspace(0.0, 2.0 * np.pi, timepoints, dtype=np.float32)
    data = np.zeros((4, 4, 2, timepoints), dtype=np.float32)
    data[:2, :, :, :] = np.sin(times)
    data[2:, :, :, :] = np.cos(times)
    atlas = np.zeros((4, 4, 2), dtype=np.int16)
    atlas[:2, :, :] = 1
    atlas[2:, :, :] = 2
    bold_path = _save(tmp_path / "sub-01_desc-filtered_bold.nii.gz", data)
    atlas_path = _save(tmp_path / "atlas.nii.gz", atlas)
    labels_path = tmp_path / "atlas.tsv"
    labels_path.write_text("label\tname\n1\tSin\n2\tCos\n3\tEmpty\n", encoding="utf-8")

    result = run_roi_timeseries(
        bold_path,
        atlas_path,
        tmp_path / "native",
        labels_path=labels_path,
        atlas_name="custom_synthetic",
    )

    assert result.status == "warning"
    assert "roi_3_empty" in result.warnings
    tsv_path = Path(result.output_artifacts[0].path)
    lines = tsv_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t") == ["roi_1_Sin", "roi_2_Cos", "roi_3_Empty"]
    assert len(lines) == timepoints + 1
    assert result.output_artifacts[0].artifact_type == "roi_timeseries"
    assert result.output_artifacts[1].artifact_type == "roi_labels"
    assert result.qc.metrics["empty_roi_count"] == 1


def test_roi_timeseries_blocks_atlas_shape_mismatch(tmp_path: Path) -> None:
    bold = _save(tmp_path / "bold.nii.gz", np.zeros((2, 2, 2, 8), dtype=np.float32))
    atlas = _save(tmp_path / "atlas.nii.gz", np.ones((3, 2, 2), dtype=np.int16))

    result = run_roi_timeseries(bold, atlas, tmp_path / "native")

    assert result.status == "blocked"
    assert "atlas shape" in result.errors[0]
