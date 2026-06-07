"""Pipeline Execution State Schema — unit tests.

Tests: run/node states, terminal sets, retry/resume/reuse eligibility,
transition helpers, unknown-string safety, purity (no file I/O, no runtime).
"""

from __future__ import annotations

import inspect

from src.backend.app.schemas.execution_state import (
    NODE_ALLOWED_TRANSITIONS,
    NODE_FAILURE_STATES,
    NODE_NON_TERMINAL_STATES,
    NODE_RETRY_ELIGIBLE_STATES,
    NODE_REUSE_ELIGIBLE_STATES,
    NODE_SUCCESS_STATES,
    NODE_TERMINAL_STATES,
    RUN_ALLOWED_TRANSITIONS,
    RUN_FAILURE_STATES,
    RUN_NON_TERMINAL_STATES,
    RUN_RESUME_ELIGIBLE_STATES,
    RUN_RETRY_ELIGIBLE_STATES,
    RUN_SUCCESS_STATES,
    RUN_TERMINAL_STATES,
    NodeState,
    NodeStateTransition,
    RunState,
    RunStateTransition,
    can_transition_node,
    can_transition_run,
    is_node_reuse_eligible,
    is_node_retry_eligible,
    is_node_terminal,
    is_run_resume_eligible,
    is_run_retry_eligible,
    is_run_terminal,
)


# ── 1. State definitions ─────────────────────────────────────────────────────

def test_all_run_states_present():
    """All 15 run states from the contract are defined in RunState."""
    expected = {
        "created", "queued", "preflight", "approval_required",
        "audit_required", "ready", "running", "succeeded", "failed",
        "blocked", "cancelled", "timeout", "partial", "interrupted", "unknown",
    }
    actual = set(RunState.__args__)  # type: ignore[attr-defined]
    assert actual == expected, f"Missing: {expected - actual}, Extra: {actual - expected}"


def test_all_node_states_present():
    """All 13 node states from the contract are defined in NodeState."""
    expected = {
        "pending", "skipped", "preflight", "ready", "running",
        "succeeded", "failed", "blocked", "cancelled", "timeout",
        "reused", "invalidated", "unknown",
    }
    actual = set(NodeState.__args__)  # type: ignore[attr-defined]
    assert actual == expected, f"Missing: {expected - actual}, Extra: {actual - expected}"


# ── 2. Terminal states ───────────────────────────────────────────────────────

def test_run_terminal_states_correct():
    """RUN_TERMINAL_STATES matches the contract: 8 terminal states."""
    expected = {
        "succeeded", "failed", "blocked", "cancelled",
        "timeout", "partial", "interrupted",
    }
    # unknown may or may not be terminal; assert at least the core set
    assert expected <= RUN_TERMINAL_STATES, \
        f"Missing terminal states: {expected - RUN_TERMINAL_STATES}"


def test_run_non_terminal_states_correct():
    """RUN_NON_TERMINAL_STATES covers created/queued/preflight/approval_required/audit_required/ready/running."""
    expected = {
        "created", "queued", "preflight", "approval_required",
        "audit_required", "ready", "running",
    }
    assert expected <= RUN_NON_TERMINAL_STATES, \
        f"Missing non-terminal states: {expected - RUN_NON_TERMINAL_STATES}"


def test_node_terminal_states_correct():
    """NODE_TERMINAL_STATES matches the contract: 8 terminal states."""
    expected = {
        "skipped", "succeeded", "failed", "blocked",
        "cancelled", "timeout", "reused", "invalidated",
    }
    assert expected <= NODE_TERMINAL_STATES, \
        f"Missing terminal states: {expected - NODE_TERMINAL_STATES}"


def test_node_non_terminal_states_correct():
    """NODE_NON_TERMINAL_STATES covers pending/preflight/ready/running."""
    expected = {"pending", "preflight", "ready", "running"}
    assert expected <= NODE_NON_TERMINAL_STATES, \
        f"Missing non-terminal states: {expected - NODE_NON_TERMINAL_STATES}"


