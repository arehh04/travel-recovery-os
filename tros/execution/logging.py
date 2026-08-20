"""Structured logging — machine-readable JSON logs (Phase 7).

Every log event contains:
- timestamp
- level
- event_name
- mission_id, execution_id, request_id (when available)
- agent (when applicable)
- phase (when applicable)
- duration_ms (when applicable)

Never logs: API keys, credentials, raw prompts with secrets.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any


class StructuredLogger:
    """Structured JSON logger for TR-OS execution events.

    Produces machine-readable log records with consistent fields.
    Integrates with Python's standard logging module.
    """

    def __init__(self, name: str = "tros.structured") -> None:
        self._logger = logging.getLogger(name)
        self._execution_context: dict[str, str] = {}

    def set_context(self, **kwargs: str) -> None:
        """Set persistent context fields (mission_id, execution_id, etc.)."""
        self._execution_context.update(kwargs)

    def event(
        self,
        event_name: str,
        level: int = logging.INFO,
        agent: str = "",
        phase: str = "",
        duration_ms: int = -1,
        **extra: Any,
    ) -> None:
        """Log a structured event."""
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": logging.getLevelName(level),
            "event_name": event_name,
            **self._execution_context,
        }
        if agent:
            record["agent"] = agent
        if phase:
            record["phase"] = phase
        if duration_ms >= 0:
            record["duration_ms"] = duration_ms
        # Merge extra fields (filtered for safety)
        for k, v in extra.items():
            if k not in ("api_key", "secret", "password", "token", "credential"):
                record[k] = v

        self._logger.log(level, json.dumps(record, default=str))


# Module-level singleton
_structured_logger = StructuredLogger()


def get_structured_logger() -> StructuredLogger:
    """Get the global structured logger instance."""
    return _structured_logger


class Timer:
    """Context manager for timing operations."""

    def __init__(self) -> None:
        self.elapsed_ms: int = 0
        self._start: float = 0

    def __enter__(self) -> Timer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed_ms = int((time.monotonic() - self._start) * 1000)
