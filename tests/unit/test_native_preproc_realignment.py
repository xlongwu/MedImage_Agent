from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")
pytest.importorskip("scipy")

from scipy.ndimage import rotate, shift

from src.backend.app.native_preproc.stages.realignment import run_realignment


def _phantom(shape: tuple[int, int, int] = (9, 9, 9)) -> np.ndarray:
    coords = np.indices(shape, dtype=np.float32)
    center = np.asarray([(size - 1) / 2 for size in shape], dtype=np.float32).reshape((3, 1, 1, 1))
    squared = np.sum((coords - center) ** 2, axis=0)
    return np.exp(-squared / (2.0 * 1.2**2)).astype(np.float32)


def _save_bold(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4)), str(path))
    return path


def _artifact_path(result, artifact_type: str) -> Path:
    return Path(next(artifact.path for artifact in result.output_artifacts if artifact.artifact_type == artifact_type))


def test_translation_only_realignment_improves_known_shift_and_writes_outputs(tmp_path: Path) -> None:
    ref = _phantom()
    moved = shift(ref, shift=(1.0, 0.0, 0.0), order=1, mode="nearest")
    data = np.stack([ref, moved], axis=3)
    bold = _save_bold(tmp_path / "sub-01_task-rest_bold.nii.gz", data)

    result = run_realignment(bold, tmp_path / "native")

    assert result.status == "simplified"
    assert result.capability_level == "simplified"
    assert "translation_only_v1_no_rotation_estimation" in result.warnings
    realigned = np.asanyarray(nib.load(_artifact_path(result, "bold_4d")).dataobj)
    before_mse = float(np.mean((moved - ref) ** 2))
    after_mse = float(np.mean((realigned[..., 1] - ref) ** 2))
    assert after_mse < before_mse

    motion_path = _artifact_path(result, "motion_parameters")
    motion_lines = motion_path.read_text(encoding="utf-8").splitlines()
    assert len(motion_lines) == 3
    transforms = np.load(_artifact_path(result, "transform_matrix"))
    assert transforms.shape == (2, 4, 4)
    assert _artifact_path(result, "mean_functional").exists()
    assert result.qc.metrics["transform_matrix_count"] == 2


def test_rotation_phantom_is_not_misreported_as_6dof(tmp_path: Path) -> None:
    ref = _phantom()
    rotated = rotate(ref, angle=12.0, axes=(0, 1), reshape=False, order=1, mode="nearest")
    bold = _save_bold(tmp_path / "sub-01_task-rest_bold.nii.gz", np.stack([ref, rotated], axis=3))

    result = run_realignment(bold, tmp_path / "native")

    assert result.status == "simplified"
    assert result.parameters["model"] == "translation_only_v1"
    motion_path = _artifact_path(result, "motion_parameters")
    rows = motion_path.read_text(encoding="utf-8").splitlines()[1:]
    rotations = [[float(value) for value in row.split("\t")[3:6]] for row in rows]
    assert rotations == [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