def test_is_run_terminal_true():
    """is_run_terminal returns True for terminal states."""
    for state in RUN_TERMINAL_STATES:
        assert is_run_terminal(state) is True, f"Expected {state} to be terminal"


def test_is_run_terminal_false():
    """is_run_terminal returns False for non-terminal states."""
    for state in RUN_NON_TERMINAL_STATES:
        assert is_run_terminal(state) is False, f"Expected {state} to be non-terminal"


def test_is_node_terminal_true():
    """is_node_terminal returns True for terminal states."""
    for state in NODE_TERMINAL_STATES:
        assert is_node_terminal(state) is True, f"Expected {state} to be terminal"


def test_is_node_terminal_false():
    """is_node_terminal returns False for non-terminal states."""
    for state in NODE_NON_TERMINAL_STATES:
        assert is_node_terminal(state) is False, f"Expected {state} to be non-terminal"


# ── 3. Success / failure sets ────────────────────────────────────────────────

def test_run_success_states():
    """RUN_SUCCESS_STATES contains succeeded."""
    assert "succeeded" in RUN_SUCCESS_STATES


def test_run_failure_states():
    """RUN_FAILURE_STATES contains failed, blocked, timeout, partial, interrupted, cancelled."""
    expected = {"failed", "blocked", "timeout", "partial", "interrupted", "cancelled"}
    assert expected <= RUN_FAILURE_STATES


def test_node_success_states():
    """NODE_SUCCESS_STATES contains succeeded, reused."""
    assert "succeeded" in NODE_SUCCESS_STATES
    assert "reused" in NODE_SUCCESS_STATES


def test_node_failure_states():
    """NODE_FAILURE_STATES contains failed, blocked, timeout, cancelled, invalidated."""
    expected = {"failed", "blocked", "timeout", "cancelled", "invalidated"}
    assert expected <= NODE_FAILURE_STATES


# ── 4. Retry eligibility ─────────────────────────────────────────────────────

def test_run_retry_eligible():
    """RUN_RETRY_ELIGIBLE_STATES matches contract: failed, blocked, timeout, partial, interrupted."""
    expected = {"failed", "blocked", "timeout", "partial", "interrupted"}
    assert expected == RUN_RETRY_ELIGIBLE_STATES, \
        f"Expected {expected}, got {RUN_RETRY_ELIGIBLE_STATES}"


def test_is_run_retry_eligible_true():
    """is_run_retry_eligible returns True for eligible states."""
    for state in RUN_RETRY_ELIGIBLE_STATES:
        assert is_run_retry_eligible(state) is True, f"Expected {state} retry-eligible"


def test_is_run_retry_eligible_false():
    """is_run_retry_eligible returns False for ineligible states."""
    ineligible = {"succeeded", "running", "created", "queued", "preflight", "ready"}
    for state in ineligible:
        assert is_run_retry_eligible(state) is False, f"Expected {state} NOT retry-eligible"


def test_node_retry_eligible():
    """NODE_RETRY_ELIGIBLE_STATES matches contract: failed, blocked, timeout, invalidated."""
    expected = {"failed", "blocked", "timeout", "invalidated"}
    assert expected == NODE_RETRY_ELIGIBLE_STATES, \
        f"Expected {expected}, got {NODE_RETRY_ELIGIBLE_STATES}"


def test_is_node_retry_eligible_true():
    """is_node_retry_eligible returns True for eligible states."""
    for state in NODE_RETRY_ELIGIBLE_STATES:
        assert is_node_retry_eligible(state) is True, f"Expected {state} retry-eligible"


def test_is_node_retry_eligible_false():
    """is_node_retry_eligible returns False for ineligible states."""
    ineligible = {"succeeded", "running", "pending", "preflight", "ready", "reused"}
    for state in ineligible:
        assert is_node_retry_eligible(state) is False, f"Expected {state} NOT retry-eligible"


