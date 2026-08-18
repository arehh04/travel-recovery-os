"""Health and readiness routes (Phase 8)."""

from __future__ import annotations

from fastapi import APIRouter

from tros.api.models import HealthCheckItem, HealthResponse
from tros.execution.health import check_health

router = APIRouter(tags=["health"])


@router.get("/api/v1/health", response_model=HealthResponse)
async def health():
    """System health check — returns aggregated health status."""
    report = check_health()
    return HealthResponse(
        status=report.status.value,
        checks=[
            HealthCheckItem(
                name=c.name,
                status=c.status.value,
                message=c.message,
            )
            for c in report.checks
        ],
    )


@router.get("/api/v1/readiness", response_model=HealthResponse)
async def readiness():
    """Readiness probe — same as health for now.

    In production, this could include additional checks like
    database connectivity, cache availability, etc.
    """
    report = check_health()
    return HealthResponse(
        status=report.status.value,
        checks=[
            HealthCheckItem(
                name=c.name,
                status=c.status.value,
                message=c.message,
            )
            for c in report.checks
        ],
    )
