from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.app.main import app
from src.backend.app.runtime.execution_entry_inventory import (
    EXECUTION_ENTRY_INVENTORY,
)
from src.backend.app.services.mock_store import SQLiteDesktopStore


def test_every_inventory_entry_has_one_allowed_disposition():
    assert EXECUTION_ENTRY_INVENTORY
    assert len({entry.entry_id for entry in EXECUTION_ENTRY_INVENTORY}) == len(
        EXECUTION_ENTRY_INVENTORY
    )
    assert {entry.disposition for entry in EXECUTION_ENTRY_INVENTORY} <= {
        "gateway",
        "proposal/dry-run",
        "deprecated",
    }
    assert sum(entry.disposition == "gateway" for entry in EXECUTION_ENTRY_INVENTORY) == 1


def test_public_api_modules_do_not_import_pipeline_executor_directly():
    api_dir = Path("src/backend/app/api")
    offenders: list[str] = []
    for path in api_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "src.backend.app.runtime.pipeline_executor"
            ):
                offenders.append(str(path))
    assert offenders == []


def test_legacy_agent_execute_is_gone_and_audited(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "src.backend.app.api.execution_contract.store_module.mock_store",
        SQLiteDesktopStore(tmp_path / "legacy.sqlite"),
    )
    response = TestClient(app).post(
        "/api/agent/execute",
        json={
            "agent_run_id": "legacy",
            "project_config_path": "ignored.yaml",
            "pipeline_path": "ignored.yaml",
            "approved": True,
        },
    )
    assert response.status_code == 410
    detail = response.json()["detail"]
    assert detail["error_code"] == "EXECUTION_CONTRACT_REQUIRED"
    assert detail["replacement"] == "/api/plans/execute-reviewed"
    assert detail["audit_event_id"].startswith("ticket_event_")
