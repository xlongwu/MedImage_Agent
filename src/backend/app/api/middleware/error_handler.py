from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.backend.app.core.error_codes import ErrorCode
from src.backend.app.core.exceptions import MedImageError


logger = logging.getLogger("src.backend.app.api.errors")


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value else None


async def medimage_exception_handler(request: Request, exc: MedImageError) -> JSONResponse:
    logger.warning(
        "application_error",
        extra={
            "medimage": {
                "event": "application_error",
                "code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "request_id": _request_id(request),
            }
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": _request_id(request),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={
            "medimage": {
                "event": "unhandled_exception",
                "path": request.url.path,
                "request_id": _request_id(request),
            }
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                "message": "An internal server error occurred.",
                "details": {},
            },
            "request_id": _request_id(request),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(MedImageError, medimage_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
