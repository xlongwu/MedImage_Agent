"""Mask and simplified tissue probability helpers."""
from __future__ import annotations

import numpy as np


def intensity_brain_mask(data: np.ndarray) -> np.ndarray:
    image = np.nan_to_num(np.asarray(data, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    finite = np.isfinite(image)
    positive = image[finite & (image > 0)]
    if positive.size == 0:
        return np.zeros(image.shape, dtype=bool)
    threshold = max(float(np.percentile(positive, 2.0)) * 0.5, 0.0)
    return finite & (image > threshold)


def tissue_probabilities_from_intensity(
    data: np.ndarray,
    mask: np.ndarray,
    *,
    iterations: int = 16,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    """Return simplified CSF/GM/WM probability maps from 1D k-means centers."""

    image = np.nan_to_num(np.asarray(data, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    brain = np.asarray(mask, dtype=bool)
    values = image[brain]
    if values.size < 3:
        raise ValueError("segmentation requires at least three in-mask voxels.")

    centers = np.asarray(np.percentile(values, [20.0, 50.0, 80.0]), dtype=np.float32)
    for _ in range(iterations):
        distances = np.abs(values[:, None] - centers[None, :])
        labels = np.argmin(distances, axis=1)
        updated = centers.copy()
        for index in range(3):
            class_values = values[labels == index]
            if class_values.size:
                updated[index] = float(np.mean(class_values))
        if np.allclose(updated, centers):
            break
        centers = updated

    centers = np.sort(centers)
    spread = float(np.median(np.diff(centers))) if centers.size > 1 else float(np.std(values))
    scale = max(spread, float(np.std(values)) * 0.25, 1e-6)
    weights = np.exp(-0.5 * ((image[..., None] - centers.reshape((1, 1, 1, 3))) / scale) ** 2).astype(np.float32)
    weights[~brain, :] = 0.0
    denominator = np.sum(weights, axis=3, keepdims=True)
    probabilities = np.divide(weights, denominator, out=np.zeros_like(weights), where=denominator > 0)
    csf = probabilities[..., 0].astype(np.float32)
    gm = probabilities[..., 1].astype(np.float32)
    wm = probabilities[..., 2].astype(np.float32)
    return csf, gm, wm, {"csf_center": float(centers[0]), "gm_center": float(centers[1]), "wm_center": float(centers[2])}


def nonzero_fraction(data: np.ndarray) -> float:
    array = np.asarray(data)
    return float(np.count_nonzero(array) / array.size) if array.size else 0.0
