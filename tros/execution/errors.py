"""Error taxonomy — structured application errors (Phase 7).

Every error has:
- error_code: stable identifier (e.g. "ATLAS_TIMEOUT")
- category: error classification
- message: human-readable (no secrets)
- retryable: whether retry may help
- phase: which pipeline phase failed
- agent: which agent encountered the error

Never exposes: stack traces to end users, API credentials, raw provider errors.
"""

from __future__ import annotations

from typing import Any


class MissionError(Exception):
    """Base exception for all TR-OS mission errors."""

    def __init__(
        self,
        error_code: str,
        category: str,
        message: str,
        retryable: bool = False,
        phase: str = "",
        agent: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.category = category
        self.message = message
        self.retryable = retryable
        self.phase = phase
        self.agent = agent
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API response (no secrets)."""
        return {
            "error_code": self.error_code,
            "category": self.category,
            "message": self.message,
            "retryable": self.retryable,
            "phase": self.phase,
            "agent": self.agent,
        }


class ValidationError(MissionError):
    """Invalid input or constraint violation."""

    def __init__(self, message: str, phase: str = "", agent: str = "", **kw: Any) -> None:
        super().__init__(
            error_code="VALIDATION_ERROR",
            category="VALIDATION",
            message=message,
            retryable=False,
            phase=phase,
            agent=agent,
            **kw,
        )


class ConstraintViolationError(MissionError):
    """Mission constraint violated (origin, currency, traveler count)."""

    def __init__(self, message: str, phase: str = "", agent: str = "", **kw: Any) -> None:
        super().__init__(
            error_code="CONSTRAINT_VIOLATION",
            category="CONSTRAINT",
            message=message,
            retryable=False,
            phase=phase,
            agent=agent,
            **kw,
        )


class ToolExecutionError(MissionError):
    """Tool call failed (unknown tool, invalid arguments)."""

    def __init__(self, message: str, phase: str = "", agent: str = "", **kw: Any) -> None:
        super().__init__(
            error_code="TOOL_ERROR",
            category="TOOL",
            message=message,
            retryable=False,
            phase=phase,
            agent=agent,
            **kw,
        )


class AtlasError(MissionError):
    """Atlas adapter/search failure."""

    def __init__(
        self, message: str, retryable: bool = True,
        phase: str = "", agent: str = "", **kw: Any,
    ) -> None:
        super().__init__(
            error_code="ATLAS_ERROR",
            category="ATLAS",
            message=message,
            retryable=retryable,
            phase=phase,
            agent=agent,
            **kw,
        )


class AtlasTimeoutError(AtlasError):
    """Atlas search timed out."""

    def __init__(self, message: str = "Atlas request timed out", **kw: Any) -> None:
        super().__init__(message=message, retryable=True, **kw)


class LLMError(MissionError):
    """LLM provider failure."""

    def __init__(
        self, message: str, retryable: bool = True,
        phase: str = "", agent: str = "", **kw: Any,
    ) -> None:
        super().__init__(
            error_code="LLM_ERROR",
            category="LLM",
            message=message,
            retryable=retryable,
            phase=phase,
            agent=agent,
            **kw,
        )


class LLMTimeoutError(LLMError):
    """LLM call timed out."""

    def __init__(self, message: str = "LLM request timed out", **kw: Any) -> None:
        super().__init__(message=message, retryable=True, **kw)


class RecoveryError(MissionError):
    """Recovery engine failure."""

    def __init__(
        self, message: str, retryable: bool = False,
        phase: str = "", agent: str = "", **kw: Any,
    ) -> None:
        super().__init__(
            error_code="RECOVERY_ERROR",
            category="RECOVERY",
            message=message,
            retryable=retryable,
            phase=phase,
            agent=agent,
            **kw,
        )


class RecommendationError(MissionError):
    """Recommendation validation or fabrication error."""

    def __init__(self, message: str, phase: str = "", agent: str = "", **kw: Any) -> None:
        super().__init__(
            error_code="RECOMMENDATION_ERROR",
            category="RECOMMENDATION",
            message=message,
            retryable=False,
            phase=phase,
            agent=agent,
            **kw,
        )


class TimeoutError(MissionError):
    """Generic timeout (mission-level)."""

    def __init__(self, message: str = "Operation timed out", **kw: Any) -> None:
        super().__init__(
            error_code="TIMEOUT",
            category="TIMEOUT",
            message=message,
            retryable=True,
            **kw,
        )


class CancellationError(MissionError):
    """Mission was cancelled."""

    def __init__(self, message: str = "Mission cancelled", **kw: Any) -> None:
        super().__init__(
            error_code="CANCELLED",
            category="CANCELLATION",
            message=message,
            retryable=False,
            **kw,
        )


class InternalMissionError(MissionError):
    """Unexpected internal error."""

    def __init__(self, message: str, **kw: Any) -> None:
        super().__init__(
            error_code="INTERNAL_ERROR",
            category="INTERNAL",
            message=message,
            retryable=False,
            **kw,
        )
