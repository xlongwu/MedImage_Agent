"""Affine and voxel-size helpers."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def voxel_sizes_from_affine(affine: np.ndarray) -> tuple[float, float, float]:
    matrix = np.asarray(affine, dtype=float)
    sizes = np.sqrt(np.sum(matrix[:3, :3] ** 2, axis=0))
    sizes = np.where(sizes <= 0, 1.0, sizes)
    return tuple(float(value) for value in sizes[:3])


def fwhm_mm_to_sigma_voxels(
    fwhm_mm: float | Sequence[float],
    affine: np.ndarray,
) -> tuple[float, float, float]:
    if isinstance(fwhm_mm, int | float):
        fwhm_values = (float(fwhm_mm), float(fwhm_mm), float(fwhm_mm))
    else:
        fwhm_values = tuple(float(value) for value in fwhm_mm)
    if len(fwhm_values) != 3:
        raise ValueError("FWHM must be a scalar or a 3-value sequence.")
    if any(value < 0 for value in fwhm_values):
        raise ValueError("FWHM values must be non-negative.")
    divisor = math.sqrt(8.0 * math.log(2.0))
    voxel_sizes = voxel_sizes_from_affine(affine)
    return tuple(float(fwhm / divisor / voxel) for fwhm, voxel in zip(fwhm_values, voxel_sizes, strict=False))


def world_center_of_mass(data: np.ndarray, affine: np.ndarray) -> np.ndarray | None:
    """Return the weighted center of mass in world coordinates, or None."""

    from scipy.ndimage import center_of_mass

    weights = np.abs(
        np.nan_to_num(np.asarray(data, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    )
    if not np.any(weights):
        return None
    voxel_center = np.asarray(center_of_mass(weights), dtype=np.float64)
    if voxel_center.shape[0] < 3 or not np.all(np.isfinite(voxel_center[:3])):
        return None
    homogeneous = np.ones(4, dtype=np.float64)
    homogeneous[:3] = voxel_center[:3]
    return (np.asarray(affine, dtype=np.float64) @ homogeneous)[:3]


def translation_affine_from_centers(
    moving_center_world: np.ndarray,
    reference_center_world: np.ndarray,
) -> np.ndarray:
    """Build a world-space translation from moving image space to reference space."""

    moving = np.asarray(moving_center_world, dtype=np.float64)[:3]
    reference = np.asarray(reference_center_world, dtype=np.float64)[:3]
    matrix = np.eye(4, dtype=np.float32)
    matrix[:3, 3] = (reference - moving).astype(np.float32)
    return matrix


def affine_is_invertible(matrix: np.ndarray) -> bool:
    try:
        determinant = float(np.linalg.det(np.asarray(matrix, dtype=np.float64)[:3, :3]))
    except np.linalg.LinAlgError:
        return False
    return bool(np.isfinite(determinant) and abs(determinant) > 1e-8)
