from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.backend.app.api._errors import raise_api_error
from src.backend.app.api.models import DesktopConfigSaveRequest
from src.backend.app.runtime.desktop_config import (
    get_desktop_config,
    get_desktop_health,
    get_dicom_conversion_capability,
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


@router.get("/api/desktop/capabilities/dicom-conversion")
def api_desktop_dicom_conversion_capability() -> dict[str, Any]:
    """Return DICOM conversion capability info per 实现dcm2nii任务方案.md §10.2."""
    return {"ok": True, "capability": get_dicom_conversion_capability()}


@router.post("/api/desktop/capabilities/dicom-conversion/detect")
def api_desktop_dicom_conversion_detect() -> dict[str, Any]:
    """Re-run dcm2niix detection and return the refreshed capability."""
    return {"ok": True, "capability": get_dicom_conversion_capability()}
