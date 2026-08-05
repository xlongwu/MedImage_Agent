from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

API_V1_PREFIX = "/api/v1"


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Map versioned API paths to the existing v1 route implementations."""

    async def dispatch(self, request: Request, call_next) -> Response:
        original_path = str(request.scope.get("path") or "")
        version = None
        if original_path == API_V1_PREFIX:
            request.scope["path"] = "/api"
            version = "v1"
        elif original_path.startswith(f"{API_V1_PREFIX}/"):
            request.scope["path"] = "/api/" + original_path[len(f"{API_V1_PREFIX}/") :]
            version = "v1"

        if version:
            request.scope["medimage_api_version"] = version
            request.scope["medimage_original_path"] = original_path

        response = await call_next(request)
        if version:
            response.headers["X-API-Version"] = version
            response.headers["X-Original-Path"] = original_path
        return response
