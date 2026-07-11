"""Spatial resampling helpers for native preprocessing."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def shift_volume(volume: np.ndarray, shift_voxels: Sequence[float], *, order: int = 1) -> np.ndarray:
    from scipy.ndimage import shift

    return shift(
        np.asarray(volume, dtype=np.float32),
        shift=tuple(float(value) for value in shift_voxels),
        order=int(order),
        mode="nearest",
        prefilter=order > 1,
    ).astype(np.float32)


def apply_volume_shifts(data: np.ndarray, shifts_voxels: np.ndarray, *, order: int = 1) -> np.ndarray:
    source = np.asarray(data, dtype=np.float32)
    if source.ndim != 4:
        raise ValueError(f"4D input required for applying volume shifts, got {source.shape}.")
    if shifts_voxels.shape != (source.shape[3], 3):
        raise ValueError("shifts_voxels must have shape (timepoints, 3).")
    corrected = np.empty_like(source, dtype=np.float32)
    for index in range(source.shape[3]):
        corrected[..., index] = shift_volume(source[..., index], shifts_voxels[index], order=order)
    return corrected


def _output_to_input_voxel_mapping(
    input_affine: np.ndarray,
    output_affine: np.ndarray,
    input_to_output_affine: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    transform = np.eye(4, dtype=np.float64) if input_to_output_affine is None else np.asarray(input_to_output_affine)
    mapping = np.linalg.inv(np.asarray(input_affine, dtype=np.float64)) @ np.linalg.inv(transform) @ np.asarray(
        output_affine, dtype=np.float64
    )
    return mapping[:3, :3], mapping[:3, 3]


def resample_spatial_to_reference(
    data: np.ndarray,
    input_affine: np.ndarray,
    reference_shape: Sequence[int],
    reference_affine: np.ndarray,
    *,
    input_to_reference_affine: np.ndarray | None = None,
    order: int = 1,
    cval: float = 0.0,
    output_dtype: str | np.dtype = np.float32,
) -> np.ndarray:
    """Resample a 3D image or each volume of a 4D image onto a reference grid."""

    from scipy.ndimage import affine_transform

    source = np.asarray(data)
    spatial_shape = tuple(int(value) for value in reference_shape[:3])
    if len(spatial_shape) != 3:
        raise ValueError("reference_shape must contain at least three spatial dimensions.")
    matrix, offset = _output_to_input_voxel_mapping(input_affine, reference_affine, input_to_reference_affine)

    def _resample_volume(volume: np.ndarray) -> np.ndarray:
        return affine_transform(
            np.asarray(volume),
            matrix=matrix,
            offset=offset,
            output_shape=spatial_shape,
            order=int(order),
            mode="constant",
            cval=float(cval),
            prefilter=order > 1,
        )

    if source.ndim == 3:
        return np.asarray(_resample_volume(source), dtype=output_dtype)
    if source.ndim == 4:
        output = np.empty(spatial_shape + (int(source.shape[3]),), dtype=output_dtype)
        for index in range(source.shape[3]):
            output[..., index] = _resample_volume(source[..., index]).astype(output_dtype, copy=False)
        return output
    raise ValueError(f"resampling requires 3D or 4D input, got shape {source.shape}.")
