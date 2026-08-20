"""Execution context — unique IDs for every mission execution (Phase 7).

Every mission execution has:
- mission_id: identifies the logical mission
- execution_id: identifies this specific execution attempt
- request_id: identifies the incoming API/request correlation

IDs are safe to log and never contain secrets.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from tros.config import LLM_MODEL, LLM_PROVIDER


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable execution context propagated through the entire pipeline."""
    mission_id: str
    execution_id: str
    request_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    provider: str = ""
    model: str = ""

    @classmethod
    def create(
        cls,
        mission_id: str = "",
        request_id: str = "",
    ) -> ExecutionContext:
        """Create a new ExecutionContext with generated IDs."""
        return cls(
            mission_id=mission_id or f"mission-{uuid.uuid4().hex[:12]}",
            execution_id=f"exec-{uuid.uuid4().hex[:12]}",
            request_id=request_id or f"req-{uuid.uuid4().hex[:12]}",
            provider=LLM_PROVIDER,
            model=LLM_MODEL,
        )

    def to_dict(self) -> dict:
        """Serialize for logging (no secrets)."""
        return {
            "mission_id": self.mission_id,
            "execution_id": self.execution_id,
            "request_id": self.request_id,
            "started_at": self.started_at.isoformat(),
            "provider": self.provider,
            "model": self.model,
        }
