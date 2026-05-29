from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.backend.app.api.models import GuiAgentSessionRequest, GuiAgentStepRequest
from src.backend.app.runtime.gui_agent import (
    abort_gui_agent_session,
    capture_gui_agent_screenshot,
    create_gui_agent_session,
    list_gui_agent_sessions,
    step_gui_agent_session,
)

router = APIRouter()


@router.get("/api/gui-agent/sessions")
def api_gui_agent_sessions() -> dict[str, Any]:
    return list_gui_agent_sessions()


@router.post("/api/gui-agent/sessions")
def api_gui_agent_create_session(request: GuiAgentSessionRequest) -> dict[str, Any]:
    try:
        return create_gui_agent_session(request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/gui-agent/sessions/{session_id}/step")
def api_gui_agent_step(session_id: str, request: GuiAgentStepRequest) -> dict[str, Any]:
    try:
        result = step_gui_agent_session(session_id, request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/gui-agent/sessions/{session_id}/screenshot")
def api_gui_agent_screenshot(session_id: str) -> dict[str, Any]:
    try:
        result = capture_gui_agent_screenshot(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/gui-agent/sessions/{session_id}/abort")
def api_gui_agent_abort(session_id: str) -> dict[str, Any]:
    try:
        return abort_gui_agent_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
