"""Audit Record — minimal review/approval/execution audit trail.

Creates immutable, hash-verifiable snapshots of plan review events
so that every future execution can be traced to a specific review.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReviewAuditRecord:
    audit_id: str
    created_at: str
    event_type: str
    plan_hash: str
    validation_hash: str
    approval_hash: str | None
    plan: dict[str, Any]
    validation: dict[str, Any]
    approval: dict[str, Any] | None
    approval_gate: dict[str, Any] | None
    dry_run_result: dict[str, Any] | None
    actor: str | None
    source: str
    safety: dict[str, Any] = field(default_factory=lambda: {
        "review_only": True,
        "executes_pipeline": False,
        "rawdata_readonly": True,
        "executor_called": False,
    })


# ── Hash ─────────────────────────────────────────────────────────────────────

def stable_hash(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA256 hex hash of a dict payload.

    Sorts keys and uses ensure_ascii=False for stable output regardless
    of Python version or platform.
    """
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Builder ──────────────────────────────────────────────────────────────────

def build_review_audit_record(
    event_type: str,
    plan: dict[str, Any],
    validation: dict[str, Any],
    approval: dict[str, Any] | None = None,
    approval_gate: dict[str, Any] | None = None,
    dry_run_result: dict[str, Any] | None = None,
    actor: str | None = None,
    source: str = "backend",
) -> ReviewAuditRecord:
    """Build a ReviewAuditRecord with stable hashes of plan/validation/approval."""
    return ReviewAuditRecord(
        audit_id=f"audit_{uuid.uuid4().hex[:16]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        event_type=event_type,
        plan_hash=stable_hash(plan),
        validation_hash=stable_hash(validation),
        approval_hash=stable_hash(approval) if approval else None,
        plan=plan,
        validation=validation,
        approval=approval,
        approval_gate=approval_gate,
        dry_run_result=dry_run_result,
        actor=actor,
        source=source,
    )


# ── Serializer ───────────────────────────────────────────────────────────────

def audit_record_to_dict(record: ReviewAuditRecord) -> dict[str, Any]:
    return {
        "audit_id": record.audit_id,
        "created_at": record.created_at,
        "event_type": record.event_type,
        "plan_hash": record.plan_hash,
        "validation_hash": record.validation_hash,
        "approval_hash": record.approval_hash,
        "plan": record.plan,
        "validation": record.validation,
        "approval": record.approval,
        "approval_gate": record.approval_gate,
        "dry_run_result": record.dry_run_result,
        "actor": record.actor,
        "source": record.source,
        "safety": record.safety,
    }


# ── Writer ───────────────────────────────────────────────────────────────────

def write_audit_record(record: ReviewAuditRecord, audit_dir: str | Path) -> Path:
    """Atomically write an audit record as JSON.

    Uses a temp file + replace to avoid partial writes.
    Does NOT overwrite existing records.
    """
    audit_dir = Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    target = audit_dir / f"{record.audit_id}.json"
    if target.exists():
        # Append a short suffix to avoid collision
        suffix = uuid.uuid4().hex[:6]
        target = audit_dir / f"{record.audit_id}_{suffix}.json"

    tmp = target.with_suffix(".tmp")
    data = audit_record_to_dict(record)
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)

    return target
