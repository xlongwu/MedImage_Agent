"""Advisor and knowledge-base route handlers."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.post("/api/advisor/protocol")
def api_advisor_protocol(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("protocol", request)

@router.post("/api/advisor/error")
def api_advisor_error(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("error", request)

@router.post("/api/advisor/qc-report")
def api_advisor_qc_report(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("qc-report", request)

@router.post("/api/advisor/parameters")
def api_advisor_parameters(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("parameters", request)

@router.post("/api/advisor/docs-qa")
def api_advisor_docs_qa(request: dict[str, Any]) -> dict[str, Any]:
    from src.backend.app.advisor.advisor_router import route_advisor

    return route_advisor("docs-qa", request)


# ── Error KB endpoints ────────────────────────────────────────────────────

@router.get("/api/kb/errors")
def api_kb_errors() -> dict[str, Any]:
    from src.backend.app.tools.error_kb_validator import list_error_kb_entries

    return list_error_kb_entries()

@router.post("/api/kb/errors/validate")
def api_kb_errors_validate() -> dict[str, Any]:
    from src.backend.app.tools.error_kb_validator import validate_error_kb

    return validate_error_kb()


# ── SessionDB endpoints ───────────────────────────────────────────────────
