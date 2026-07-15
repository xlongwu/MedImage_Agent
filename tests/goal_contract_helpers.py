from __future__ import annotations

from typing import Any

from src.backend.app.planner.goal_contract_builder import (
    build_goal_contract_semantics,
)


def reviewed_goal_candidate(plan: dict[str, Any], goal_text: str) -> dict[str, Any]:
    """Return explicit review input for tests that exercise real execution.

    The production builder may decline an ambiguous legacy goal. Tests that
    intentionally exercise those plans still need a human-review analogue, so
    the fallback binds terminal and node-status criteria without claiming a
    scientific artifact or capability level.
    """
    built = build_goal_contract_semantics(plan, goal_text)
    if built.ok and built.semantics is not None:
        return built.semantics
    node_ids = [
        str(node["id"])
        for node in plan.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    ]
    return {
        "goal_text": goal_text,
        "goal_kind": "reviewed_execution_boundary",
        "scope": {"completeness_required": True},
        "criteria": [
            {
                "criterion_id": "reviewed-pipeline-terminal",
                "criterion_type": "pipeline_terminal",
                "target": "pipeline",
                "required_evidence": ["pipeline_summary", "node_states"],
                "expected": {
                    "statuses": ["SUCCESS", "COMPLETED"],
                    "active_nodes": 0,
                },
                "failure_semantics": "indeterminate_if_source_incomplete",
            },
            {
                "criterion_id": "reviewed-node-status",
                "criterion_type": "node_status",
                "target": "required_nodes",
                "required_evidence": ["node_states"],
                "expected": {
                    "node_ids": node_ids,
                    "statuses": ["SUCCESS", "COMPLETED"],
                },
                "failure_semantics": "indeterminate_if_source_incomplete",
            },
        ],
        "minimum_capability_level": "unavailable",
        "builder_source": "explicit_test_review",
    }
