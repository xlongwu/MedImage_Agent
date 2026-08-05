"""Shared impact/provenance classification for executable node parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.backend.app.runtime.node_contract_registry import NODE_CONTRACTS

ParameterImpact = Literal["scientific", "safety", "operational"]


@dataclass(frozen=True)
class ParameterImpactRule:
    impact: ParameterImpact
    allowed_provenance: tuple[str, ...]
    confirmation_policy: str


_SAFETY = {
    "confirmations",
    "overwrite_policy",
    "allow_rawdata_write",
    "requires_approval",
}
_SCIENTIFIC = {
    "atlas",
    "atlas_path",
    "atlas_labels",
    "labels_path",
    "template",
    "tr",
    "fallback_tr",
    "low_hz",
    "high_hz",
    "model",
    "include_intercept",
    "include_linear_trend",
    "include_global_signal",
    "neighborhood",
    "use_gm_mask",
    "roi_count",
    "generate_seed_map",
    "stage_overrides",
    "compute_policy",
    "backend",
}


def classify_parameter(name: str, *, path_access: str | None = None) -> ParameterImpactRule:
    normalized = name.strip().casefold()
    if normalized in _SAFETY:
        return ParameterImpactRule(
            impact="safety",
            allowed_provenance=("current_lifecycle", "reviewed_plan", "static_governance"),
            confirmation_policy="never_from_memory",
        )
    if normalized in _SCIENTIFIC:
        return ParameterImpactRule(
            impact="scientific",
            allowed_provenance=("current_lifecycle", "project_context"),
            confirmation_policy="confirm_each_agent_task",
        )
    return ParameterImpactRule(
        impact="operational",
        allowed_provenance=("planner", "project_context", "current_lifecycle"),
        confirmation_policy="reviewed_plan",
    )


def build_parameter_registry() -> dict[str, dict[str, ParameterImpactRule]]:
    registry: dict[str, dict[str, ParameterImpactRule]] = {}
    for node_id, contract in NODE_CONTRACTS.items():
        if not contract.executable:
            continue
        registry[node_id] = {
            name: classify_parameter(name, path_access=parameter.path_access)
            for name, parameter in contract.parameter_schema.items()
        }
    return registry


SCIENTIFIC_PARAMETER_REGISTRY = build_parameter_registry()


def get_parameter_rule(node_id: str, parameter: str) -> ParameterImpactRule:
    """Return a parameter rule; unknown executable parameters fail closed."""

    contract = NODE_CONTRACTS.get(node_id)
    if contract is None or not contract.executable:
        raise KeyError(f"MEMORY_GUARD_NODE_NOT_EXECUTABLE: {node_id}")
    try:
        return SCIENTIFIC_PARAMETER_REGISTRY[node_id][parameter]
    except KeyError as exc:
        raise KeyError(
            f"MEMORY_GUARD_PARAMETER_UNCLASSIFIED: {node_id}.{parameter}"
        ) from exc


def registry_completeness_errors() -> list[str]:
    errors: list[str] = []
    for node_id, contract in NODE_CONTRACTS.items():
        if not contract.executable:
            continue
        missing = sorted(
            set(contract.parameter_schema)
            - set(SCIENTIFIC_PARAMETER_REGISTRY.get(node_id, {}))
        )
        if missing:
            errors.append(f"{node_id}: missing {missing}")
    return errors

