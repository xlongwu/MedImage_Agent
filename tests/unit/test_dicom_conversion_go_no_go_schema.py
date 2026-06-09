"""Tests for DICOM conversion GO/NO-GO schema — Phase 4G-0.

Tests decision logic with various criteria combinations.
No subprocess. No file I/O. No dcm2niix. No SPM/DPABI/MATLAB.
"""

from __future__ import annotations

from src.backend.app.schemas.dicom_conversion_go_no_go import (
    DicomConversionGoNoGoCriterion,
    build_default_go_no_go_review,
    evaluate_go_no_go_criteria,
    is_conditional_go_allowed,
    summarize_missing_go_criteria,
)


def _make_criterion(gate_id: int, status: str = "met") -> DicomConversionGoNoGoCriterion:
    return DicomConversionGoNoGoCriterion(gate_id=gate_id, label=f"gate-{gate_id}", status=status)  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Decision logic
# ═══════════════════════════════════════════════════════════════════════


def test_all_met_produces_go():
    criteria = [_make_criterion(i, "met") for i in range(1, 33)]
    result = evaluate_go_no_go_criteria(criteria)
    assert result == "GO"


def test_missing_critical_gate_produces_no_go():
    criteria = [_make_criterion(i, "met") for i in range(1, 33)]
    criteria[0] = _make_criterion(1, "missing")  # rawdata read-only is critical
    result = evaluate_go_no_go_criteria(criteria)
    assert result == "NO_GO"


def test_missing_non_critical_gate_produces_no_go():
    criteria = [_make_criterion(i, "met") for i in range(1, 33)]
    criteria[10] = _make_criterion(11, "missing")  # logs planned (not critical but missing)
    result = evaluate_go_no_go_criteria(criteria)
    assert result == "NO_GO"


def test_partial_non_critical_produces_conditional_go():
    criteria = [_make_criterion(i, "met") for i in range(1, 33)]
    criteria[11] = _make_criterion(12, "partial")  # rollback (non-critical)
    result = evaluate_go_no_go_criteria(criteria)
    assert result == "CONDITIONAL_GO"


def test_partial_critical_produces_no_go():
    criteria = [_make_criterion(i, "met") for i in range(1, 33)]
    criteria[0] = _make_criterion(1, "partial")  # rawdata (critical)
    result = evaluate_go_no_go_criteria(criteria)
    assert result == "NO_GO"


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Default review
# ═══════════════════════════════════════════════════════════════════════


def test_default_review_is_conditional_go():
    review = build_default_go_no_go_review()
    # Phase 4G-3: CONDITIONAL GO maintained, 30/32 gates met, zero missing
    assert review.decision == "CONDITIONAL_GO"
    assert review.missing_count == 0  # No missing gates!
    assert review.met_count >= 28  # 28 met + 2 partial = 30 total, 0 missing
    assert "30/32" in review.recommendation


def test_default_review_has_all_criteria():
    review = build_default_go_no_go_review()
    assert review.total_criteria == 32


def test_conditional_go_helper():
    review = build_default_go_no_go_review()
    assert is_conditional_go_allowed(review) is True  # Phase 4G-2: CONDITIONAL GO


def test_summarize_missing():
    review = build_default_go_no_go_review()
    summary = summarize_missing_go_criteria(review)
    assert summary["decision"] == "CONDITIONAL_GO"
    assert summary["missing_count"] == 0  # Zero missing gates after Phase 4I-1b


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Purity
# ═══════════════════════════════════════════════════════════════════════


def test_schema_has_no_subprocess():
    import src.backend.app.schemas.dicom_conversion_go_no_go as mod
    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content
    assert "from subprocess" not in content


def test_schema_has_no_file_write():
    import src.backend.app.schemas.dicom_conversion_go_no_go as mod
    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "open(" not in content


def test_helpers_are_pure():
    # All helpers must return valid results without side effects
    review = build_default_go_no_go_review()
    assert review.decision in {"NO_GO", "CONDITIONAL_GO", "GO"}
    decision = evaluate_go_no_go_criteria(review.criteria)
    assert decision in {"NO_GO", "CONDITIONAL_GO", "GO"}
    summary = summarize_missing_go_criteria(review)
    assert isinstance(summary, dict)
