from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from src.backend.app.tools.slice_timing_qc import (
    build_slice_timing_parameters,
    find_bids_sidecar_for_bold,
)


def test_find_bids_sidecar_for_bold(tmp_path: Path):
    bold = tmp_path / "sub-001_task-rest_bold.nii.gz"
    sidecar = tmp_path / "sub-001_task-rest_bold.json"

    bold.write_bytes(b"fake")
    sidecar.write_text("{}", encoding="utf-8")

    assert find_bids_sidecar_for_bold(str(bold)) == str(sidecar)


def test_build_slice_timing_parameters_from_bids_sidecar(tmp_path: Path):
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func"
    raw.mkdir(parents=True)

    bold = raw / "sub-001_task-rest_bold.nii.gz"
    sidecar = raw / "sub-001_task-rest_bold.json"
    prepared = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func" / "sub-001_bold.nii"
    prepared.parent.mkdir(parents=True)

    data = np.zeros((4, 4, 4, 5), dtype=np.float32)
    img = nib.Nifti1Image(data, affine=np.eye(4))
    nib.save(img, str(prepared))
    nib.save(img, str(bold))

    sidecar.write_text(
        json.dumps({
            "TaskName": "rest",
            "RepetitionTime": 2.0,
            "SliceTiming": [0.0, 1.0, 0.5, 1.5],
        }),
        encoding="utf-8",
    )

    params = build_slice_timing_parameters(
        input_bold=str(bold),
        prepared_nii=str(prepared),
    )

    assert params["ok"] is True
    assert params["nslices"] == 4
    assert params["frames_total"] == 5
    assert params["tr"] == 2.0
    assert params["slice_order"] == [1, 3, 2, 4]
    assert params["reference_slice"] in {2, 3}
