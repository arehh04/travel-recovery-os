"""FastAPI application factory (Phase 8).

Creates the API application with:
- CORS configuration (configurable, not allow-all in production)
- Security headers
- Error handlers
- Mission routes
- Health/readiness routes
- SSE events
- OpenAPI documentation
"""

from __future__ import annotations

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
from tros.api.routes.missions import router as missions_router
from tros.api.routes.health import router as health_router
from tros.api.routes.events import router as events_router
from tros.execution.errors import MissionError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Startup
    yield
    # Shutdown — clean up resources
    from tros.api.deps import _manager
    if _manager is not None:
        _manager._executor.shutdown(wait=False)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TR-OS Mission API",
        description="Travel Recovery Operating System — AI-powered flight recovery API",
        version="0.8.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
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
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Add request ID to response if present in request
        req_id = request.headers.get("X-Request-Id", "")
        if req_id:
            response.headers["X-Request-Id"] = req_id
        return response

    # --- Error handlers ---
    app.add_exception_handler(MissionError, mission_error_handler)

    # --- Routes ---
    app.include_router(missions_router)
    app.include_router(health_router)
    app.include_router(events_router)

    # --- Root redirect to docs ---
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "TR-OS Mission API", "docs": "/api/docs"}

    return app


# Module-level app for uvicorn
app = create_app()
