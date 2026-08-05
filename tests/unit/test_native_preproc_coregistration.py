from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")
pytest.importorskip("scipy")

from scipy.ndimage import shift  # noqa: E402

from src.backend.app.native_preproc.orchestrator.validation import (  # noqa: E402
    validate_stage_result_artifacts,  # noqa: E402
)
from src.backend.app.native_preproc.stages.coregistration import run_coregistration  # noqa: E402


def _phantom(shape: tuple[int, int, int] = (9, 9, 9)) -> np.ndarray:
    coords = np.indices(shape, dtype=np.float32)
    center = np.asarray([(size - 1) / 2 for size in shape], dtype=np.float32).reshape((3, 1, 1, 1))
    squared = np.sum((coords - center) ** 2, axis=0)
    return np.exp(-squared / (2.0 * 1.1**2)).astype(np.float32)


def _save(path: Path, data: np.ndarray, affine: np.ndarray | None = None) -> Path:
    nib.save(
        nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4) if affine is None else affine),
        str(path),
    )
    return path


def _artifact_path(result, artifact_type: str) -> Path:
    return Path(
        next(
            artifact.path
            for artifact in result.output_artifacts
            if artifact.artifact_type == artifact_type
        )
    )


def test_coregistration_improves_known_translation_and_writes_transform(tmp_path: Path) -> None:
    mean = _phantom()
    t1 = shift(mean, shift=(1.0, 0.0, 0.0), order=1, mode="constant", cval=0.0)
    mean_path = _save(tmp_path / "sub-01_desc-mean_bold.nii.gz", mean)
    t1_path = _save(tmp_path / "sub-01_T1w.nii.gz", t1)

    result = run_coregistration(mean_path, t1_path, tmp_path / "native")

    assert result.status == "simplified"
    assert result.capability_level == "simplified"
    assert "translation_only_affine_v1_not_spm_coregister_equivalent" in result.warnings
    assert validate_stage_result_artifacts(result) == []
    coregistered = np.asanyarray(nib.load(_artifact_path(result, "t1w")).dataobj)
    before_mse = float(np.mean((t1 - mean) ** 2))
    after_mse = float(np.mean((coregistered - mean) ** 2))
    assert after_mse < before_mse
    assert result.qc.metrics["nmi_after"] >= result.qc.metrics["nmi_before"]
    transform = np.load(_artifact_path(result, "transform_matrix"))
    assert transform.shape == (4, 4)
    assert not np.allclose(transform, np.eye(4))


def test_coregistration_blocks_empty_images_without_success(tmp_path: Path) -> None:
    mean_path = _save(
        tmp_path / "sub-01_desc-mean_bold.nii.gz", np.zeros((5, 5, 5), dtype=np.float32)
    )
    t1_path = _save(tmp_path / "sub-01_T1w.nii.gz", np.zeros((5, 5, 5), dtype=np.float32))

    result = run_coregistration(mean_path, t1_path, tmp_path / "native")

    assert result.status == "blocked"
    assert result.output_artifacts == []
    assert "center of mass" in result.errors[0]
