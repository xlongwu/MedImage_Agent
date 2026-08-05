from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from src.backend.app.native_preproc.io.dicom_to_nifti import (
    NativeDicomConversionError,
    convert_dicom_series,
)

pytest.importorskip("pydicom")
pytest.importorskip("nibabel")


def _write_classic_series(
    root: Path, *, positions: tuple[float, ...] = (-5.0, 0.0, 5.0)
) -> list[Path]:
    import pydicom
    from pydicom.dataset import FileDataset, FileMetaDataset

    root.mkdir(parents=True, exist_ok=True)
    series_uid = pydicom.uid.generate_uid()
    study_uid = pydicom.uid.generate_uid()
    paths: list[Path] = []
    # Deliberately reverse filenames relative to spatial order.
    for index, z_position in enumerate(reversed(positions), start=1):
        sop_uid = pydicom.uid.generate_uid()
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = pydicom.uid.MRImageStorage
        file_meta.MediaStorageSOPInstanceUID = sop_uid
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        path = root / f"image_{index:03d}.dcm"
        dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
        dataset.SOPClassUID = pydicom.uid.MRImageStorage
        dataset.SOPInstanceUID = sop_uid
        dataset.StudyInstanceUID = study_uid
        dataset.SeriesInstanceUID = series_uid
        dataset.Modality = "MR"
        dataset.Manufacturer = "SYNTHETIC"
        dataset.SeriesDescription = "Synthetic structural"
        dataset.InstanceNumber = index
        dataset.Rows = 4
        dataset.Columns = 5
        dataset.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        dataset.ImagePositionPatient = [10, 20, z_position]
        dataset.PixelSpacing = [2, 3]
        dataset.SliceThickness = 5
        dataset.SamplesPerPixel = 1
        dataset.PhotometricInterpretation = "MONOCHROME2"
        dataset.BitsAllocated = 16
        dataset.BitsStored = 16
        dataset.HighBit = 15
        dataset.PixelRepresentation = 0
        value = int(z_position + 20)
        dataset.PixelData = np.full((4, 5), value, dtype=np.uint16).tobytes()
        dataset.save_as(str(path), enforce_file_format=True)
        paths.append(path)
    return paths


def _fingerprint(paths: list[Path]) -> list[tuple[str, int, int]]:
    return [
        (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in paths
    ]


def test_native_classic_conversion_persists_reloadable_artifacts_without_touching_source(
    tmp_path: Path,
) -> None:
    import nibabel as nib

    source_paths = _write_classic_series(tmp_path / "raw")
    before = _fingerprint(source_paths)
    output = tmp_path / "project" / "converted_bids" / "sub-001" / "anat" / "sub-001_T1w.nii.gz"

    result = convert_dicom_series(
        tmp_path / "raw",
        output,
        subject_id="sub-001",
        modality="anat",
    )

    assert _fingerprint(source_paths) == before
    assert result.series_kind == "classic_single_frame_3d"
    assert result.shape == (4, 5, 3)
    image = nib.load(str(output))
    data = np.asarray(image.dataobj)
    assert image.shape == (4, 5, 3)
    assert str(image.get_data_dtype()) == "float32"
    np.testing.assert_array_equal(data[0, 0, :], np.array([15, 20, 25], dtype=np.float32))
    np.testing.assert_allclose(
        image.affine,
        np.array(
            [
                [0, -3, 0, -10],
                [-2, 0, 0, -20],
                [0, 0, 5, -5],
                [0, 0, 0, 1],
            ],
            dtype=float,
        ),
    )
    sidecar = json.loads(output.with_name("sub-001_T1w.json").read_text(encoding="utf-8"))
    assert sidecar["CapabilityLevel"] == "computed"
    assert sidecar["AlgorithmID"] == "medimage.native_dicom_to_nifti"
    assert sidecar["SourceFileCount"] == 3
    assert sidecar["OutputSHA256"] == result.output_sha256
    assert str(tmp_path / "raw") not in json.dumps(sidecar)


def test_native_conversion_refuses_overwrite(tmp_path: Path) -> None:
    _write_classic_series(tmp_path / "raw")
    output = tmp_path / "out" / "image.nii.gz"
    convert_dicom_series(tmp_path / "raw", output)

    with pytest.raises(NativeDicomConversionError, match="overwrite"):
        convert_dicom_series(tmp_path / "raw", output)


def test_native_conversion_rejects_mixed_series(tmp_path: Path) -> None:
    paths = _write_classic_series(tmp_path / "raw")
    import pydicom

    dataset = pydicom.dcmread(str(paths[-1]))
    dataset.SeriesInstanceUID = pydicom.uid.generate_uid()
    dataset.save_as(str(paths[-1]), enforce_file_format=True)

    with pytest.raises(NativeDicomConversionError, match="Mixed DICOM series"):
        convert_dicom_series(tmp_path / "raw", tmp_path / "out" / "image.nii.gz")


def test_native_conversion_rejects_repeated_classic_slice_positions(tmp_path: Path) -> None:
    _write_classic_series(tmp_path / "raw", positions=(0.0, 0.0))

    with pytest.raises(NativeDicomConversionError, match="Repeated classic slice positions"):
        convert_dicom_series(tmp_path / "raw", tmp_path / "out" / "image.nii.gz")