# ── 5. Resume eligibility ────────────────────────────────────────────────────

def test_run_resume_eligible():
    """RUN_RESUME_ELIGIBLE_STATES matches contract: failed, timeout, partial, interrupted."""
    expected = {"failed", "timeout", "partial", "interrupted"}
    assert expected == RUN_RESUME_ELIGIBLE_STATES, \
        f"Expected {expected}, got {RUN_RESUME_ELIGIBLE_STATES}"


def test_is_run_resume_eligible_true():
    """is_run_resume_eligible returns True for eligible states."""
    for state in RUN_RESUME_ELIGIBLE_STATES:
        assert is_run_resume_eligible(state) is True, f"Expected {state} resume-eligible"


def test_is_run_resume_eligible_false():
    """is_run_resume_eligible returns False for ineligible states."""
    ineligible = {"succeeded", "running", "created", "queued", "blocked", "cancelled"}
    for state in ineligible:
        assert is_run_resume_eligible(state) is False, f"Expected {state} NOT resume-eligible"


# ── 6. Node reuse eligibility ────────────────────────────────────────────────

def test_node_reuse_eligible():
    """NODE_REUSE_ELIGIBLE_STATES: succeeded, reused."""
    expected = {"succeeded", "reused"}
    assert expected == NODE_REUSE_ELIGIBLE_STATES


def test_is_node_reuse_eligible_true():
    """is_node_reuse_eligible returns True for succeeded and reused."""
    for state in NODE_REUSE_ELIGIBLE_STATES:
        assert is_node_reuse_eligible(state) is True


def test_is_node_reuse_eligible_false():
    """is_node_reuse_eligible returns False for non-reuse-eligible states."""
    for state in ("pending", "running", "failed", "blocked", "invalidated"):
        assert is_node_reuse_eligible(state) is False, f"Expected {state} NOT reuse-eligible"


# ── 7. Transition helpers ────────────────────────────────────────────────────

def test_can_transition_run_allowed():
    """Allowed transitions return True."""
    # Spot-check key transitions from the contract
    allowed_pairs = [
        ("created", "queued"),
        ("queued", "preflight"),
        ("preflight", "approval_required"),
        ("preflight", "audit_required"),
        ("preflight", "ready"),
        ("approval_required", "preflight"),
        ("audit_required", "preflight"),
        ("ready", "running"),
        ("running", "succeeded"),
        ("running", "failed"),
        ("running", "timeout"),
        ("running", "cancelled"),
        ("running", "partial"),
        ("running", "interrupted"),
        ("partial", "failed"),
        ("partial", "interrupted"),
    ]
    for from_s, to_s in allowed_pairs:
        assert can_transition_run(from_s, to_s) is True, \
            f"Expected {from_s} -> {to_s} allowed"


def test_can_transition_run_disallowed():
    """Disallowed transitions return False."""
    disallowed_pairs = [
        ("succeeded", "running"),
        ("succeeded", "failed"),
        ("failed", "succeeded"),
        ("blocked", "running"),
        ("running", "created"),
        ("created", "succeeded"),
    ]
    for from_s, to_s in disallowed_pairs:
        assert can_transition_run(from_s, to_s) is False, \
            f"Expected {from_s} -> {to_s} disallowed"


def test_terminal_succeeded_no_outgoing_transition():
    """Terminal succeeded run has no outgoing transition by default."""
    for to_state in RunState.__args__:  # type: ignore[attr-defined]
        if to_state == "succeeded":
            continue
        assert can_transition_run("succeeded", to_state) is False, \
            f"succeeded should not transition to {to_state}"


