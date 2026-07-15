"""Real-data sandbox and workflow route handlers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from src.backend.app.api.execution_contract import reject_execution_contract

router = APIRouter()


@router.post("/api/real-data/inspect")
async def real_data_inspect(request: dict[str, Any]):
    """Inspect a real dataset directory and generate data inventory."""
    from src.backend.app.tools.real_data_inspector import inspect_real_data_directory

    return inspect_real_data_directory(
        root_dir=request.get("root_dir", "./data/DemoData"),
        work_dir=request.get("work_dir", "./work"),
        report_dir=request.get("report_dir", "outputs/reports"),
        max_subjects=int(request.get("max_subjects", 500)),
    )

@router.get("/api/real-data/inventory/latest")
async def real_data_inventory_latest():
    """Get latest data inventory."""
    path = Path("outputs/reports") / "real_data_sandbox" / "data_inventory.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No inventory found. POST /api/real-data/inspect first.")
    return json.loads(path.read_text(encoding="utf-8"))

@router.post("/api/real-data/risk-report")
async def real_data_risk_report():
    """Generate risk report from latest data inventory."""
    from src.backend.app.tools.real_data_risk_reporter import build_risk_report

    return build_risk_report(
        inventory_path="outputs/reports/real_data_sandbox/data_inventory.json",
        output_dir="outputs/reports/real_data_sandbox",
    )

@router.get("/api/real-data/risk-report/latest")
async def real_data_risk_report_latest():
    """Get latest risk report."""
    path = Path("outputs/reports/real_data_sandbox/risk_report.json")
    if not path.exists():
        raise HTTPException(status_code=404, detail="No risk report found. POST /api/real-data/risk-report first.")
    return json.loads(path.read_text(encoding="utf-8"))

@router.post("/api/real-data/protocol-recommend")
async def real_data_protocol_recommend():
    """Generate protocol recommendation from latest data inventory."""
    from src.backend.app.tools.real_data_protocol_advisor import recommend_protocol_from_inventory

    return recommend_protocol_from_inventory(
        inventory_path="outputs/reports/real_data_sandbox/data_inventory.json",
        output_dir="outputs/reports/real_data_sandbox",
    )

@router.get("/api/sandbox/status")
async def sandbox_status():
    """Get sandbox mode status."""
    import os
    return {
        "ok": True,
        "mode": os.environ.get("MEDIMAGE_REAL_DATA_MODE", "readonly_sandbox"),
        "rawdata_readonly": True,
        "preprocessing_enabled": False,
        "auto_upload_enabled": False,
    }

@router.post("/api/workflow/run")
async def workflow_run(request: dict[str, Any]):
    """Run quickstart demo or real-data mini pipeline.

    Delegates heavy computation to workflow_runner module.
    """
    reject_execution_contract("realdata.workflow")
