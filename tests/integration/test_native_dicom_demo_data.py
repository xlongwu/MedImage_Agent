from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
import pytest

from src.backend.app.native_preproc.io.dicom_to_nifti import convert_dicom_series

pytest.importorskip("pydicom")
pytest.importorskip("nibabel")


def _digest_tree(root: Path) -> list[tuple[str, str, int, int]]:
    result: list[tuple[str, str, int, int]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        result.append(
            (
                str(path.relative_to(root)),
                hashlib.sha256(path.read_bytes()).hexdigest(),
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
        )
    return result


@pytest.mark.integration
def test_native_converter_on_one_demo_subject_read_only(tmp_path: Path) -> None:
    import nibabel as nib
    import pydicom
    from nibabel.nicom.dicomwrappers import wrapper_from_data

    demo_root_value = os.environ.get("MEDIMAGE_DEMO_DATA_DIR", "")
    if not demo_root_value:
        pytest.skip("MEDIMAGE_DEMO_DATA_DIR is not configured")
    demo_root = Path(demo_root_value)
    func_root = demo_root / "FunRaw" / "Sub_001"
    anat_root = demo_root / "T1Raw" / "Sub_001"
    if not func_root.exists() or not anat_root.exists():
        pytest.skip("DemoData Sub_001 FunRaw/T1Raw layout is unavailable")

    before_func = _digest_tree(func_root)
    before_anat = _digest_tree(anat_root)
    func_output = tmp_path / "converted_bids" / "sub-001" / "func" / "sub-001_task-rest_bold.nii.gz"
    anat_output = tmp_path / "converted_bids" / "sub-001" / "anat" / "sub-001_T1w.nii.gz"

    func_result = convert_dicom_series(
        func_root, func_output, subject_id="sub-001", modality="func"
    )
    anat_result = convert_dicom_series(
        anat_root, anat_output, subject_id="sub-001", modality="anat"
    )

    assert _digest_tree(func_root) == before_func
    assert _digest_tree(anat_root) == before_anat
    assert func_result.series_kind == "siemens_mosaic_4d"
    assert func_result.shape == (64, 64, 33, 240)
    assert anat_result.series_kind == "classic_single_frame_3d"
    assert anat_result.shape == (256, 256, 128)
    assert nib.load(str(func_output)).header.get_zooms()[3] == pytest.approx(2.0)

    first_func_path = sorted(path for path in func_root.rglob("*") if path.is_file())[0]
    reference = np.asarray(
        wrapper_from_data(pydicom.dcmread(str(first_func_path))).get_data(), dtype=np.float32
    )
    converted = np.asarray(nib.load(str(func_output)).dataobj[..., 0], dtype=np.float32)
    np.testing.assert_allclose(converted, reference, atol=0.0, rtol=0.0)
