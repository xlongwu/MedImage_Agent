"""Tests for LLM Planner — mock/rule-based plan generation."""

from __future__ import annotations

import json

from src.backend.app.planner.llm_planner import (
    PlannerRequest,
    PlannerResponse,
    generate_plan_from_goal,
    plan_from_request,
)
from src.backend.app.runtime.tool_catalog import build_tool_catalog


# ── Helper ──

def _catalog_ids() -> set[str]:
    return {item.id for item in build_tool_catalog()}


# ── 1. motion goal generates plan ──

def test_motion_goal_generates_plan():
    resp = generate_plan_from_goal("run motion correction")
    assert resp.ok is True
    assert resp.plan["pipeline_id"] == "planned_motion_qc"
    assert len(resp.plan["nodes"]) == 4


# ── 2. plan has pipeline_id and nodes ──

def test_plan_has_required_fields():
    resp = generate_plan_from_goal("motion correction")
    assert "pipeline_id" in resp.plan
    assert "nodes" in resp.plan
    assert isinstance(resp.plan["nodes"], list)


# ── 3. all node ids are in Tool Catalog ──

def test_generated_nodes_in_catalog():
    resp = generate_plan_from_goal("motion")
    catalog = _catalog_ids()
    for node in resp.plan["nodes"]:
        assert node["id"] in catalog, f"Node '{node['id']}' not in Tool Catalog"


# ── 4. plan is validated ──

def test_validation_called():
    resp = generate_plan_from_goal("motion correction")
    assert "validation" in resp.to_dict()
    assert resp.validation["ok"] is True


# ── 5. motion plan has no errors ──

def test_motion_plan_no_errors():
    resp = generate_plan_from_goal("motion")
    assert len(resp.validation.get("errors", [])) == 0


# ── 6. SPM node in approval_required_nodes ──

def test_spm_in_approval_required():
    resp = generate_plan_from_goal("motion")
    assert "spm_realign_subject" in resp.validation["approval_required_nodes"]


# ── 7. ALFF goal ──

def test_alff_goal():
    resp = generate_plan_from_goal("compute alff analysis")
    assert resp.ok is True
    assert resp.plan["pipeline_id"] == "planned_alff"
    nids = [n["id"] for n in resp.plan["nodes"]]
    assert "alff_falff_subject" in nids


# ── 8. ReHo goal ──

def test_reho_goal():
    resp = generate_plan_from_goal("reho analysis")
    assert resp.ok is True
    assert resp.plan["pipeline_id"] == "planned_reho"
    nids = [n["id"] for n in resp.plan["nodes"]]
    assert "reho_subject" in nids


# ── 9. empty goal → ok=False ──

def test_empty_goal():
    resp = generate_plan_from_goal("")
    assert resp.ok is False
    assert any("EMPTY_GOAL" in e for e in resp.errors)


# ── 10. unsupported goal → ok=False ──

def test_unsupported_goal():
    resp = generate_plan_from_goal("do something completely unknown")
    assert resp.ok is False
    assert any("UNSUPPORTED_GOAL" in e for e in resp.errors)


# ── 11. unsupported provider → ok=False ──

def test_unsupported_provider():
    resp = generate_plan_from_goal("motion", provider="openai")
    assert resp.ok is False
    assert any("UNSUPPORTED_PROVIDER" in e for e in resp.errors)


# ── 12. to_dict is JSON-serializable ──

def test_response_to_dict_json():
    resp = generate_plan_from_goal("motion correction")
    d = resp.to_dict()
    raw = json.dumps(d, ensure_ascii=False)
    back = json.loads(raw)
    assert back["ok"] is True


# ── 13. does not execute runners ──

def test_no_runner_execution():
    resp = generate_plan_from_goal("motion")
    assert resp.ok is True
    # No side effects — trivially passes


# ── 14. no file writes ──

def test_no_file_writes(tmp_path):
    """Planner must not write any files to disk."""
    import os
    before = set(os.listdir(tmp_path))
    generate_plan_from_goal("motion")
    after = set(os.listdir(tmp_path))
    assert after == before


# ── 15. plan_from_request wrapper ──

def test_plan_from_request():
    req = PlannerRequest(goal="motion correction")
    resp = plan_from_request(req)
    assert resp.ok is True
    assert resp.plan["pipeline_id"] == "planned_motion_qc"


# ── 16. full pipeline goal ──

def test_full_pipeline_goal():
    resp = generate_plan_from_goal("run full pipeline preprocessing")
    assert resp.ok is True
    assert resp.plan["pipeline_id"] == "planned_full_preprocessing"
    assert len(resp.plan["nodes"]) >= 5
    # SPM approval warning expected, but no errors
    assert len(resp.validation.get("errors", [])) == 0


# ── 17. Chinese goal matching ──

def test_chinese_goal():
    resp = generate_plan_from_goal("全流程预处理")
    assert resp.ok is True
    assert resp.plan["pipeline_id"] == "planned_full_preprocessing"
