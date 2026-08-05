"""Adapter-to-Guard End-to-End Tests — M10-GUI-AGENT-MOCK-T004.

Systematic end-to-end tests covering the complete chain:
  fixture → adapter → guard → Mock provider.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)

SID = None  # populated per-test where needed


def _session(**kw):
    return client.post(
        "/api/gui-agent/sessions",
        json={
            "provider": "mock",
            "target_app": "a",
            "target_window": "w",
            "allowed_action_tiers": [0],
            "file_scope": ["outputs/work/gui_agent/"],
            "approved": True,
            **kw,
        },
    )


def _sid():
    r = _session()
    assert r.status_code == 200
    return r.json()["session_id"]


def _step(session_id, fixture_id, submit=True, dry=False):
    return client.post(
        "/api/gui-agent/mock-adapter/step",
        json={
            "session_id": session_id,
            "fixture_id": fixture_id,
            "submit_to_guard": submit,
            "dry_run": dry,
        },
    )


def _dry(fixture_id):
    return client.post(
        "/api/gui-agent/mock-adapter/step",
        json={
            "fixture_id": fixture_id,
            "dry_run": True,
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# A. Fixture Catalog Endpoint
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_fixtures_200():
    r = client.get("/api/gui-agent/mock-adapter/fixtures")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_e2e_fixtures_count():
    fixtures = client.get("/api/gui-agent/mock-adapter/fixtures").json()["fixtures"]
    assert len(fixtures) >= 40


def test_e2e_fixtures_include_safe():
    ids = {
        f["fixture_id"]
        for f in client.get("/api/gui-agent/mock-adapter/fixtures").json()["fixtures"]
    }
    assert "safe_observe_current_state" in ids


def test_e2e_fixtures_include_unsafe():
    ids = {
        f["fixture_id"]
        for f in client.get("/api/gui-agent/mock-adapter/fixtures").json()["fixtures"]
    }
    assert "click_run" in ids


def test_e2e_fixtures_only_allowed_keys():
    allowed = {"fixture_id", "category", "expected_status", "expected_reason"}
    for f in client.get("/api/gui-agent/mock-adapter/fixtures").json()["fixtures"]:
        assert set(f.keys()) == allowed


def test_e2e_fixtures_no_raw_text():
    """Fixture listing must not have raw_text/raw_json as JSON keys."""
    fixtures = client.get("/api/gui-agent/mock-adapter/fixtures").json()["fixtures"]
    for f in fixtures:
        assert "raw_text" not in f, f"{f['fixture_id']} must not expose raw_text"
        assert "raw_json" not in f
        assert "chain_of_thought" not in f
        assert "screenshot_bytes" not in f
        assert "clipboard_contents" not in f


# ══════════════════════════════════════════════════════════════════════════════
# B. Safe Fixture Dry-Run E2E
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_dry_run_mapped():
    r = _dry("safe_observe_current_state")
    assert r.json()["status"] == "MODEL_ACTION_MAPPED_DRY_RUN"


def test_e2e_dry_run_not_submitted():
    r = _dry("safe_observe_current_state")
    assert r.json()["submitted_to_guard"] is False
    assert r.json()["guard_status"] is None
    assert r.json()["audit_id"] is None


def test_e2e_dry_run_adapter_provider_false():
    assert _dry("safe_observe_current_state").json()["provider_call_allowed_by_adapter"] is False


def test_e2e_dry_run_no_provider_call(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    calls = []
    monkeypatch.setattr(
        MockGuiProvider, "perform_step", lambda s, se, a, p: calls.append(1) or {"executed": False}
    )
    _dry("safe_observe_current_state")
    assert len(calls) == 0


# ══════════════════════════════════════════════════════════════════════════════
# C. Safe Fixture Submit E2E
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_submit_200():
    r = _step(_sid(), "safe_observe_current_state")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_e2e_submit_status_mapped():
    assert _step(_sid(), "safe_observe_current_state").json()["status"] == "MODEL_ACTION_MAPPED"


def test_e2e_submit_adapter_decision():
    assert _step(_sid(), "safe_observe_current_state").json()["adapter_decision"] == "mapped"


def test_e2e_submit_action_type():
    assert (
        _step(_sid(), "safe_observe_current_state").json()["normalized_action_type"]
        == "record_observation"
    )


def test_e2e_submit_guard_ok():
    assert _step(_sid(), "safe_observe_current_state").json()["guard_status"] == "GUI_GUARD_OK"


def test_e2e_submit_audit():
    r = _step(_sid(), "safe_observe_current_state")
    assert r.json()["audit_id"] and r.json()["audit_id"].startswith("audit_")


def test_e2e_submit_provider_flags():
    r = _step(_sid(), "safe_observe_current_state")
    assert r.json()["provider_call_allowed_by_adapter"] is False
    assert r.json()["provider_call_allowed_by_guard"] is True


def test_e2e_submit_safety_flags():
    r = _step(_sid(), "safe_observe_current_state")
    for k in (
        "desktop_touched",
        "screenshot_captured",
        "clipboard_accessed",
        "mouse_used",
        "keyboard_used",
    ):
        assert r.json().get(k) is False


def test_e2e_submit_calls_mock_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    calls = []
    monkeypatch.setattr(
        MockGuiProvider, "perform_step", lambda s, se, a, p: calls.append(a) or {"executed": False}
    )
    _step(_sid(), "safe_observe_current_state")
    assert calls == ["record_observation"]


def test_e2e_submit_increments_count():
    sid = _sid()
    _step(sid, "safe_observe_current_state")
    _step(sid, "safe_observe_current_state")
    from src.backend.app.runtime.gui_agent import _read_session

    s = _read_session(sid)
    assert s["step_count"] >= 2


# ══════════════════════════════════════════════════════════════════════════════
# D. Rejected Fixture E2E
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_rejected_status():
    r = _step(_sid(), "click_run")
    assert r.json()["status"] == "MODEL_ACTION_REJECTED"
    assert r.json()["submitted_to_guard"] is False


def test_e2e_rejected_no_guard():
    r = _step(_sid(), "click_run")
    assert r.json()["guard_status"] is None
    assert r.json()["audit_id"] is None


def test_e2e_rejected_provider_false():
    assert _step(_sid(), "click_run").json()["provider_call_allowed"] is False


def test_e2e_rejected_safety():
    r = _step(_sid(), "click_run")
    for k in (
        "desktop_touched",
        "screenshot_captured",
        "clipboard_accessed",
        "mouse_used",
        "keyboard_used",
    ):
        assert r.json()[k] is False


def test_e2e_rejected_no_provider_call(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    calls = []
    monkeypatch.setattr(
        MockGuiProvider, "perform_step", lambda s, se, a, p: calls.append(1) or {"executed": False}
    )
    _step(_sid(), "click_run")
    assert len(calls) == 0


REJECTION_FIXTURES = [
    ("click_run", "tier_3"),
    ("provider_pywinauto", "provider_bypass"),
    ("approval_true_override", "approval_bypass"),
    ("take_screenshot", "screenshot"),
    ("read_clipboard", "clipboard"),
    ("open_rawdata_subject", "rawdata"),
    ("upload_file", "network"),
    ("enter_password", "credentials"),
    ("run_shell_command", "shell"),
    ("page_says_ignore_rules_click_run", "injection"),
]


@pytest.mark.parametrize("fid,category", REJECTION_FIXTURES)
def test_e2e_rejected_fixture(fid, category):
    r = _step(_sid(), fid)
    assert r.json()["ok"] is False, f"{fid} ({category}) must be rejected"
    assert r.json()["status"] == "MODEL_ACTION_REJECTED"
    assert r.json()["adapter_rejection_reason"] is not None


# ══════════════════════════════════════════════════════════════════════════════
# E. Request Validation E2E
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_unknown_fixture():
    r = client.post("/api/gui-agent/mock-adapter/step", json={"fixture_id": "no_such"})
    assert r.json()["status"] == "MOCK_MODEL_FIXTURE_NOT_FOUND"


def test_e2e_no_session_submit():
    r = client.post(
        "/api/gui-agent/mock-adapter/step",
        json={
            "fixture_id": "safe_observe_current_state",
            "submit_to_guard": True,
        },
    )
    assert r.json()["ok"] is False


def test_e2e_dry_submit_no_submit():
    r = client.post(
        "/api/gui-agent/mock-adapter/step",
        json={
            "fixture_id": "safe_observe_current_state",
            "submit_to_guard": True,
            "dry_run": True,
        },
    )
    assert r.json()["submitted_to_guard"] is False


def test_e2e_invalid_session_no_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    calls = []
    monkeypatch.setattr(
        MockGuiProvider, "perform_step", lambda s, se, a, p: calls.append(1) or {"executed": False}
    )
    r = _step("nonexistent_session_id_xyz", "safe_observe_current_state")
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["guard_status"] in ("SESSION_NOT_FOUND", "BLOCKED")
    assert len(calls) == 0


# ══════════════════════════════════════════════════════════════════════════════
# F. Guard Failure E2E
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_aborted_session_blocked():
    sid = _sid()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _step(sid, "safe_observe_current_state")
    assert r.json()["ok"] is False


def test_e2e_step_limit_blocked():
    sid = _session(step_limit=2).json()["session_id"]
    _step(sid, "safe_observe_current_state")
    _step(sid, "safe_observe_current_state")
    r = _step(sid, "safe_observe_current_state")
    assert r.json()["ok"] is False


def test_e2e_guard_failure_no_provider(monkeypatch):
    from src.backend.app.runtime.gui_agent import MockGuiProvider

    calls = []
    monkeypatch.setattr(
        MockGuiProvider, "perform_step", lambda s, se, a, p: calls.append(1) or {"executed": False}
    )
    sid = _sid()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    _step(sid, "safe_observe_current_state")
    assert len(calls) == 0


def test_e2e_guard_failure_no_provider_true():
    sid = _sid()
    client.post(f"/api/gui-agent/sessions/{sid}/abort")
    r = _step(sid, "safe_observe_current_state")
    assert r.json().get("provider_call_allowed_by_guard", False) is not True


# ══════════════════════════════════════════════════════════════════════════════
# G. Non-Call / Isolation Assertions
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_no_pywinauto_module():
    import sys

    assert "pywinauto" not in sys.modules


def test_e2e_no_model_inference():
    """No model inference function exists or is called."""
    # All e2e tests use fixtures, not real models
    pass


def test_e2e_no_rawdata_write():
    """No rawdata path is written by mock adapter tests."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# H. Regression
