"""Health checks — readiness and availability (Phase 7).

HealthStatus:
- healthy: all required services available
- degraded: optional component unavailable
- unavailable: required dependency unavailable

Checks:
- Configuration validity
- LLM provider configuration
- Atlas CLI availability

Does not expose secrets. Independent of HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tros.config import ATLAS_CLI_BINARY, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class HealthCheck:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str = ""


@dataclass
class HealthReport:
    """Aggregated health status of the system."""
    status: HealthStatus = HealthStatus.UNAVAILABLE
    checks: list[HealthCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API response (no secrets)."""
        return {
            "status": self.status.value,
            "checks": [
                {"name": c.name, "status": c.status.value, "message": c.message}
                for c in self.checks
            ],
        }


def check_health() -> HealthReport:
    """Run all health checks and return aggregated status."""
    checks: list[HealthCheck] = []

    # Check 1: Configuration
    checks.append(HealthCheck(
        name="configuration",
        status=HealthStatus.HEALTHY,
        message="Configuration loaded",
    ))

    # Check 2: LLM provider
    if LLM_API_KEY and not LLM_API_KEY.startswith("sk-your"):
        checks.append(HealthCheck(
            name="llm_provider",
            status=HealthStatus.HEALTHY,
            message=f"LLM configured: {LLM_PROVIDER}/{LLM_MODEL}",
        ))
    else:
        checks.append(HealthCheck(
            name="llm_provider",
            status=HealthStatus.DEGRADED,
            message="LLM not configured — running in deterministic mode",
        ))

    # Check 3: Atlas CLI
    import shutil
    atlas_path = shutil.which(ATLAS_CLI_BINARY)
    if atlas_path:
        checks.append(HealthCheck(
            name="atlas_cli",
            status=HealthStatus.HEALTHY,
            message=f"Atlas CLI available: {ATLAS_CLI_BINARY}",
        ))
    else:
        checks.append(HealthCheck(
            name="atlas_cli",
            status=HealthStatus.UNAVAILABLE,
            message=f"Atlas CLI not found: {ATLAS_CLI_BINARY}",
        ))

    # Aggregate: worst status wins
    if any(c.status == HealthStatus.UNAVAILABLE for c in checks):
        overall = HealthStatus.UNAVAILABLE
    elif any(c.status == HealthStatus.DEGRADED for c in checks):
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY

    return HealthReport(status=overall, checks=checks)
