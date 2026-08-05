"""Synthetic DICOM test helpers — Phase 4C-1.

Creates minimal valid DICOM files using pydicom for smoke testing
dcm2niix conversion without touching real rawdata.

No patient-identifying data.  Deterministic metadata.  All files are
created under the provided ``root`` path (typically pytest ``tmp_path``).

Tests that require these helpers should skip if pydicom is not installed.
"""

from __future__ import annotations

from pathlib import Path


def pydicom_available() -> bool:
    """Return True if pydicom can be imported."""
    try:
        import pydicom  # noqa: F401

        return True
    except ImportError:
        return False


def create_minimal_dicom_series(
    root: Path,
    subject_id: str = "sub-001",
    series_name: str = "synthetic",
    series_description: str = "Synthetic BOLD",
    modality: str = "MR",
    num_slices: int = 3,
    slice_size: int = 16,
) -> Path:
    """Create a tiny valid DICOM series under *root* for smoke testing.

    Returns the path to the series directory containing the DICOM files.

    Requires ``pydicom``.  Raises ``ImportError`` if unavailable.
    """
    import numpy as np
    import pydicom
    from pydicom.dataset import FileDataset, FileMetaDataset

    series_dir = root / series_name
    series_dir.mkdir(parents=True, exist_ok=True)

    for slice_idx in range(num_slices):
        # Create a minimal DICOM dataset
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

        ds = FileDataset(
            str(series_dir / f"slice_{slice_idx:03d}.dcm"),
            {},
            file_meta=file_meta,
            preamble=b"\0" * 128,
        )

        ds.PatientName = "Synthetic"
        ds.PatientID = f"{subject_id}_synth"
        ds.Modality = modality
        ds.SeriesDescription = series_description
        ds.StudyInstanceUID = pydicom.uid.generate_uid()
        ds.SeriesInstanceUID = pydicom.uid.generate_uid()
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.InstanceNumber = slice_idx + 1
        ds.SliceLocation = float(slice_idx)
        ds.Rows = slice_size
        ds.Columns = slice_size
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1

        # Create a tiny synthetic image with a gradient
        pixel_data = np.arange(slice_size * slice_size, dtype=np.uint16).reshape(
            slice_size, slice_size
        ) + (slice_idx * 256)
        ds.PixelData = pixel_data.tobytes()

        ds.save_as(str(series_dir / f"slice_{slice_idx:03d}.dcm"))

    return series_dir


def create_synthetic_funraw_layout(
    root: Path,
    subject_count: int = 1,
) -> dict[str, Path]:
    """Create a minimal FunRaw/T1Raw-style DICOM layout under *root*.

    Returns a dict with keys ``"FunRaw"`` and ``"T1Raw"`` mapping to
    the created directory paths.
    """
    funraw_dir = root / "FunRaw"
    t1raw_dir = root / "T1Raw"

    result: dict[str, Path] = {}

    for i in range(1, subject_count + 1):
        subj = f"Sub_{i:03d}"
        result[f"FunRaw_{subj}"] = create_minimal_dicom_series(
            funraw_dir / subj,
            subject_id=f"sub-{i:03d}",
            series_name="functional",
            series_description="Synthetic BOLD",
        )

    for i in range(1, subject_count + 1):
        subj = f"Sub_{i:03d}"
        result[f"T1Raw_{subj}"] = create_minimal_dicom_series(
            t1raw_dir / subj,
            subject_id=f"sub-{i:03d}",
            series_name="structural",
            series_description="Synthetic T1w",
        )

    return result