def test_can_transition_node_allowed():
    """Allowed node transitions return True."""
    allowed_pairs = [
        ("pending", "preflight"),
        ("pending", "skipped"),
        ("pending", "blocked"),
        ("preflight", "ready"),
        ("ready", "running"),
        ("ready", "skipped"),
        ("running", "succeeded"),
        ("running", "failed"),
        ("running", "timeout"),
        ("running", "blocked"),
        ("running", "cancelled"),
        ("failed", "preflight"),
        ("failed", "ready"),
        ("blocked", "preflight"),
        ("timeout", "preflight"),
        ("invalidated", "pending"),
        ("invalidated", "preflight"),
        ("succeeded", "reused"),
        ("succeeded", "invalidated"),
        ("reused", "invalidated"),
    ]
    for from_s, to_s in allowed_pairs:
        assert can_transition_node(from_s, to_s) is True, \
            f"Expected {from_s} -> {to_s} allowed"


def test_can_transition_node_disallowed():
    """Disallowed node transitions return False."""
    disallowed_pairs = [
        ("succeeded", "failed"),
        ("succeeded", "pending"),
        ("failed", "succeeded"),
        ("skipped", "running"),
        ("reused", "pending"),
        ("running", "pending"),
    ]
    for from_s, to_s in disallowed_pairs:
        assert can_transition_node(from_s, to_s) is False, \
            f"Expected {from_s} -> {to_s} disallowed"


def test_succeeded_node_can_transition_to_reused_or_invalidated():
    """Succeeded node can transition to reused or invalidated only within terminal set."""
    assert can_transition_node("succeeded", "reused") is True
    assert can_transition_node("succeeded", "invalidated") is True


# ── 8. Unknown string safety ─────────────────────────────────────────────────

def test_unknown_string_terminal_returns_false():
    """Unknown strings return False for all terminal/eligibility functions."""
    bogus = "bogus_nonexistent_state"
    assert is_run_terminal(bogus) is False
    assert is_node_terminal(bogus) is False
    assert is_run_retry_eligible(bogus) is False
    assert is_run_resume_eligible(bogus) is False
    assert is_node_retry_eligible(bogus) is False
    assert is_node_reuse_eligible(bogus) is False


def test_unknown_string_transition_returns_false():
    """Unknown strings return False for transition helpers."""
    bogus = "bogus_nonexistent_state"
    assert can_transition_run(bogus, "running") is False
    assert can_transition_run("running", bogus) is False
    assert can_transition_node(bogus, "running") is False
    assert can_transition_node("running", bogus) is False


def test_empty_string_transition_returns_false():
    """Empty string returns False."""
    assert can_transition_run("", "running") is False
    assert can_transition_node("", "running") is False


# ── 9. Purity / no runtime imports ────────────────────────────────────────────

def test_module_imports_no_runtime_executor():
    """Schema module must not import from pipeline_executor, state_store, or execute_reviewed_routes."""
    import src.backend.app.schemas.execution_state as es
    source = inspect.getsource(es)
    forbidden = [
        "pipeline_executor",
        "state_store",
        "execute_reviewed_routes",
        "node_registry",
    ]
    for name in forbidden:
        assert name not in source, f"Found forbidden import: {name}"


def test_module_does_no_file_io():
    """Schema module must not perform file I/O on import."""
    import src.backend.app.schemas.execution_state as es
    source = inspect.getsource(es)
    iowords = ["open(", "Path(", "write_text", "read_text", "json.dump", "json.load"]
    for word in iowords:
        assert word not in source, f"Found file I/O pattern: {word}"


# ── 10. Pydantic models ──────────────────────────────────────────────────────

def test_run_state_transition_model():
    """RunStateTransition model works correctly."""
    t = RunStateTransition(from_state="created", to_state="queued", allowed=True, reason=None)
    assert t.from_state == "created"
    assert t.to_state == "queued"
    assert t.allowed is True
    assert t.reason is None

    t2 = RunStateTransition(from_state="succeeded", to_state="running", allowed=False, reason="terminal")
    assert t2.allowed is False
    assert t2.reason == "terminal"


def test_node_state_transition_model():
    """NodeStateTransition model works correctly."""
    t = NodeStateTransition(from_state="pending", to_state="ready", allowed=True)
    assert t.from_state == "pending"
    assert t.to_state == "ready"
    assert t.allowed is True
