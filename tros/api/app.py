"""FastAPI application factory (Phase 8/10).

Creates the API application with:
- CORS configuration (configurable, not allow-all in production)
- Security headers
- Error handlers
- Mission routes
- Health/readiness routes
- SSE events
- OpenAPI documentation (disabled in production)
- Database initialization and migrations (Phase 10)
- Request ID generation and logging middleware (Phase 10)
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tros.api.config import (
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ORIGINS,
)
from tros.api.errors import mission_error_handler
from tros.api.routes.events import router as events_router
from tros.api.routes.health import router as health_router
from tros.api.routes.missions import router as missions_router
from tros.execution.errors import MissionError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Startup — initialize database and run pending migrations (Phase 10)
    from tros.api.settings import Environment, get_settings
    settings = get_settings()
    if settings.environment in (Environment.PRODUCTION, Environment.TESTING):
        try:
            from tros.api.db import init_db
            from tros.api.migrations import MigrationRunner
            init_db()
            MigrationRunner().run_pending()
        except Exception:
            logger.exception("Database initialization failed")
    yield
    # Shutdown — gracefully stop executor
    from tros.api.deps import _manager
    if _manager is not None:
        _manager.shutdown(wait=True, timeout=10.0)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from tros.api.settings import get_settings
    settings = get_settings()

    # Disable OpenAPI docs in production (Phase 10)
    docs_url = None if settings.is_production else "/api/docs"
    redoc_url = None if settings.is_production else "/api/redoc"
    openapi_url = None if settings.is_production else "/api/openapi.json"

    app = FastAPI(
        title="TR-OS Mission API",
        description="Travel Recovery Operating System \u2014 AI-powered flight recovery API",
        version="0.10.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )

    # --- Security headers middleware ---
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        # Generate or propagate request ID (Phase 10)
        req_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-Id"] = req_id

        # Request logging (Phase 10)
        logger.info(
            "%s %s %s %sms req=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            req_id,
        )
        return response

    # --- Rate limiting middleware ---
    from tros.api.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

    # --- Error handlers ---
    app.add_exception_handler(MissionError, mission_error_handler)

    # QueueFullError → 503
    from tros.api.execution_manager import QueueFullError

    @app.exception_handler(QueueFullError)
    async def queue_full_handler(request, exc):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "SERVICE_OVERLOADED",
                    "message": str(exc),
                    "retryable": True,
                }
            },
        )

    from tros.api.routes.claims import router as claims_router
    from tros.api.routes.profile import router as profile_router
    from tros.api.routes.swarm import router as swarm_router
    from tros.api.routes.webhooks import router as webhooks_router
    # --- Routes ---
    app.include_router(missions_router)
    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(webhooks_router)
    app.include_router(swarm_router)
    app.include_router(profile_router, prefix="/api/v1")
    app.include_router(claims_router, prefix="/api/v1")

    # --- Root redirect to docs ---
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "TR-OS Mission API", "docs": "/api/docs"}

    return app


# Module-level app for uvicorn
app = create_app()
