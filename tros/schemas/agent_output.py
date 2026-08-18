"""Standardized agent output contract.

Every agent writes using this schema to guarantee interoperability
across the orchestration pipeline (Arch ADR-009).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class AgentOutput(BaseModel):
    """Standard output contract for every agent (Arch §5.5)."""
    agent: str
    status: AgentStatus = AgentStatus.COMPLETED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reasoning_summary: str = ""
    recommendation: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
