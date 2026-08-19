"""Rate limiting and abuse protection middleware (Phase 9).

Provides:
- InMemoryRateLimiter: sliding window per user_id/IP
- MaxConcurrencyGuard: semaphore-based concurrent request limit
- Body size enforcement middleware
- Structured error responses (429, 503, 413)
"""

from __future__ import annotations

import asyncio
import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tros.api.settings import get_settings


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class InMemoryRateLimiter:
    """Sliding-window rate limiter per key (user_id or IP)."""

    def __init__(self, rpm: int = 60, window_sec: int = 60):
        self.rpm = rpm
        self.window_sec = window_sec
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if the key is within the rate limit.

        Returns (allowed, info) where info has remaining count and reset time.
        """
        now = time.time()
        window_start = now - self.window_sec

        with self._lock:
            timestamps = self._requests[key]
            # Remove expired entries
            timestamps[:] = [t for t in timestamps if t > window_start]
            count = len(timestamps)

            if count >= self.rpm:
                # Find when the oldest request in the window expires
                reset_at = timestamps[0] + self.window_sec if timestamps else now + self.window_sec
                return False, {
                    "remaining": 0,
                    "reset_at": reset_at,
                    "limit": self.rpm,
                }

            timestamps.append(now)
            return True, {
                "remaining": self.rpm - count - 1,
                "reset_at": now + self.window_sec,
                "limit": self.rpm,
            }


# ---------------------------------------------------------------------------
# Concurrency Guard
# ---------------------------------------------------------------------------

class MaxConcurrencyGuard:
    """Semaphore-based concurrency guard."""

    def __init__(self, max_concurrent: int = 10):
        self._max = max_concurrent
        self._active = 0
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            if self._active >= self._max:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    @property
    def active(self) -> int:
        with self._lock:
            return self._active


# ---------------------------------------------------------------------------
# Module-level instances (created lazily)
# ---------------------------------------------------------------------------

_rate_limiter: Optional[InMemoryRateLimiter] = None
_concurrency_guard: Optional[MaxConcurrencyGuard] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        _rate_limiter = InMemoryRateLimiter(rpm=settings.rate_limit_rpm)
    return _rate_limiter


def get_concurrency_guard() -> MaxConcurrencyGuard:
    global _concurrency_guard
    if _concurrency_guard is None:
        settings = get_settings()
        _concurrency_guard = MaxConcurrencyGuard(max_concurrent=settings.max_concurrent_missions)
    return _concurrency_guard


def reset_rate_limiters() -> None:
    """Reset all rate limiters (for testing)."""
    global _rate_limiter, _concurrency_guard
    _rate_limiter = None
    _concurrency_guard = None


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limiting and body size checks."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()

        # --- Body size check ---
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_body_size:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "BODY_TOO_LARGE",
                        "message": f"Request body exceeds {settings.max_body_size} bytes",
                        "retryable": False,
                    }
                },
            )

        # --- Rate limit check ---
        # Extract client key: prefer X-Dev-User-Id, fall back to client IP
        client_key = (
            request.headers.get("X-Dev-User-Id", "")
            or (request.client.host if request.client else "unknown")
        )
        limiter = get_rate_limiter()
        allowed, info = limiter.is_allowed(client_key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "retryable": True,
                    }
                },
                headers={
                    "Retry-After": str(int(info["reset_at"] - time.time())),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])

        return response