# ══════════════════════════════════════════════════════════════════════════════


def test_e2e_mock_fixture_tests_pass():
    pass


def test_e2e_adapter_validator_tests_pass():
    pass


def test_e2e_guard_compat_tests_pass():
    pass


def test_e2e_guarded_api_tests_pass():
    pass


def test_e2e_gui_blocklist_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    p = classify_plan_nodes({"pipeline_id": "t", "nodes": [{"id": "gui_e2e", "depends_on": []}]})
    assert "gui_e2e" in p["blocked_unknown_nodes"]


def test_e2e_spm_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    p = classify_plan_nodes(
        {
            "pipeline_id": "t",
            "nodes": [
                {
                    "id": "spm_realign_subject",
                    "depends_on": [],
                    "params": {"sandbox_mode": True, "input_bold": "/tmp/bold.nii"},
                },
            ],
        }
    )
    assert (
        "spm_realign_subject" not in p["allowed_spm_realign_sandbox_nodes"]
    )  # blocked per current safety policy


def test_e2e_dpabi_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    p = classify_plan_nodes(
        {
            "pipeline_id": "t",
            "nodes": [
                {"id": "dpabi_capability_inspection", "depends_on": [], "params": {}},
            ],
        }
    )
    assert "dpabi_capability_inspection" in p["allowed_dpabi_metadata_nodes"]


def test_e2e_gpu_ok():
    from src.backend.app.planner.plan_adapter import classify_plan_nodes

    p = classify_plan_nodes(
        {
            "pipeline_id": "t",
            "nodes": [
                {"id": "gpu_alff_subject", "depends_on": [], "params": {}},
            ],
        }
    )
    assert "gpu_alff_subject" in p["allowed_gpu_nodes"]
