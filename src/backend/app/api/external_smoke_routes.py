from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.backend.app.api.models import ExternalSmokeRunRequest
from src.backend.app.tools.external_smoke import get_external_smoke_status, run_external_smoke

router = APIRouter()


@router.get("/api/external-smoke/status")
def api_external_smoke_status() -> dict[str, Any]:
    return get_external_smoke_status()


@router.post("/api/external-smoke/run")
def api_external_smoke_run(request: ExternalSmokeRunRequest) -> dict[str, Any]:
    try:
        return run_external_smoke(
            target=request.target,
            mode=request.mode,
            config_path=request.config_path,
            approve=request.approved,
            approved_by=request.approved_by,
            dpabi_function=request.dpabi_function,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
