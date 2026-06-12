from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("src.backend.app.api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured log entry per completed HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "medimage": {
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
        response.headers["X-Response-Time-ms"] = str(duration_ms)
        return response
