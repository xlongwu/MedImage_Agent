from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from src.backend.app.tools.atlas_io import AtlasValidationError, load_atlas_for_bold


def _bold_img(shape=(4, 4, 3, 8), affine=None):
    affine = np.eye(4) if affine is None else affine
    data = np.zeros(shape, dtype=np.float32)
    return nib.Nifti1Image(data, affine)


def test_load_atlas_for_bold_reads_labels_and_checksum(tmp_path: Path):
    bold = _bold_img()
    atlas = np.zeros((4, 4, 3), dtype=np.int16)
    atlas[:2, :, :] = 1
    atlas[2:, :, :] = 2
    atlas_path = tmp_path / "atlas.nii.gz"
    nib.save(nib.Nifti1Image(atlas, np.eye(4)), str(atlas_path))
    labels_path = tmp_path / "labels.tsv"
    labels_path.write_text("label\tname\n1\tFrontal\n2\tTemporal\n", encoding="utf-8")

    result = load_atlas_for_bold(atlas_path=atlas_path, bold_img=bold, labels_path=labels_path)

    assert result["label_count"] == 2
    assert result["roi_definitions"][0]["name"] == "Frontal"
    assert result["checksum"]
    assert result["shape"] == [4, 4, 3]


def test_load_atlas_for_bold_rejects_shape_mismatch(tmp_path: Path):
    bold = _bold_img()
    atlas_path = tmp_path / "atlas_bad_shape.nii.gz"
    nib.save(nib.Nifti1Image(np.ones((3, 4, 3), dtype=np.int16), np.eye(4)), str(atlas_path))

    with pytest.raises(AtlasValidationError, match="shape"):
        load_atlas_for_bold(atlas_path=atlas_path, bold_img=bold)


def test_load_atlas_for_bold_rejects_non_integer_labels(tmp_path: Path):
    bold = _bold_img()
    atlas = np.ones((4, 4, 3), dtype=np.float32)
    atlas[0, 0, 0] = 1.25
    atlas_path = tmp_path / "atlas_float.nii.gz"
    nib.save(nib.Nifti1Image(atlas, np.eye(4)), str(atlas_path))

    with pytest.raises(AtlasValidationError, match="integer"):
        load_atlas_for_bold(atlas_path=atlas_path, bold_img=bold)


def test_load_atlas_for_bold_reads_json_labels(tmp_path: Path):
    bold = _bold_img()
    atlas = np.ones((4, 4, 3), dtype=np.int16)
    atlas_path = tmp_path / "atlas.nii"
    labels_path = tmp_path / "labels.json"
    nib.save(nib.Nifti1Image(atlas, np.eye(4)), str(atlas_path))
    labels_path.write_text(json.dumps({"labels": [{"label": 1, "name": "One"}]}), encoding="utf-8")

    result = load_atlas_for_bold(atlas_path=atlas_path, bold_img=bold, labels_path=labels_path)

    assert result["roi_definitions"] == [{"label": 1, "name": "One", "strategy": "provided_atlas"}]
