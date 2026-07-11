"""NIfTI read/write helpers for native preprocessing stages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class NiftiImageData:
    data: np.ndarray
    affine: np.ndarray
    header: Any
    path: Path

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(int(value) for value in self.data.shape)

    @property
    def dtype_name(self) -> str:
        return str(self.data.dtype)


def _nibabel():
    try:
        import nibabel as nib
    except ImportError as exc:  # pragma: no cover - exercised in dependency probes
        raise RuntimeError("Missing dependency: nibabel is required for native NIfTI I/O.") from exc
    return nib


def load_nifti(path: str | Path, *, dtype: str | np.dtype = np.float32) -> NiftiImageData:
    """Load a NIfTI image as an in-memory numeric array."""

    nib = _nibabel()
    image_path = Path(path)
    img = nib.load(str(image_path))
    data = np.asarray(img.get_fdata(dtype=np.dtype(dtype)), dtype=dtype)
    return NiftiImageData(data=data, affine=np.asarray(img.affine), header=img.header.copy(), path=image_path)


def save_nifti(
    path: str | Path,
    data: np.ndarray,
    affine: np.ndarray,
    *,
    header: Any | None = None,
    dtype: str | np.dtype = np.float32,
) -> Path:
    """Persist a NIfTI image and return the output path."""

    nib = _nibabel()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    out_data = np.asarray(data, dtype=dtype)
    out_header = header.copy() if header is not None else None
    if out_header is not None:
        out_header.set_data_dtype(out_data.dtype)
    img = nib.Nifti1Image(out_data, np.asarray(affine), header=out_header)
    nib.save(img, str(target))
    return target


def nifti_summary(path: str | Path) -> dict[str, Any]:
    """Return lightweight reload metadata for an existing NIfTI artifact."""

    nib = _nibabel()
    image_path = Path(path)
    img = nib.load(str(image_path))
    shape = [int(value) for value in img.shape]
    dtype = str(img.get_data_dtype())
    zooms = [float(value) for value in img.header.get_zooms()[: len(shape)]]
    return {
        "shape": shape,
        "dtype": dtype,
        "zooms": zooms,
        "affine": np.asarray(img.affine).tolist(),
    }


def ensure_4d(data: np.ndarray, *, stage_id: str) -> None:
    if data.ndim != 4:
        raise ValueError(f"{stage_id} requires 4D BOLD input, got shape {tuple(data.shape)}.")
