"""Transform helpers for native realignment."""
from __future__ import annotations

import numpy as np


def translation_matrix_mm(translation_mm: np.ndarray) -> np.ndarray:
    matrix = np.eye(4, dtype=np.float32)
    matrix[:3, 3] = np.asarray(translation_mm, dtype=np.float32)[:3]
    return matrix


def voxel_shift_to_mm(shift_voxels: np.ndarray, voxel_sizes: tuple[float, float, float]) -> np.ndarray:
    return np.asarray(shift_voxels, dtype=np.float32) * np.asarray(voxel_sizes, dtype=np.float32)


def motion_row_from_translation(translation_mm: np.ndarray) -> list[float]:
    translation = np.asarray(translation_mm, dtype=float)[:3]
    return [float(translation[0]), float(translation[1]), float(translation[2]), 0.0, 0.0, 0.0]
