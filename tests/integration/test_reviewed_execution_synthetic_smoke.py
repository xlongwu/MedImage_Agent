"""CI-safe integration test for reviewed execution synthetic smoke.

Uses FastAPI TestClient to call POST /api/plans/execute-reviewed with
a mocked executor.  Verifies the full route → gate → writer → audit →
mocked executor chain without running real tools, MATLAB, SPM, DPABI,
or GPU.

The executor is monkeypatched — run_pipeline() is never actually called.
All file writes go to tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _write_config(tmp_path: Path) -> str:
    """Write a valid project_config.yaml to tmp_path. Returns the path."""
    cfg = tmp_path / "project_config.yaml"
    config = {
        "project": {"name": "ci_smoke", "description": "CI smoke test", "root_dir": "."},
        "runtime": {
            "work_dir": str(tmp_path / "work"),
            "log_dir": str(tmp_path / "logs"),
            "derivatives_dir": str(tmp_path / "derivatives"),
            "report_dir": str(tmp_path / "reports"),
        },
        "third_party": {
            "spm_dir": str(tmp_path / "third_party" / "spm"),
            "dpabi_dir": str(tmp_path / "third_party" / "dpabi"),
        },
        "safety": {
            "rawdata_readonly": True,
            "allow_overwrite_derivatives": False,
            "require_confirmation": True,
        },
    }
    cfg.write_text(yaml.safe_dump(config), encoding="utf-8")
    return str(cfg)


def _safe_plan():
    """Return a safe Python-only reviewed plan dict."""
    return {
        "pipeline_id": "synthetic_reviewed_smoke",
        "nodes": [
            {
                "id": "data_inspection",
                "backend": "python",
                "depends_on": [],
                "params": {},
            },
        ],
    }


def _unsafe_plan():
    """Return a plan with an SPM node that should be blocked."""
    return {
        "pipeline_id": "blocked_spm_plan",
        "nodes": [
            {
                "id": "spm_realign_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": {},
            },
        ],
    }


def _request_body(plan: dict, project_config_path: str, **overrides) -> dict:
    """Build a valid execute-reviewed request body."""
    body = {
        "plan": plan,
        "approval": {
            "approved": True,
            "approved_by": "ci-smoke",
            "approved_nodes": ["*"],
            "rejected_nodes": [],
        },
        "project_config_path": project_config_path,
        "dry_run": False,
        "confirm_execution": True,
        "persist_audit": True,
        "write_pipeline_yaml": True,
        "actor": "ci-smoke",
    }
    body.update(overrides)
    return body


# ══════════════════════════════════════════════════════════════════════════════
# Smoke: safe Python-only plan → EXECUTION_SUBMITTED
# ══════════════════════════════════════════════════════════════════════════════

def test_safe_plan_execution_submitted(monkeypatch, tmp_path):
    """Full integration: safe plan, mocked executor, check all gates."""
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")

    # ── Mock executor ──
    executor_calls = []

    def _fake_run_pipeline(project_config_path, pipeline_path):
        executor_calls.append({
            "project_config_path": project_config_path,
            "pipeline_path": pipeline_path,
        })
        return {"status": "SUCCESS", "run_id": "ci-mock-run-001"}

    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.run_pipeline",
        _fake_run_pipeline,
    )

    # ── Redirect file writes ──
    reviewed_dir = tmp_path / "reviewed_pipelines"
    audit_dir = tmp_path / "audit_records"
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.pipeline_writer.REVIEWED_PIPELINE_DIR",
        reviewed_dir,
    )
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.AUDIT_RECORD_DIR",
        audit_dir,
    )

    # ── Create config ──
    config_path = _write_config(tmp_path)

    # ── Call API ──
    resp = client.post(
        "/api/plans/execute-reviewed",
        json=_request_body(_safe_plan(), config_path),
    )

    # ── Assert ──
    assert resp.status_code == 200                                          # 1
    data = resp.json()

    assert data["status"] == "EXECUTION_SUBMITTED"                         # 2
    assert data["ok"] is True                                              # 3
    assert data["execution"]["executor_called"] is True                    # 4
    assert data["execution"]["submitted"] is True                          # 5
    assert data["execution"]["run_id"] is not None                         # 6
    assert data["execution"]["run_id"] == "ci-mock-run-001"                # 6b

    # ── Executor called once ──
    assert len(executor_calls) == 1                                         # 7
    call = executor_calls[0]
    assert call["project_config_path"] == config_path                      # 8
    assert Path(call["pipeline_path"]).exists()                            # 9

    # ── Pipeline YAML ──
    yaml_path = Path(call["pipeline_path"])
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))        # 10
    assert content is not None
    assert "version" in content                                            # 11
    assert "modality" in content
    assert "execution" in content
    assert "nodes" in content

    # ── Audit ──
    assert data["audit"]["persisted"] is True                              # 12
    assert "audit_id" in data["audit"]                                     # 13
    audit_files = list(audit_dir.glob("*.json"))
    assert len(audit_files) >= 1                                           # 14

    # ── No rawdata ──
    rawdata = tmp_path / "data"
    derivatives = tmp_path / "derivatives"
    assert not rawdata.exists() or list(rawdata.glob("*")) == []           # 15
    assert not derivatives.exists() or list(derivatives.glob("*")) == []   # 16

    # ── JSON serializable ──
    json.loads(resp.text)                                                  # 18


# ══════════════════════════════════════════════════════════════════════════════
# Blocked: unsafe SPM plan → EXECUTION_POLICY_BLOCKED
# ══════════════════════════════════════════════════════════════════════════════

def test_unsafe_spm_plan_blocked(monkeypatch, tmp_path):
    """SPM plan should be blocked by execution policy."""
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")

    executor_calls = []

    def _fake_run_pipeline(*args, **kwargs):
        executor_calls.append(1)
        return {"status": "SHOULD_NOT_BE_CALLED"}

    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.run_pipeline",
        _fake_run_pipeline,
    )

    reviewed_dir = tmp_path / "reviewed_pipelines"
    audit_dir = tmp_path / "audit_records"
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.pipeline_writer.REVIEWED_PIPELINE_DIR",
        reviewed_dir,
    )
    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.AUDIT_RECORD_DIR",
        audit_dir,
    )

    config_path = _write_config(tmp_path)
    resp = client.post(
        "/api/plans/execute-reviewed",
        json=_request_body(_unsafe_plan(), config_path),
    )

    data = resp.json()
    assert resp.status_code == 200
    # Policy blocked (SPM nodes are blocked by execution policy)
    assert data["status"] in ("EXECUTION_POLICY_BLOCKED",
                               "SAFE_EXECUTION_POLICY_BLOCKED",
                               "APPROVAL_GATE_BLOCKED")
    assert data["execution"]["executor_called"] is False
    assert len(executor_calls) == 0  # executor NOT called


# ══════════════════════════════════════════════════════════════════════════════
# dry_run=true regression
# ══════════════════════════════════════════════════════════════════════════════

def test_dry_run_true_does_not_call_executor(monkeypatch, tmp_path):
    """dry_run=true must never call the executor."""
    monkeypatch.setenv("MEDIMAGE_ENABLE_REVIEWED_EXECUTION", "1")

    executor_calls = []

    def _fake_run_pipeline(*args, **kwargs):
        executor_calls.append(1)
        return {"status": "SHOULD_NOT_BE_CALLED"}

    monkeypatch.setattr(
        "src.backend.app.api.execute_reviewed_routes.run_pipeline",
        _fake_run_pipeline,
    )

    config_path = _write_config(tmp_path)
    resp = client.post(
        "/api/plans/execute-reviewed",
        json=_request_body(_safe_plan(), config_path, dry_run=True),
    )

    data = resp.json()
    assert data["status"] == "DRY_RUN_OK"
    assert data["execution"]["executor_called"] is False
    assert len(executor_calls) == 0
