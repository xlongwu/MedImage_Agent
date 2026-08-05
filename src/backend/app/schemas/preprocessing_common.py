"""Shared execution-status semantics for preprocessing sandbox services.

Single authoritative definition of the layered execution status enum so the
sandbox execution services do not overload a single ``succeeded/failed``
string to mean both "sandbox prepared" and "numeric result produced".
"""

from __future__ import annotations

from enum import StrEnum


class ExecutionStatus(StrEnum):
    """Layered status distinguishing sandbox scaffolding from numeric output.

    Ordered from least to most real. Read-side code should treat anything below
    ``NUMERICALLY_COMPUTED`` as "no real metric artifact produced yet".
    """

    PLANNED = "planned"
    DRY_RUN_READY = "dry_run_ready"
    SANDBOX_PREPARED = "sandbox_prepared"
    METADATA_ONLY = "metadata_only"
    PARTIALLY_COMPUTED = "partially_computed"
    NUMERICALLY_COMPUTED = "numerically_computed"
    VALIDATED = "validated"
    REGISTERED = "registered"
    FAILED = "failed"


def normalize_legacy_status(raw: str) -> str:
    """Map historical status strings onto the layered enum values.

    Older manifests/services used ``succeeded``/``warning``/``failed``. This
    keeps reads backward compatible without rewriting historical artifacts.
    """
    if not raw:
        return ExecutionStatus.METADATA_ONLY.value
    mapping = {
        "succeeded": ExecutionStatus.NUMERICALLY_COMPUTED.value,
        "warning": ExecutionStatus.METADATA_ONLY.value,
        "disabled": ExecutionStatus.FAILED.value,
        "blocked": ExecutionStatus.FAILED.value,
        "failed": ExecutionStatus.FAILED.value,
    }
    if raw in mapping:
        return mapping[raw]
    # Already an enum value, or an unknown value: pass through.
    return raw


def is_numeric_status(status: str) -> bool:
    """True only when a real numeric artifact has been produced/validated."""
    return status in {
        ExecutionStatus.NUMERICALLY_COMPUTED.value,
        ExecutionStatus.VALIDATED.value,
        ExecutionStatus.REGISTERED.value,
    }
