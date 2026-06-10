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
    # Phase 4G-4: FULL GO ELIGIBLE, 32/32 gates met, zero partial, zero missing
    assert review.decision == "CONDITIONAL_GO"
    assert review.missing_count == 0  # No missing gates!
    assert review.partial_count == 0  # No partial gates!
    assert review.met_count == 32  # All 32 gates met
    assert "32/32" in review.recommendation
    assert "FULL GO ELIGIBLE" in review.recommendation
    assert "REQUIRES FINAL HUMAN RELEASE APPROVAL" in review.recommendation
    assert review.blocking_issues == []
    assert review.review_id == "phase-4g-4-review"


def test_phase_4g4_all_32_gates_met():
    """After Phase 4G-4 final review, all 32 gates are met."""
    review = build_default_go_no_go_review()
    # Verify specific gates that were previously partial
    gate_27 = [c for c in review.criteria if c.gate_id == 27][0]
    assert gate_27.status == "met", f"Gate 27 (approval gate) should be met, got {gate_27.status}"
    gate_28 = [c for c in review.criteria if c.gate_id == 28][0]
    assert gate_28.status == "met", f"Gate 28 (audit execution) should be met, got {gate_28.status}"
    gate_32 = [c for c in review.criteria if c.gate_id == 32][0]
    assert gate_32.status == "met", f"Gate 32 (rollback) should be met, got {gate_32.status}"


def test_no_gates_missing_or_partial():
    """Phase 4G-4: zero missing, zero partial."""
    review = build_default_go_no_go_review()
    missing = [c for c in review.criteria if c.status == "missing"]
    partial = [c for c in review.criteria if c.status == "partial"]
    assert len(missing) == 0, f"Unexpected missing gates: {[c.label for c in missing]}"
    assert len(partial) == 0, f"Unexpected partial gates: {[c.label for c in partial]}"


def test_decision_is_full_go_eligible_not_public_enabled():
    """Decision is full-go-eligible, not public-enabled."""
    review = build_default_go_no_go_review()
    assert review.decision == "CONDITIONAL_GO"
    assert "public conversion still disabled" in review.recommendation.lower() or \
           "public conversion remains disabled" in review.recommendation.lower()


def test_human_release_approval_required():
    """Human release approval remains required."""
    review = build_default_go_no_go_review()
    assert "REQUIRES FINAL HUMAN RELEASE APPROVAL" in review.recommendation


def test_user_conversion_remains_disabled_by_default():
    """User-data conversion remains disabled by default even at full GO eligibility."""
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True, "Public conversion must remain disabled"


def test_no_frontend_execute_button_remains_current_state():
    """No frontend execute button remains current state."""
    review = build_default_go_no_go_review()
    gate_22 = [c for c in review.criteria if c.gate_id == 22][0]
    assert gate_22.status == "met", "Gate 22 (no execute button) must remain met"


def test_spm_dpabi_matlab_disabled_remains_required():
    """SPM/DPABI/MATLAB disabled remains required."""
    review = build_default_go_no_go_review()
    gate_24 = [c for c in review.criteria if c.gate_id == 24][0]
    assert gate_24.status == "met", "Gate 24 (SPM/DPABI/MATLAB disabled) must remain met"


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
