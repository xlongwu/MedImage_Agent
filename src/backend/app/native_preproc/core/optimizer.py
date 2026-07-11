"""Lightweight optimization helpers for phase-02 native realignment."""
from __future__ import annotations

import numpy as np


def _center_of_mass_or_none(volume: np.ndarray) -> np.ndarray | None:
    from scipy.ndimage import center_of_mass

    weights = np.abs(np.nan_to_num(volume.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0))
    if not np.any(weights):
        return None
    center = np.asarray(center_of_mass(weights), dtype=np.float32)
    if not np.all(np.isfinite(center)):
        return None
    return center


def estimate_translation_to_reference(
    moving: np.ndarray,
    reference: np.ndarray,
) -> tuple[np.ndarray, list[str]]:
    """Estimate a translation-only shift that moves ``moving`` toward ``reference``."""

    warnings: list[str] = []
    reference_center = _center_of_mass_or_none(reference)
    moving_center = _center_of_mass_or_none(moving)
    if reference_center is None or moving_center is None:
        warnings.append("center_of_mass_unavailable_zero_translation_used")
        return np.zeros(3, dtype=np.float32), warnings
    return (reference_center - moving_center).astype(np.float32), warnings
