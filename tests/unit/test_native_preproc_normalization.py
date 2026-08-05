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
from src.backend.app.native_preproc.stages.normalization import (  # noqa: E402
    run_affine_normalization,  # noqa: E402
)


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


def test_affine_normalization_resamples_bold_to_template_grid(tmp_path: Path) -> None:
    template = _phantom()
    subject_t1 = shift(template, shift=(1.0, 0.0, 0.0), order=1, mode="constant", cval=0.0)
    bold = np.stack([subject_t1, subject_t1 * 2.0], axis=3)
    template_path = _save(tmp_path / "synthetic_template.nii.gz", template)
    t1_path = _save(tmp_path / "sub-01_T1w.nii.gz", subject_t1)
    bold_path = _save(tmp_path / "sub-01_task-rest_bold.nii.gz", bold)

    result = run_affine_normalization(t1_path, bold_path, template_path, tmp_path / "native")

    assert result.status == "simplified"
    assert result.capability_level == "affine_only"
    assert "affine_only_no_nonlinear_deformation" in result.warnings
    assert validate_stage_result_artifacts(result) == []
    normalized = np.asanyarray(nib.load(_artifact_path(result, "normalized_bold")).dataobj)
    assert normalized.shape == template.shape + (2,)
    before_mse = float(np.mean((subject_t1 - template) ** 2))
    after_mse = float(np.mean((normalized[..., 0] - template) ** 2))
    assert after_mse < before_mse
    transform = np.load(_artifact_path(result, "transform_matrix"))
    assert transform.shape == (4, 4)
    assert result.qc.metrics["transform_invertible"] is True
    assert result.parameters["template_resource_policy"] == "caller_supplied_no_bundled_template"


def test_affine_normalization_resamples_tissue_probabilities_to_template_grid(
    tmp_path: Path,
) -> None:
    source_shape = (7, 7, 7)
    template_shape = (5, 6, 5)
    source_affine = np.diag([1.5, 1.5, 1.5, 1.0]).astype(np.float32)
    template_affine = np.diag([2.0, 2.0, 2.0, 1.0]).astype(np.float32)
    t1_data = _phantom(source_shape)
    bold_data = np.stack([t1_data, t1_data * 2.0], axis=3)
    tissue = np.clip(t1_data / float(np.max(t1_data)), 0.0, 1.0)

    template_path = _save(
        tmp_path / "synthetic_template.nii.gz",
        np.ones(template_shape, dtype=np.float32),
        template_affine,
    )
    t1_path = _save(tmp_path / "sub-01_T1w.nii.gz", t1_data, source_affine)
    bold_path = _save(tmp_path / "sub-01_task-rest_bold.nii.gz", bold_data, source_affine)
    wm_path = _save(tmp_path / "sub-01_desc-wm_probseg.nii.gz", tissue, source_affine)
    csf_path = _save(tmp_path / "sub-01_desc-csf_probseg.nii.gz", 1.0 - tissue, source_affine)

    result = run_affine_normalization(
        t1_path,
        bold_path,
        template_path,
        tmp_path / "native",
        wm_map=wm_path,
        csf_map=csf_path,
    )

    assert result.status == "simplified"
    for artifact_type in ("wm_map", "csf_map"):
        image = nib.load(_artifact_path(result, artifact_type))
        data = np.asanyarray(image.dataobj)
        assert data.shape == template_shape
        assert np.allclose(image.affine, template_affine)
        assert np.isfinite(data).all()
        assert float(np.min(data)) >= 0.0
        assert float(np.max(data)) <= 1.0
    assert result.qc.metrics["resampled_tissue_shapes"] == {
        "wm_map": list(template_shape),
        "csf_map": list(template_shape),
    }
    assert result.parameters["tissue_mask_interpolation"] == "nearest"


def test_affine_normalization_blocks_non_4d_bold(tmp_path: Path) -> None:
    template_path = _save(tmp_path / "synthetic_template.nii.gz", _phantom())
    t1_path = _save(tmp_path / "sub-01_T1w.nii.gz", _phantom())
    bold_path = _save(tmp_path / "sub-01_task-rest_bold.nii.gz", _phantom())

    result = run_affine_normalization(t1_path, bold_path, template_path, tmp_path / "native")

    assert result.status == "blocked"
    assert result.output_artifacts == []
    assert "requires 4D BOLD input" in result.errors[0]
