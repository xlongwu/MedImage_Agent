"""Native, fail-closed MR DICOM to NIfTI conversion.

The implementation intentionally supports a narrow, validated subset:

* classic single-frame MR slice series;
* Siemens single-frame mosaic MR time series.

Enhanced multi-frame DICOM, mixed series, repeated classic slice positions,
and vendor mosaics other than Siemens are rejected instead of being guessed.
No external executable is invoked and source files are opened read-only.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from src.backend.app.runtime.atomic_file import atomic_write_json


ALGORITHM_ID = "medimage.native_dicom_to_nifti"
ALGORITHM_VERSION = "1.0.0"
_LPS_TO_RAS = np.diag([-1.0, -1.0, 1.0, 1.0])


class NativeDicomConversionError(ValueError):
    """Raised when input is unsafe, inconsistent, or outside supported scope."""


@dataclass(frozen=True)
class NativeDicomConversionResult:
    nifti_path: str
    sidecar_path: str
    source_file_count: int
    source_fingerprint_sha256: str
    output_sha256: str
    series_instance_uid_sha256: str
    series_kind: str
    shape: tuple[int, ...]
    dtype: str
    zooms: tuple[float, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_dependencies() -> tuple[Any, Any]:
    try:
        import nibabel as nib
    except ImportError as exc:  # pragma: no cover - dependency probe
        raise RuntimeError("Missing optional dependency: nibabel is required for native DICOM conversion.") from exc
    try:
        import pydicom
    except ImportError as exc:  # pragma: no cover - dependency probe
        raise RuntimeError("Missing optional dependency: pydicom is required for native DICOM conversion.") from exc
    return nib, pydicom


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint(paths: Iterable[Path]) -> str:
    """Hash source content without persisting machine-specific paths."""

    digest = hashlib.sha256()
    for file_digest in sorted(_sha256_file(path) for path in paths):
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_mosaic(dataset: Any) -> bool:
    image_type = [str(item).upper() for item in getattr(dataset, "ImageType", [])]
    return "MOSAIC" in image_type or (0x0019, 0x100A) in dataset


def _read_datasets(input_dir: Path, pydicom: Any) -> tuple[list[Path], list[Any]]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise NativeDicomConversionError(f"DICOM input directory does not exist: {input_dir}")

    paths: list[Path] = []
    datasets: list[Any] = []
    for path in sorted((item for item in input_dir.rglob("*") if item.is_file()), key=lambda item: str(item).lower()):
        try:
            dataset = pydicom.dcmread(str(path), force=False)
        except Exception:
            continue
        if not getattr(dataset, "SeriesInstanceUID", None):
            continue
        paths.append(path)
        datasets.append(dataset)

    if not datasets:
        raise NativeDicomConversionError(f"No readable DICOM instances found under {input_dir}.")

    series_uids = {str(dataset.SeriesInstanceUID) for dataset in datasets}
    if len(series_uids) != 1:
        raise NativeDicomConversionError(
            f"Mixed DICOM series are not supported in one mapping; found {len(series_uids)} SeriesInstanceUID values."
        )
    modalities = {str(getattr(dataset, "Modality", "")).upper() for dataset in datasets}
    if modalities != {"MR"}:
        raise NativeDicomConversionError(f"Only MR DICOM is supported, found modalities: {sorted(modalities)}.")
    if any(int(getattr(dataset, "NumberOfFrames", 1) or 1) != 1 for dataset in datasets):
        raise NativeDicomConversionError("Enhanced or other multi-frame DICOM is not supported by the native converter.")
    return paths, datasets


def _scaled_pixels(dataset: Any) -> np.ndarray:
    try:
        pixels = np.asarray(dataset.pixel_array)
    except Exception as exc:
        transfer_syntax = str(getattr(getattr(dataset, "file_meta", None), "TransferSyntaxUID", "unknown"))
        raise NativeDicomConversionError(
            f"DICOM pixel data could not be decoded (TransferSyntaxUID={transfer_syntax}): {exc}"
        ) from exc
    slope = _safe_float(getattr(dataset, "RescaleSlope", 1.0), 1.0) or 1.0
    intercept = _safe_float(getattr(dataset, "RescaleIntercept", 0.0), 0.0) or 0.0
    return np.asarray(pixels, dtype=np.float32) * np.float32(slope) + np.float32(intercept)


def _classic_series(datasets: list[Any]) -> tuple[np.ndarray, np.ndarray, tuple[float, ...], list[str]]:
    first = datasets[0]
    try:
        orientation = np.asarray(first.ImageOrientationPatient, dtype=np.float64)
        origin = np.asarray(first.ImagePositionPatient, dtype=np.float64)
        pixel_spacing = np.asarray(first.PixelSpacing, dtype=np.float64)
    except Exception as exc:
        raise NativeDicomConversionError(
            "Classic MR conversion requires ImageOrientationPatient, ImagePositionPatient, and PixelSpacing."
        ) from exc
    if orientation.shape != (6,) or origin.shape != (3,) or pixel_spacing.shape != (2,):
        raise NativeDicomConversionError("Invalid classic MR geometry tag dimensions.")

    row_direction = orientation[:3]
    column_direction = orientation[3:]
    normal = np.cross(row_direction, column_direction)
    normal_norm = float(np.linalg.norm(normal))
    if normal_norm <= 1e-8:
        raise NativeDicomConversionError("ImageOrientationPatient defines a degenerate slice plane.")
    normal /= normal_norm

    positioned: list[tuple[float, Any, np.ndarray]] = []
    expected_shape: tuple[int, int] | None = None
    for dataset in datasets:
        try:
            current_orientation = np.asarray(dataset.ImageOrientationPatient, dtype=np.float64)
            current_spacing = np.asarray(dataset.PixelSpacing, dtype=np.float64)
            position = np.asarray(dataset.ImagePositionPatient, dtype=np.float64)
        except Exception as exc:
            raise NativeDicomConversionError("Every classic MR slice must contain complete geometry tags.") from exc
        if not np.allclose(current_orientation, orientation, atol=1e-5, rtol=0.0):
            raise NativeDicomConversionError("Classic MR slice orientations are inconsistent.")
        if not np.allclose(current_spacing, pixel_spacing, atol=1e-5, rtol=0.0):
            raise NativeDicomConversionError("Classic MR pixel spacing is inconsistent.")
        pixels = _scaled_pixels(dataset)
        if pixels.ndim != 2:
            raise NativeDicomConversionError(f"Classic MR instances must be 2D, got shape {pixels.shape}.")
        if expected_shape is None:
            expected_shape = tuple(int(value) for value in pixels.shape)
        elif pixels.shape != expected_shape:
            raise NativeDicomConversionError("Classic MR slice matrix sizes are inconsistent.")
        positioned.append((float(np.dot(position, normal)), dataset, pixels))

    positioned.sort(key=lambda item: item[0])
    projections = np.asarray([item[0] for item in positioned], dtype=np.float64)
    if len(projections) > 1:
        deltas = np.diff(projections)
        if np.any(deltas <= 1e-5):
            raise NativeDicomConversionError(
                "Repeated classic slice positions are unsupported; split temporal volumes into separate mappings."
            )
        slice_spacing = float(np.median(deltas))
        if not np.allclose(deltas, slice_spacing, atol=max(1e-3, slice_spacing * 1e-3), rtol=0.0):
            raise NativeDicomConversionError("Classic MR slice spacing is inconsistent.")
    else:
        slice_spacing = _safe_float(getattr(first, "SpacingBetweenSlices", None)) or _safe_float(
            getattr(first, "SliceThickness", None)
        ) or 1.0

    first_position = np.asarray(positioned[0][1].ImagePositionPatient, dtype=np.float64)
    affine_lps = np.eye(4, dtype=np.float64)
    # NumPy pixel axis 0 follows the DICOM column direction; axis 1 follows row direction.
    affine_lps[:3, 0] = column_direction * pixel_spacing[0]
    affine_lps[:3, 1] = row_direction * pixel_spacing[1]
    affine_lps[:3, 2] = normal * slice_spacing
    affine_lps[:3, 3] = first_position
    data = np.stack([item[2] for item in positioned], axis=2).astype(np.float32, copy=False)
    affine_ras = _LPS_TO_RAS @ affine_lps
    return data, affine_ras, (float(pixel_spacing[0]), float(pixel_spacing[1]), slice_spacing), []


def _mosaic_sort_key(dataset: Any) -> tuple[Any, ...]:
    def number(name: str) -> int:
        try:
            return int(getattr(dataset, name, 0) or 0)
        except (TypeError, ValueError):
            return 0

    return (
        number("TemporalPositionIdentifier"),
        number("AcquisitionNumber"),
        number("InstanceNumber"),
        str(getattr(dataset, "AcquisitionTime", "")),
        str(getattr(dataset, "SOPInstanceUID", "")),
    )


def _siemens_mosaic_series(datasets: list[Any]) -> tuple[np.ndarray, np.ndarray, tuple[float, ...], list[str]]:
    manufacturers = {str(getattr(dataset, "Manufacturer", "")).upper() for dataset in datasets}
    if not all("SIEMENS" in manufacturer for manufacturer in manufacturers):
        raise NativeDicomConversionError("Only Siemens single-frame mosaic DICOM is supported.")
    if not all(_is_mosaic(dataset) for dataset in datasets):
        raise NativeDicomConversionError("Mosaic and non-mosaic instances cannot be mixed in one series.")

    try:
        from nibabel.nicom.dicomwrappers import wrapper_from_data
    except Exception as exc:  # pragma: no cover - nibabel installation issue
        raise RuntimeError("nibabel Siemens DICOM wrapper is unavailable.") from exc

    volumes: list[np.ndarray] = []
    reference_affine: np.ndarray | None = None
    reference_shape: tuple[int, ...] | None = None
    reference_zooms: tuple[float, ...] | None = None
    for dataset in sorted(datasets, key=_mosaic_sort_key):
        try:
            wrapper = wrapper_from_data(dataset)
            volume = np.asarray(wrapper.get_data(), dtype=np.float32)
            affine = _LPS_TO_RAS @ np.asarray(wrapper.affine, dtype=np.float64)
            voxel_sizes = wrapper.voxel_sizes
            if callable(voxel_sizes):  # compatibility with older nibabel releases
                voxel_sizes = voxel_sizes()
            zooms = tuple(float(value) for value in voxel_sizes)
        except Exception as exc:
            raise NativeDicomConversionError(f"Failed to unpack Siemens mosaic geometry: {exc}") from exc
        if volume.ndim != 3:
            raise NativeDicomConversionError(f"Siemens mosaic must unpack to 3D, got shape {volume.shape}.")
        if reference_shape is None:
            reference_shape = tuple(int(value) for value in volume.shape)
            reference_affine = affine
            reference_zooms = zooms
        elif volume.shape != reference_shape or not np.allclose(affine, reference_affine, atol=1e-4, rtol=0.0):
            raise NativeDicomConversionError("Siemens mosaic volume geometry is inconsistent across timepoints.")
        volumes.append(volume)

    assert reference_affine is not None and reference_zooms is not None
    data = np.stack(volumes, axis=3).astype(np.float32, copy=False)
    tr_seconds = (_safe_float(getattr(datasets[0], "RepetitionTime", None)) or 0.0) / 1000.0
    zooms = (*reference_zooms[:3], tr_seconds if tr_seconds > 0 else 1.0)
    warnings = [] if tr_seconds > 0 else ["RepetitionTime was unavailable; NIfTI time spacing defaults to 1 second."]
    return data, reference_affine, zooms, warnings


def _atomic_save_nifti(nib: Any, target: Path, image: Any) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = ".nii.gz" if target.name.lower().endswith(".nii.gz") else ".nii"
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.stem}.", suffix=suffix)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        nib.save(image, str(tmp_path))
        # Windows requires a writable descriptor for FlushFileBuffers/fsync.
        with tmp_path.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(tmp_path, target)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _sidecar_path(nifti_path: Path) -> Path:
    if nifti_path.name.lower().endswith(".nii.gz"):
        return nifti_path.with_name(nifti_path.name[:-7] + ".json")
    return nifti_path.with_suffix(".json")


def convert_dicom_series(
    input_dir: str | Path,
    output_path: str | Path,
    *,
    subject_id: str | None = None,
    session_id: str | None = None,
    modality: str | None = None,
    overwrite: bool = False,
) -> NativeDicomConversionResult:
    """Convert one supported MR series without invoking an external program."""

    nib, pydicom = _require_dependencies()
    source_root = Path(input_dir).resolve()
    target = Path(output_path).resolve()
    if not target.name.lower().endswith((".nii", ".nii.gz")):
        raise NativeDicomConversionError("Output path must end in .nii or .nii.gz.")
    sidecar = _sidecar_path(target)
    if not overwrite and (target.exists() or sidecar.exists()):
        raise NativeDicomConversionError(f"Refusing to overwrite existing conversion output: {target}")
    try:
        target.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise NativeDicomConversionError("Conversion output must not be inside the DICOM source directory.")

    source_paths, datasets = _read_datasets(source_root, pydicom)
    mosaic_flags = {_is_mosaic(dataset) for dataset in datasets}
    if len(mosaic_flags) != 1:
        raise NativeDicomConversionError("Mosaic and classic DICOM instances cannot be mixed in one series.")
    if True in mosaic_flags:
        data, affine, zooms, warnings = _siemens_mosaic_series(datasets)
        series_kind = "siemens_mosaic_4d"
    else:
        data, affine, zooms, warnings = _classic_series(datasets)
        series_kind = "classic_single_frame_3d"

    image = nib.Nifti1Image(data, affine)
    image.header.set_data_dtype(np.float32)
    image.header.set_xyzt_units("mm", "sec")
    image.header.set_zooms(tuple(zooms[: data.ndim]))
    image.set_qform(affine, code=1)
    image.set_sform(affine, code=1)
    _atomic_save_nifti(nib, target, image)

    reloaded = nib.load(str(target))
    if tuple(int(value) for value in reloaded.shape) != tuple(int(value) for value in data.shape):
        target.unlink(missing_ok=True)
        raise NativeDicomConversionError("Persisted NIfTI failed reload shape verification.")

    source_fingerprint = _source_fingerprint(source_paths)
    output_sha = _sha256_file(target)
    series_uid = str(datasets[0].SeriesInstanceUID)
    series_uid_hash = hashlib.sha256(series_uid.encode("utf-8")).hexdigest()
    first = datasets[0]
    payload: dict[str, Any] = {
        "ConversionSoftware": "MedImage Agent native Python converter",
        "ConversionSoftwareVersion": ALGORITHM_VERSION,
        "AlgorithmID": ALGORITHM_ID,
        "AlgorithmVersion": ALGORITHM_VERSION,
        "CapabilityLevel": "computed",
        "SupportedInputProfile": series_kind,
        "Modality": str(getattr(first, "Modality", "MR")),
        "Manufacturer": str(getattr(first, "Manufacturer", "")),
        "SeriesDescription": str(getattr(first, "SeriesDescription", "")),
        "Subject": subject_id,
        "Session": session_id,
        "OutputModality": modality,
        "SourceFileCount": len(source_paths),
        "SourceFingerprintSHA256": source_fingerprint,
        "SeriesInstanceUIDSHA256": series_uid_hash,
        "OutputSHA256": output_sha,
        "Shape": [int(value) for value in data.shape],
        "DataType": "float32",
        "VoxelSize": [float(value) for value in zooms[:3]],
        "Warnings": warnings,
        "CreatedAt": datetime.now(timezone.utc).isoformat(),
        "ResearchUseOnly": True,
    }
    tr_ms = _safe_float(getattr(first, "RepetitionTime", None))
    te_ms = _safe_float(getattr(first, "EchoTime", None))
    flip_angle = _safe_float(getattr(first, "FlipAngle", None))
    if tr_ms is not None:
        payload["RepetitionTime"] = tr_ms / 1000.0
    if te_ms is not None:
        payload["EchoTime"] = te_ms / 1000.0
    if flip_angle is not None:
        payload["FlipAngle"] = flip_angle
    atomic_write_json(sidecar, payload, schema_version=1)

    return NativeDicomConversionResult(
        nifti_path=str(target),
        sidecar_path=str(sidecar),
        source_file_count=len(source_paths),
        source_fingerprint_sha256=source_fingerprint,
        output_sha256=output_sha,
        series_instance_uid_sha256=series_uid_hash,
        series_kind=series_kind,
        shape=tuple(int(value) for value in data.shape),
        dtype="float32",
        zooms=tuple(float(value) for value in zooms[: data.ndim]),
        warnings=tuple(warnings),
    )


__all__ = [
    "ALGORITHM_ID",
    "ALGORITHM_VERSION",
    "NativeDicomConversionError",
    "NativeDicomConversionResult",
    "convert_dicom_series",
]
