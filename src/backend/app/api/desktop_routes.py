from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.backend.app.api._errors import raise_api_error
from src.backend.app.api.models import DesktopConfigSaveRequest
from src.backend.app.runtime.desktop_config import (
    get_desktop_config,
    get_desktop_health,
    save_desktop_config,
)

router = APIRouter()


@router.get("/api/desktop/config")
def api_desktop_config() -> dict[str, Any]:
    return {"ok": True, "config": get_desktop_config(redacted=True)}


@router.post("/api/desktop/config")
def api_desktop_save_config(request: DesktopConfigSaveRequest) -> dict[str, Any]:
    try:
        payload = {
            key: value
            for key, value in request.model_dump().items()
            if value is not None and value != {}
        }
        return save_desktop_config(payload)
    except Exception as exc:
        raise_api_error(exc)


@router.get("/api/desktop/health")
def api_desktop_health() -> dict[str, Any]:
    return get_desktop_health()
