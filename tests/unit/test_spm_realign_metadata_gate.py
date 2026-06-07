"""Tests for SPM realign metadata gate and params schema."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.planner.plan_validator import validate_plan
from src.backend.app.runtime.tool_catalog import get_tool_catalog_item
from src.backend.app.services.spm_realign_params import (
    default_spm_realign_params,
    validate_spm_realign_params,
)


# ── Tool Catalog metadata tests ──────────────────────────────────────────────


def test_spm_realign_in_tool_catalog():
    item = get_tool_catalog_item("spm_realign_subject")
    assert item.id == "spm_realign_subject"
    assert item.backend == "matlab-spm"
    assert item.requires_approval is True
    assert item.manual_required is True
    assert item.risk_level == "high"
    assert "not-executable" in item.tags or "not executable" in item.description.lower()
    assert "BOLD NIfTI" in " ".join(item.inputs)
    assert "rp_*.txt" in " ".join(item.outputs) or "motion parameters" in " ".join(item.outputs)


# ── Params validation tests ──────────────────────────────────────────────────


def test_default_params_validate():
    params, warnings, errors = validate_spm_realign_params(None)
    assert len(errors) == 0
    assert len(warnings) == 0
    assert params["quality"] == 0.9
    assert params["wrap"] == [0, 0, 0]
    assert params["weight_image"] is None


def test_default_params_validate_explicit():
    params, warnings, errors = validate_spm_realign_params(default_spm_realign_params())
    assert len(errors) == 0


def test_quality_out_of_range():
    _, _, errors = validate_spm_realign_params({"quality": 1.5})
    assert len(errors) >= 1
    assert any("quality" in e for e in errors)

    _, _, errors = validate_spm_realign_params({"quality": 0})
    assert len(errors) >= 1

    _, _, errors = validate_spm_realign_params({"quality": -0.1})
    assert len(errors) >= 1


def test_negative_separation_rejected():
    _, _, errors = validate_spm_realign_params({"separation_mm": -1})
    assert len(errors) >= 1


def test_invalid_wrap_rejected():
    _, _, errors = validate_spm_realign_params({"wrap": [0, 0]})
    assert len(errors) >= 1

    _, _, errors = validate_spm_realign_params({"wrap": [0, 0, 0, 0]})
    assert len(errors) >= 1

    _, _, errors = validate_spm_realign_params({"wrap": [0, 2, 0]})
    assert len(errors) >= 1


def test_invalid_interpolation_rejected():
    _, _, errors = validate_spm_realign_params({"interpolation": 99})
    assert len(errors) >= 1


def test_unknown_param_rejected():
    _, _, errors = validate_spm_realign_params({"arbitrary_param": "value"})
    assert len(errors) >= 1
    assert any("Unknown" in e for e in errors)


def test_absolute_weight_image_rejected():
    _, _, errors = validate_spm_realign_params({"weight_image": "C:\\absolute\\path.nii"})
    assert len(errors) >= 1

    _, _, errors = validate_spm_realign_params({"weight_image": "/absolute/path.nii"})
    assert len(errors) >= 1


# ── Validator / plan tests ───────────────────────────────────────────────────


def test_plan_with_spm_realign_is_known():
    plan = {
        "pipeline_id": "test_spm_realign",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": default_spm_realign_params(),
            },
        ],
    }
    result = validate_plan(plan)
    # Must be recognized — not unknown
    assert "spm_realign_subject" not in result.unknown_nodes
    # Must be flagged as requiring approval and high risk
    assert "spm_realign_subject" in result.approval_required_nodes
    assert "spm_realign_subject" in result.high_risk_nodes
    assert result.risk_summary.get("requires_approval") is True


def test_tool_catalog_client():
    """Verify the HTTP catalog endpoint returns spm_realign_subject."""
    client = TestClient(app)
    resp = client.get("/api/tools/catalog/spm_realign_subject")
    assert resp.status_code == 200
    item = resp.json()["item"]
    assert item["backend"] == "matlab-spm"
    assert item["requires_approval"] is True
    assert item["risk_level"] == "high"
    assert "not-executable" in item["tags"]


# ── Validator integration tests ──────────────────────────────────────────────


def test_plan_with_valid_spm_params_validates():
    plan = {
        "pipeline_id": "test_spm_param_valid",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": default_spm_realign_params(),
            },
        ],
    }
    result = validate_plan(plan)
    assert result.ok is True
    # Should not have SPM_REALIGN_PARAM_INVALID errors
    spm_errors = [e for e in result.errors if e.code == "SPM_REALIGN_PARAM_INVALID"]
    assert len(spm_errors) == 0, f"Unexpected SPM param errors: {[e.message for e in spm_errors]}"
    # Should have the non-executable warning
    ne_warnings = [w for w in result.warnings if w.code == "SPM_REALIGN_NODE_NOT_EXECUTABLE"]
    assert len(ne_warnings) >= 1


def test_plan_with_invalid_quality_fails_validation():
    plan = {
        "pipeline_id": "test_spm_bad_quality",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": {"quality": 1.5},
            },
        ],
    }
    result = validate_plan(plan)
    assert result.ok is False
    spm_errors = [e for e in result.errors if e.code == "SPM_REALIGN_PARAM_INVALID"]
    assert len(spm_errors) >= 1
    assert any("quality" in e.message for e in spm_errors)


def test_plan_with_invalid_wrap_fails_validation():
    plan = {
        "pipeline_id": "test_spm_bad_wrap",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": {"wrap": [0, 1]},
            },
        ],
    }
    result = validate_plan(plan)
    assert result.ok is False
    spm_errors = [e for e in result.errors if e.code == "SPM_REALIGN_PARAM_INVALID"]
    assert len(spm_errors) >= 1


def test_plan_with_absolute_weight_image_fails_validation():
    plan = {
        "pipeline_id": "test_spm_bad_weight",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": {"weight_image": "C:\\unsafe\\path.nii"},
            },
        ],
    }
    result = validate_plan(plan)
    assert result.ok is False
    spm_errors = [e for e in result.errors if e.code == "SPM_REALIGN_PARAM_INVALID"]
    assert len(spm_errors) >= 1


def test_plan_with_traversal_weight_image_fails_validation():
    plan = {
        "pipeline_id": "test_spm_traversal_weight",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": {"weight_image": "../weight.nii"},
            },
        ],
    }
    result = validate_plan(plan)
    assert result.ok is False
    spm_errors = [e for e in result.errors if e.code == "SPM_REALIGN_PARAM_INVALID"]
    assert len(spm_errors) >= 1


def test_plan_with_unknown_param_fails_validation():
    plan = {
        "pipeline_id": "test_spm_unknown_param",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": {"matlab_script": "evil()", "shell_command": "rm -rf /"},
            },
        ],
    }
    result = validate_plan(plan)
    assert result.ok is False
    spm_errors = [e for e in result.errors if e.code == "SPM_REALIGN_PARAM_INVALID"]
    assert len(spm_errors) >= 1


def test_plan_approval_and_high_risk_still_reported():
    """Even with valid SPM params, approval + high-risk are still flagged."""
    plan = {
        "pipeline_id": "test_spm_risk",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": default_spm_realign_params(),
            },
        ],
    }
    result = validate_plan(plan)
    assert "spm_realign_subject" in result.approval_required_nodes
    assert "spm_realign_subject" in result.high_risk_nodes
    assert result.risk_summary["requires_approval"] is True
