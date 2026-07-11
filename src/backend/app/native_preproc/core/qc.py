"""QC helpers shared by native preprocessing stages."""
from __future__ import annotations

from typing import Any

import numpy as np


def finite_stats(data: np.ndarray) -> dict[str, Any]:
    array = np.asarray(data)
    finite = np.isfinite(array)
    total = int(array.size)
    finite_count = int(np.count_nonzero(finite))
    stats: dict[str, Any] = {
        "shape": [int(value) for value in array.shape],
        "dtype": str(array.dtype),
        "finite_fraction": float(finite_count / total) if total else 0.0,
    }
    if finite_count:
        values = array[finite]
        stats.update(
            {
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
            }
        )
    return stats


def qc_status(errors: list[str], warnings: list[str]) -> str:
    if errors:
        return "fail"
    if warnings:
        return "warning"
    return "pass"
