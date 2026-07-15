from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.backend.app.api._errors import raise_api_error
from src.backend.app.api.execution_contract import reject_execution_contract
from src.backend.app.api.models import ExternalSmokeRunRequest
from src.backend.app.tools.external_smoke import get_external_smoke_status, run_external_smoke

router = APIRouter()


@router.get("/api/external-smoke/status")
def api_external_smoke_status() -> dict[str, Any]:
    return get_external_smoke_status()


@router.post("/api/external-smoke/run")
def api_external_smoke_run(request: ExternalSmokeRunRequest) -> dict[str, Any]:
    reject_execution_contract("external_smoke.run")
