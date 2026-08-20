"""Retry policy — bounded exponential backoff (Phase 7).

Retryable:
- Transient LLM network failure
- Transient Atlas failure
- Timeout

NOT retryable:
- Invalid mission / constraint violation
- Malformed tool arguments
- Fabricated recommendation
- Deterministic validation failure

Bounded: max_retries + exponential backoff.
Recovery attempts and infrastructure retries are conceptually separate.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TypeVar

from tros.execution.errors import MissionError
from tros.execution.logging import get_structured_logger

T = TypeVar("T")

logger = get_structured_logger()

# Defaults
DEFAULT_MAX_RETRIES = 2
DEFAULT_BASE_DELAY_SECONDS = 1.0
DEFAULT_MAX_DELAY_SECONDS = 10.0


def execute_with_retry(
    fn: Callable[..., T],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY_SECONDS,
    max_delay: float = DEFAULT_MAX_DELAY_SECONDS,
    operation_name: str = "operation",
    **kwargs: Any,
) -> T:
    """Execute a function with bounded exponential backoff retry.

    Only retries on retryable MissionError or transient exceptions.
    Non-retryable errors propagate immediately.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except MissionError as exc:
            if not exc.retryable:
                logger.event(
                    "RETRY_NON_RETRYABLE",
                    agent=operation_name,
                    error_code=exc.error_code,
                    attempt=attempt,
                )
                raise
            last_error = exc
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.event(
                    "RETRY_ATTEMPT",
                    agent=operation_name,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_seconds=delay,
                    error_code=exc.error_code,
                )
                time.sleep(delay)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.event(
                    "RETRY_ATTEMPT",
                    agent=operation_name,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_seconds=delay,
                )
                time.sleep(delay)
            else:
                raise

    # All retries exhausted
    logger.event(
        "RETRY_EXHAUSTED",
        agent=operation_name,
        max_retries=max_retries,
    )
    if last_error:
        raise last_error
    raise RuntimeError(f"Retry exhausted for {operation_name}")
