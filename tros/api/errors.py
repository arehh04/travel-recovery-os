"""API error handling — maps MissionError to HTTP responses (Phase 8)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from tros.api.models import ApiError, ErrorResponse
from tros.execution.errors import (
    AtlasError,
    AtlasTimeoutError,
    CancellationError,
    ConstraintViolationError,
    InternalMissionError,
    LLMError,
    LLMTimeoutError,
    MissionError,
    ValidationError,
)

# Error class → HTTP status code mapping
_ERROR_STATUS_MAP: dict[type[MissionError], int] = {
    ValidationError: 400,
    ConstraintViolationError: 422,
    CancellationError: 499,
    AtlasError: 502,
    AtlasTimeoutError: 504,
    LLMError: 503,
    LLMTimeoutError: 504,
    InternalMissionError: 500,
}


def error_to_http_status(error: MissionError) -> int:
    """Map a MissionError to an HTTP status code."""
    for error_type, status in _ERROR_STATUS_MAP.items():
        if isinstance(error, error_type):
            return status
    return 500


def build_error_response(
    error: MissionError,
    request_id: str = "",
    status_code: int | None = None,
) -> JSONResponse:
    """Build a structured JSON error response from a MissionError."""
    status = status_code or error_to_http_status(error)
    api_error = ApiError(
        code=error.error_code,
        message=str(error),
        retryable=error.retryable,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=api_error).model_dump(),
    )


async def mission_error_handler(request: Request, exc: MissionError) -> JSONResponse:
    """FastAPI exception handler for MissionError."""
    request_id = request.headers.get("X-Request-Id", "")
    return build_error_response(exc, request_id=request_id)
