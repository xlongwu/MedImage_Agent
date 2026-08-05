from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

DEFAULT_RATE_LIMIT_PER_MINUTE = 6000


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-client in-memory rate limiter for local API protection."""

    def __init__(self, app, limit_per_minute: int | None = None) -> None:
        super().__init__(app)
        if limit_per_minute is None:
            raw_limit = os.environ.get("MEDIMAGE_RATE_LIMIT_PER_MINUTE", str(DEFAULT_RATE_LIMIT_PER_MINUTE))
            try:
                limit_per_minute = int(raw_limit)
            except ValueError:
                limit_per_minute = DEFAULT_RATE_LIMIT_PER_MINUTE
        self.limit_per_minute = max(0, limit_per_minute)
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.limit_per_minute <= 0:
            return await call_next(request)

        now = time.monotonic()
        key = self._client_key(request)
        with self._lock:
            hits = self._hits[key]
            cutoff = now - 60.0
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit_per_minute:
                retry_after = max(1, int(60.0 - (now - hits[0])))
                request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id")
                return JSONResponse(
                    status_code=429,
                    content={
                        "ok": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests.",
                            "details": {"limit_per_minute": self.limit_per_minute},
                        },
                        "request_id": request_id,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        **({"X-Request-ID": request_id} if request_id else {}),
                    },
                )
            hits.append(now)

        return await call_next(request)

    @staticmethod
    def _client_key(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
