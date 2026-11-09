"""API-key enforcement + per-IP sliding-window rate limiting.

Open mode by default (API_KEYS unset). Set API_KEYS to enable:
    API_KEYS=["sk_soundprint_dev_..."]  (comma-separated in env)
Clients then send: X-API-Key: ...
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

# exempt paths: health, docs, openapi
_EXEMPT = {"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}

_windows: dict[str, deque[float]] = defaultdict(deque)


class ApiGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        path = request.url.path

        if path in _EXEMPT:
            return await call_next(request)

        # 1) API key (when configured)
        if settings.api_keys:
            key = request.headers.get("X-API-Key", "")
            if key not in settings.api_keys:
                return JSONResponse(
                    {"detail": "Invalid or missing X-API-Key header"},
                    status_code=401,
                    headers={"WWW-Authenticate": "ApiKey"},
                )

        # 2) Rate limit per client IP
        now = time.monotonic()
        ip = (request.client.host if request.client else "unknown")
        window = _windows[ip]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            retry_after = int(60.0 - (now - window[0])) + 1
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)

        return await call_next(request)
