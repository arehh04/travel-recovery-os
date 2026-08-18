"""Performance instrumentation — execution timing metrics (Phase 7).

Measures duration of:
- Total mission
- Individual agents
- LLM calls
- Atlas searches
- Recovery
- Evidence construction
- Ranking
- Validation
- Summary

Stored as structured metadata — never as fake evidence.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceMetrics:
    """Structured performance timing for one mission execution.

    All values are in milliseconds. Non-negative.
    """
    total_ms: int = 0
    supervisor_ms: int = 0
    flight_agent_ms: int = 0
    llm_ms: int = 0
    atlas_ms: int = 0
    recovery_ms: int = 0
    evidence_ms: int = 0
    ranking_ms: int = 0
    validation_ms: int = 0
    summary_ms: int = 0
    critic_ms: int = 0
    reflection_ms: int = 0
    budget_ms: int = 0

    def to_dict(self) -> dict[str, int]:
        """Serialize for inclusion in execution metadata."""
        return {
            "total_ms": self.total_ms,
            "supervisor_ms": self.supervisor_ms,
            "flight_agent_ms": self.flight_agent_ms,
            "llm_ms": self.llm_ms,
            "atlas_ms": self.atlas_ms,
            "recovery_ms": self.recovery_ms,
            "evidence_ms": self.evidence_ms,
            "ranking_ms": self.ranking_ms,
            "validation_ms": self.validation_ms,
            "summary_ms": self.summary_ms,
            "critic_ms": self.critic_ms,
            "reflection_ms": self.reflection_ms,
            "budget_ms": self.budget_ms,
        }


class PerfTimer:
    """Context manager that writes elapsed time to a PerformanceMetrics field."""

    def __init__(self, metrics: PerformanceMetrics, field_name: str) -> None:
        self._metrics = metrics
        self._field = field_name
        self._start: float = 0

    def __enter__(self) -> PerfTimer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed = int((time.monotonic() - self._start) * 1000)
        setattr(self._metrics, self._field, elapsed)

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)
