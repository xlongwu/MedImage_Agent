"""Reference comparison helpers for native preprocessing validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _safe_correlation(candidate: np.ndarray, reference: np.ndarray) -> float | None:
    cand = np.asarray(candidate, dtype=np.float64).reshape(-1)
    ref = np.asarray(reference, dtype=np.float64).reshape(-1)
    finite = np.isfinite(cand) & np.isfinite(ref)
    if finite.sum() < 2:
        return None
    cand = cand[finite]
    ref = ref[finite]
    if float(np.std(cand)) == 0.0 or float(np.std(ref)) == 0.0:
        return None
    return float(np.corrcoef(cand, ref)[0, 1])


def _dice(candidate: np.ndarray, reference: np.ndarray) -> float | None:
    cand = np.asarray(candidate).astype(bool)
    ref = np.asarray(reference).astype(bool)
    denom = int(cand.sum() + ref.sum())
    if denom == 0:
        return 1.0
    return float(2 * np.logical_and(cand, ref).sum() / denom)


def compare_numeric_reference(
    candidate: np.ndarray,
    reference: np.ndarray,
    *,
    stage_id: str,
    metric_name: str,
    tolerance: float,
    max_abs_tolerance: float | None = None,
    min_correlation: float | None = None,
    min_dice: float | None = None,
    reference_source: str = "synthetic_reference",
) -> dict[str, Any]:
    """Compare candidate output with an approved numeric reference."""

    candidate_array = np.asarray(candidate)
    reference_array = np.asarray(reference)
    shape_match = tuple(candidate_array.shape) == tuple(reference_array.shape)
    max_abs_tolerance = tolerance if max_abs_tolerance is None else max_abs_tolerance
    if shape_match:
        diff = np.asarray(candidate_array, dtype=np.float64) - np.asarray(reference_array, dtype=np.float64)
        finite = np.isfinite(diff)
        if finite.any():
            mae = float(np.mean(np.abs(diff[finite])))
            rmse = float(np.sqrt(np.mean(np.square(diff[finite]))))
            max_abs_error = float(np.max(np.abs(diff[finite])))
        else:
            mae = rmse = max_abs_error = float("inf")
        correlation = _safe_correlation(candidate_array, reference_array)
        dice = _dice(candidate_array, reference_array) if min_dice is not None else None
    else:
        mae = rmse = max_abs_error = float("inf")
        correlation = None
        dice = None

    passed = shape_match and mae <= tolerance and rmse <= tolerance and max_abs_error <= max_abs_tolerance
    if min_correlation is not None:
        passed = passed and correlation is not None and correlation >= min_correlation
    if min_dice is not None:
        passed = passed and dice is not None and dice >= min_dice

    return {
        "stage_id": stage_id,
        "metric_name": metric_name,
        "reference_source": reference_source,
        "passed": bool(passed),
        "shape_match": shape_match,
        "candidate_shape": [int(value) for value in candidate_array.shape],
        "reference_shape": [int(value) for value in reference_array.shape],
        "tolerance": tolerance,
        "max_abs_tolerance": max_abs_tolerance,
        "mae": mae,
        "rmse": rmse,
        "max_abs_error": max_abs_error,
        "correlation": correlation,
        "min_correlation": min_correlation,
        "dice": dice,
        "min_dice": min_dice,
    }


def load_reference_array(path: str | Path) -> np.ndarray:
    """Load a reference array from `.npy` or NIfTI without executing tools."""

    ref_path = Path(path)
    if ref_path.suffix == ".npy":
        return np.load(ref_path)
    if ref_path.suffix == ".nii" or ref_path.name.endswith(".nii.gz"):
        import nibabel as nib

        return np.asarray(nib.load(str(ref_path)).get_fdata(dtype=np.float32))
    raise ValueError(f"Unsupported reference artifact type: {ref_path}")


def compare_reference_artifacts(
    candidate_path: str | Path,
    reference_path: str | Path,
    *,
    stage_id: str,
    metric_name: str,
    tolerance: float,
    max_abs_tolerance: float | None = None,
    min_correlation: float | None = None,
    min_dice: float | None = None,
    reference_source: str = "approved_reference_artifact",
) -> dict[str, Any]:
    """Compare persisted candidate and reference artifacts."""

    return compare_numeric_reference(
        load_reference_array(candidate_path),
        load_reference_array(reference_path),
        stage_id=stage_id,
        metric_name=metric_name,
        tolerance=tolerance,
        max_abs_tolerance=max_abs_tolerance,
        min_correlation=min_correlation,
        min_dice=min_dice,
        reference_source=reference_source,
    )


def reference_pending(stage_id: str, *, reason: str) -> dict[str, Any]:
    """Record that a stage intentionally remains short of reference validation."""

    return {
        "stage_id": stage_id,
        "metric_name": "reference_validation",
        "reference_source": "",
        "passed": False,
        "status": "pending",
        "reason": reason,
    }


__all__ = [
    "compare_numeric_reference",
    "compare_reference_artifacts",
    "load_reference_array",
    "reference_pending",
]
