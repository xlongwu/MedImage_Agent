"""Interpolation kernels for native preprocessing."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def interpolate_series_to_reference_time(
    series: np.ndarray,
    *,
    tr: float,
    source_time: float,
    reference_time: float,
) -> np.ndarray:
    """Shift one voxel time series from slice acquisition time to reference time."""

    values = np.asarray(series, dtype=np.float32)
    timepoints = values.shape[-1]
    sample_times = np.arange(timepoints, dtype=np.float32) * float(tr) + float(source_time)
    target_times = np.arange(timepoints, dtype=np.float32) * float(tr) + float(reference_time)
    corrected = np.interp(target_times, sample_times, values, left=float(values[0]), right=float(values[-1]))
    return corrected.astype(np.float32)


def slice_timing_correct_4d(
    data: np.ndarray,
    *,
    tr: float,
    slice_timing: Sequence[float],
    reference_time: float,
) -> np.ndarray:
    """Apply per-slice temporal interpolation to a 4D BOLD array."""

    source = np.asarray(data, dtype=np.float32)
    if source.ndim != 4:
        raise ValueError(f"slice timing correction requires 4D input, got {source.shape}.")
    if len(slice_timing) != source.shape[2]:
        raise ValueError("slice_timing length must equal the number of z slices.")
    if tr <= 0:
        raise ValueError("TR must be positive.")

    corrected = np.empty_like(source, dtype=np.float32)
    for z_index, acquisition_time in enumerate(slice_timing):
        plane = source[:, :, z_index, :]
        flat = plane.reshape((-1, plane.shape[-1]))
        shifted = np.vstack(
            [
                interpolate_series_to_reference_time(
                    row,
                    tr=tr,
                    source_time=float(acquisition_time),
                    reference_time=float(reference_time),
                )
                for row in flat
            ]
        )
        corrected[:, :, z_index, :] = shifted.reshape(plane.shape)
    return corrected
