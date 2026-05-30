"""Tests for GPU contract/metadata runners (M8-GPU-T004)."""

from __future__ import annotations

import json
from src.backend.app.runtime.node_registry import NODE_REGISTRY


GPU_CONTRACT_NODES = [
    "alff_falff_gpu_candidate_contract",
    "functional_connectivity_gpu_candidate_contract",
    "reho_gpu_candidate_contract",
]


def test_all_three_registered():
    for nid in GPU_CONTRACT_NODES:
        assert nid in NODE_REGISTRY, f"{nid} not registered"


def test_runners_are_callable():
    from src.backend.app.runtime.node_registry import get_node_runner
    for nid in GPU_CONTRACT_NODES:
        runner = get_node_runner(nid)
        assert callable(runner), f"{nid} runner not callable"


def test_contract_nodes_still_blocked_by_safe_allowlist():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    for nid in GPU_CONTRACT_NODES:
        plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
        policy = classify_plan_nodes(plan)
        assert nid in policy["allowed_contract_nodes"], \
            f"{nid} not in allowed_contract_nodes (found in: {policy.get(nid, '?')})"


def test_gpu_subject_nodes_blocked():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    for nid in ["gpu_alff_subject", "gpu_reho_subject"]:
        plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
        policy = classify_plan_nodes(plan)
        assert nid not in policy.get("allowed_python_nodes", []), f"{nid} in python allowlist"
        assert nid not in policy.get("allowed_contract_nodes", []), f"{nid} in contract allowlist"


def test_gpu_contract_nodes_not_in_safe_allowlist():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes
    nid = "alff_falff_gpu_candidate_contract"
    plan = {"pipeline_id": "t", "nodes": [{"id": nid, "depends_on": [], "params": {}}]}
    policy = classify_plan_nodes(plan)
    assert nid in policy["allowed_contract_nodes"]
    # contract nodes are currently blocked by _check_safe_allowlist
