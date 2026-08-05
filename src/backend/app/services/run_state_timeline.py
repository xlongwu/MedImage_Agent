"""Read-only run-state timeline service — Phase 3 Productization.

Derives a standardized run/node state timeline from existing run
records, summary previews, events, and node state artifacts using
the Phase 3 ``execution_state.py`` helpers.

Pure read-only — never modifies executor state, writes files, or
calls external tools.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.backend.app.schemas.execution_state import (
    is_node_retry_eligible,
    is_node_reuse_eligible,
    is_node_terminal,
    is_run_resume_eligible,
    is_run_retry_eligible,
    is_run_terminal,
)

# ═══════════════════════════════════════════════════════════════════════
# 1. State normalization
# ═══════════════════════════════════════════════════════════════════════

_RUN_NORMALIZE_MAP: dict[str, str] = {
    "completed": "succeeded",
    "success": "succeeded",
    "succeeded": "succeeded",
    "failed": "failed",
    "execution_failed": "failed",
    "blocked": "blocked",
    "approval_gate_blocked": "blocked",
    "execution_policy_blocked": "blocked",
    "safe_execution_policy_blocked": "blocked",
    "submitted": "running",
    "running": "running",
    "partial": "partial",
    "timeout": "timeout",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "interrupted": "interrupted",
    "unknown": "unknown",
    "invalid": "unknown",
}


def normalize_run_state(status: str | None) -> str:
    """Map legacy / uppercase run statuses to Phase 3 ``RunState`` values.

    Unknown strings return ``"unknown"`` — never raises.
    """
    if not status:
        return "unknown"
    key = str(status).strip().lower()
    mapped = _RUN_NORMALIZE_MAP.get(key)
    if mapped:
        return mapped
    # Check if it's already a valid Phase 3 state (pass-through)
    if key in _RUN_NORMALIZE_MAP.values() or key in {
        "created", "queued", "preflight", "approval_required",
        "audit_required", "ready",
    }:
        return key
    return "unknown"


_NODE_NORMALIZE_MAP: dict[str, str] = {
    "success": "succeeded",
    "succeeded": "succeeded",
    "completed": "succeeded",
    "failed": "failed",
    "error": "failed",
    "skipped": "skipped",
    "running": "running",
    "blocked": "blocked",
    "timeout": "timeout",
    "reused": "reused",
    "invalidated": "invalidated",
    "pending": "pending",
    "unknown": "unknown",
}


def normalize_node_state(status: str | None) -> str:
    """Map legacy / uppercase node statuses to Phase 3 ``NodeState`` values.

    Unknown strings return ``"unknown"`` — never raises.
    """
    if not status:
        return "unknown"
    key = str(status).strip().lower()
    mapped = _NODE_NORMALIZE_MAP.get(key)
    if mapped:
        return mapped
    if key in _NODE_NORMALIZE_MAP.values() or key in {
        "preflight", "ready", "cancelled",
    }:
        return key
    return "unknown"


# ═══════════════════════════════════════════════════════════════════════
# 2. Timeline response models
# ═══════════════════════════════════════════════════════════════════════

class RunStateTimelineEvent(BaseModel):
    timestamp: str | None = None
    state: str
    source: str = "derived"
    message: str | None = None
    node_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeStateTimelineRecord(BaseModel):
    node_id: str
    state: str = "unknown"
    terminal: bool = False
    retry_eligible: bool = False
    reuse_eligible: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectRunStateTimelineResponse(BaseModel):
    ok: bool
    project_id: str
    run_id: str
    current_run_state: str = "unknown"
    terminal: bool = False
    retry_eligible: bool = False
    resume_eligible: bool = False
    events: list[RunStateTimelineEvent] = Field(default_factory=list)
    nodes: list[NodeStateTimelineRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# 3. Timeline builder
# ═══════════════════════════════════════════════════════════════════════

def build_run_state_timeline(
    *,
    project_id: str,
    run_id: str,
    run_link_status: str | None = None,
    created_at: str | None = None,
    summary_preview: dict[str, Any] | None = None,
    run_events: list[dict[str, Any]] | None = None,
    node_states_raw: list[dict[str, Any]] | None = None,
) -> ProjectRunStateTimelineResponse:
    """Build a standardized run-state timeline from existing metadata.

    All inputs are optional — the function derives as much as it can
    from available data.  Never writes files or modifies state.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # ── Normalize run state ────────────────────────────────────────────
    # Priority: summary_preview.status > run_link_status
    raw_status = None
    if summary_preview and summary_preview.get("status"):
        raw_status = summary_preview["status"]
    elif run_link_status:
        raw_status = run_link_status

    current_run_state = normalize_run_state(raw_status)

    # ── Classify state ─────────────────────────────────────────────────
    terminal = is_run_terminal(current_run_state)
    retry_eligible = is_run_retry_eligible(current_run_state)
    resume_eligible = is_run_resume_eligible(current_run_state)

    # ── Build events ───────────────────────────────────────────────────
    events: list[RunStateTimelineEvent] = []

    # Run link creation event
    if created_at:
        events.append(RunStateTimelineEvent(
            timestamp=created_at,
            state="created",
            source="run_link",
            message="Run link created.",
        ))

    # Summary-based events
    if summary_preview:
        started = summary_preview.get("started_at")
        finished = summary_preview.get("finished_at")
        if started:
            events.append(RunStateTimelineEvent(
                timestamp=started,
                state="running",
                source="summary",
                message="Pipeline execution started.",
            ))
        if finished:
            events.append(RunStateTimelineEvent(
                timestamp=finished,
                state=current_run_state,
                source="summary",
                message=f"Pipeline finished: {current_run_state}.",
                metadata={"raw_status": raw_status},
            ))

        for warn_msg in summary_preview.get("warnings", [])[:10]:
            events.append(RunStateTimelineEvent(
                timestamp=finished,
                state=current_run_state,
                source="summary",
                message=str(warn_msg),
                metadata={"severity": "warning"},
            ))

    # Events from existing event pipeline
    if run_events:
        for ev in run_events[:30]:
            ts = ev.get("timestamp")
            msg = ev.get("message", "")
            level = ev.get("level", "info")
            nid = ev.get("node_id")
            events.append(RunStateTimelineEvent(
                timestamp=ts,
                state=current_run_state,
                source=ev.get("source", "derived"),
                message=msg,
                node_id=nid,
                metadata={"level": level},
            ))

    def _event_sort_key(event: RunStateTimelineEvent) -> tuple[int, str, int]:
        if not event.timestamp:
            return (1, "", 0)
        try:
            normalized = event.timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            timestamp = parsed.astimezone(UTC).isoformat()
        except (TypeError, ValueError):
            timestamp = event.timestamp
        state_order = {"created": 0, "running": 1}.get(event.state, 2)
        return (0, timestamp, state_order)

    events.sort(key=_event_sort_key)

    # ── Build node records ─────────────────────────────────────────────
    nodes: list[NodeStateTimelineRecord] = []

    # From summary_preview node_results
    if summary_preview:
        node_results = summary_preview.get("node_results") or []
        if isinstance(node_results, list):
            for nr in node_results[:50]:
                if not isinstance(nr, dict):
                    continue
                nid = nr.get("node_id") or nr.get("node") or "unknown"
                raw_ns = nr.get("status") or ("SUCCESS" if nr.get("ok") else "FAILED")
                ns = normalize_node_state(str(raw_ns))
                nodes.append(NodeStateTimelineRecord(
                    node_id=str(nid),
                    state=ns,
                    terminal=is_node_terminal(ns),
                    retry_eligible=is_node_retry_eligible(ns),
                    reuse_eligible=is_node_reuse_eligible(ns),
                    warnings=[str(w) for w in (nr.get("warnings") or [])[:5]],
                    errors=[str(e) for e in (nr.get("errors") or [])[:5]],
                ))

    # From explicit node_states_raw
    if node_states_raw:
        for nsr in node_states_raw[:50]:
            if not isinstance(nsr, dict):
                continue
            nid = nsr.get("node_id") or nsr.get("node") or "unknown"
            # Skip if already present from summary
            if any(n.node_id == str(nid) for n in nodes):
                continue

            # Check if this is a normalized Phase 3 node-state artifact
            schema_v = nsr.get("schema_version", "")
            if isinstance(schema_v, str) and schema_v.startswith("phase3-node-state"):
                # Use normalized fields directly
                raw_state = nsr.get("state") or "unknown"
                ns = normalize_node_state(str(raw_state))
                # Prefer artifact's computed booleans, fall back to helpers
                terminal_v = nsr.get("terminal")
                retry_v = nsr.get("retry_eligible")
                reuse_v = nsr.get("reuse_eligible")
                nodes.append(NodeStateTimelineRecord(
                    node_id=str(nid),
                    state=ns,
                    terminal=bool(terminal_v) if isinstance(terminal_v, bool) else is_node_terminal(ns),
                    retry_eligible=bool(retry_v) if isinstance(retry_v, bool) else is_node_retry_eligible(ns),
                    reuse_eligible=bool(reuse_v) if isinstance(reuse_v, bool) else is_node_reuse_eligible(ns),
                    warnings=[str(w) for w in (nsr.get("warnings") or [])[:5]],
                    errors=[str(e) for e in (nsr.get("errors") or [])[:5]],
                ))
                continue

            # Legacy node state: normalize from status field
            raw_ns = nsr.get("status") or "unknown"
            ns = normalize_node_state(str(raw_ns))
            nodes.append(NodeStateTimelineRecord(
                node_id=str(nid),
                state=ns,
                terminal=is_node_terminal(ns),
                retry_eligible=is_node_retry_eligible(ns),
                reuse_eligible=is_node_reuse_eligible(ns),
                warnings=[str(w) for w in (nsr.get("warnings") or [])[:5]],
                errors=[str(e) for e in (nsr.get("errors") or [])[:5]],
            ))

    # If no nodes but we have a current state, add a synthetic node
    if not nodes:
        nodes.append(NodeStateTimelineRecord(
            node_id="pipeline",
            state=current_run_state,
            terminal=terminal,
            retry_eligible=retry_eligible,
            reuse_eligible=False,
            metadata={"synthetic": True},
        ))

    return ProjectRunStateTimelineResponse(
        ok=True,
        project_id=project_id,
        run_id=run_id,
        current_run_state=current_run_state,
        terminal=terminal,
        retry_eligible=retry_eligible,
        resume_eligible=resume_eligible,
        events=events,
        nodes=nodes,
        warnings=warnings,
        errors=errors,
    )
