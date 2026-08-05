from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from src.backend.app.core.exceptions import SafetyError
from src.backend.app.schemas.recovery_attempt import RecoveryApprovalEvent
from src.backend.app.services.recovery_policy_service import (
    RecoveryPolicyService,
    calculate_recovery_approval_hash,
)
from tests.helpers_phase8 import build_recovery_fixture


def test_default_policy_requires_explicit_approval_and_revocation_is_authoritative(tmp_path):
    fixture = build_recovery_fixture(tmp_path)
    policy = RecoveryPolicyService(fixture.store)
    approval = policy.approve(
        project_id=fixture.project_id,
        lifecycle_id=fixture.lifecycle_id,
        proposal_id=fixture.proposal.recovery_proposal_id,
        candidate_id=fixture.candidate.candidate_id,
        command_id="approve-1",
        actor="local-reviewer",
    )
    assert approval.approval_mode == "explicit_retry_approval"
    assert approval.parent_ticket_hash == fixture.parent.canonical_hash
    assert approval.candidate_hash == fixture.candidate.candidate_hash

    revoked = policy.revoke(
        approval.recovery_approval_id,
        command_id="revoke-1",
        actor="local-reviewer",
    )
    assert revoked.status == "revoked"
    with pytest.raises(SafetyError, match="RECOVERY_APPROVAL_INACTIVE"):
        policy.validate_approval(
            approval.recovery_approval_id,
            proposal=fixture.proposal,
            candidate=fixture.candidate,
        )


def test_expired_approval_cannot_authorize_child_ticket(tmp_path):
    fixture = build_recovery_fixture(tmp_path)
    policy = RecoveryPolicyService(fixture.store)
    approval = policy.approve(
        project_id=fixture.project_id,
        lifecycle_id=fixture.lifecycle_id,
        proposal_id=fixture.proposal.recovery_proposal_id,
        candidate_id=fixture.candidate.candidate_id,
        command_id="approve-expiring",
        actor="local-reviewer",
    )
    expired = approval.model_copy(
        update={
            "status": "expired",
            "expires_at": datetime.now(UTC) - timedelta(seconds=1),
            "recovery_approval_hash": "pending",
        }
    )
    expired = expired.model_copy(
        update={"recovery_approval_hash": calculate_recovery_approval_hash(expired)}
    )
    fixture.store.update_recovery_approval(
        expired,
        RecoveryApprovalEvent(
            event_id="approval-expired-event",
            recovery_approval_id=approval.recovery_approval_id,
            project_id=fixture.project_id,
            event_type="expired",
            occurred_at=datetime.now(UTC),
            actor="system",
            command_id="expire-1",
            reason_code="APPROVAL_EXPIRED",
            audit_id=approval.audit_id,
        ),
        expected_status="active",
    )
    with pytest.raises(SafetyError, match="RECOVERY_APPROVAL_INACTIVE"):
        policy.validate_approval(
            approval.recovery_approval_id,
            proposal=fixture.proposal,
            candidate=fixture.candidate,
        )


def test_quota_reservation_is_atomic_under_concurrent_requests(tmp_path):
    fixture = build_recovery_fixture(
        tmp_path,
        quota={"max_lifecycle_recovery_attempts": 1, "max_node_attempts": 1},
    )
    policy = RecoveryPolicyService(fixture.store)
    _, _, _, (_, quota) = policy.authorize_candidate(
        project_id=fixture.project_id,
        lifecycle_id=fixture.lifecycle_id,
        proposal_id=fixture.proposal.recovery_proposal_id,
        candidate_id=fixture.candidate.candidate_id,
        require_execution=True,
    )

    def reserve(index: int) -> str:
        try:
            policy.reserve_quota(
                proposal=fixture.proposal,
                candidate=fixture.candidate,
                attempt_id=f"concurrent-attempt-{index}",
                quota=quota,
            )
            return "reserved"
        except SafetyError as exc:
            return str(exc.code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, (1, 2)))
    assert outcomes.count("reserved") == 1
    assert len(fixture.store.list_recovery_quota_reservations(fixture.project_id)) == 1
    assert any(value.startswith("RECOVERY_QUOTA_") for value in outcomes if value != "reserved")
