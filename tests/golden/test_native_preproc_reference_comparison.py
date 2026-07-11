from __future__ import annotations

import numpy as np

from src.backend.app.native_preproc.orchestrator.golden_reference import (
    compare_numeric_reference,
    reference_pending,
)


def test_native_reference_comparison_passes_when_metrics_are_within_tolerance() -> None:
    reference = np.array([[1.0, 0.5], [0.5, 1.0]], dtype=np.float32)
    candidate = reference + np.array([[0.0, 1e-5], [-1e-5, 0.0]], dtype=np.float32)

    comparison = compare_numeric_reference(
        candidate,
        reference,
        stage_id="functional_connectivity",
        metric_name="fc_matrix",
        tolerance=1e-4,
        min_correlation=0.999,
        reference_source="approved_synthetic_reference",
    )

    assert comparison["passed"] is True
    assert comparison["shape_match"] is True
    assert comparison["max_abs_error"] < 1e-4
    assert comparison["correlation"] >= 0.999


def test_native_reference_comparison_fails_on_shape_or_tolerance_mismatch() -> None:
    reference = np.zeros((2, 2), dtype=np.float32)
    wrong_shape = np.zeros((2, 3), dtype=np.float32)
    wrong_values = np.ones((2, 2), dtype=np.float32)

    shape_comparison = compare_numeric_reference(
        wrong_shape,
        reference,
        stage_id="alff",
        metric_name="alff_map",
        tolerance=1e-4,
    )
    value_comparison = compare_numeric_reference(
        wrong_values,
        reference,
        stage_id="alff",
        metric_name="alff_map",
        tolerance=1e-4,
    )

    assert shape_comparison["passed"] is False
    assert shape_comparison["shape_match"] is False
    assert value_comparison["passed"] is False
    assert value_comparison["mae"] > 1e-4


def test_reference_pending_is_not_a_passing_reference_claim() -> None:
    pending = reference_pending(
        "normalization",
        reason="No approved SPM or independent template reference fixture was provided.",
    )

    assert pending["status"] == "pending"
    assert pending["passed"] is False
    assert pending["stage_id"] == "normalization"
