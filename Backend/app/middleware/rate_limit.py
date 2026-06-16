from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

GLOBAL_RATE_LIMIT = "100/minute"
AUTH_RATE_LIMIT = "10/minute"
PUBLIC_PORTAL_RATE_LIMIT = "60/minute"

try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, default_limits=[GLOBAL_RATE_LIMIT])
except Exception:
    RateLimitExceeded = None
    SlowAPIMiddleware = None

    class _NoopLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    limiter = _NoopLimiter()


def apply_rate_limiting(app: FastAPI) -> None:
    if SlowAPIMiddleware is None or RateLimitExceeded is None:
        return

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)


async def _rate_limit_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded", "code": "rate_limited"},
    )
