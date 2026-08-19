"""Health, readiness, and metrics routes (Phase 8/9/10)."""

from __future__ import annotations

from fastapi import APIRouter

from tros.api.build_info import get_build_info
from tros.api.metrics import get_metrics_collector
from tros.api.models import HealthCheckItem, HealthResponse
from tros.execution.health import check_health

router = APIRouter(tags=["health"])


@router.get("/api/v1/health", response_model=HealthResponse)
async def health():
    """System health check — returns aggregated health status."""
    report = check_health()
    build = get_build_info()
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
        version=build["version"],
        commit=build["commit"],
        build_time=build["build_time"],
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


@router.get("/api/v1/metrics")
async def metrics():
    """Aggregate metrics endpoint — observability data.

    Returns only aggregate numbers, no sensitive mission content.
    """
    collector = get_metrics_collector()
    snapshot = collector.get_snapshot()
    build = get_build_info()
    snapshot["version"] = build["version"]
    snapshot["commit"] = build["commit"]
    snapshot["build_time"] = build["build_time"]
    return snapshot
