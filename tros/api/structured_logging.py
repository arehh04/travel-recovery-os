"""Structured logging — JSON formatter with secret scrubbing (Phase 9).

Provides:
- StructuredFormatter: JSON log output with standard fields
- SecretScrubber: regex-based filter that strips API keys, bearer tokens, etc.
- Request logging middleware for request/response tracking
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Secret Scrubber
# ---------------------------------------------------------------------------

# Patterns to scrub from log output
_SCRUB_PATTERNS = [
    # DeepSeek / OpenAI style API keys
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    # Bearer tokens
    re.compile(r"Bearer\s+[a-zA-Z0-9._\-/=+]+"),
    # Generic API key patterns in JSON
    re.compile(r'"api_key"\s*:\s*"[^"]+"'),
    re.compile(r'"secret"\s*:\s*"[^"]+"'),
    re.compile(r'"token"\s*:\s*"[^"]+"'),
    # Authorization header values
    re.compile(r"Authorization:\s*[^\s,;]+"),
]

_SCRUB_REPLACEMENT = "[REDACTED]"


def scrub_secrets(text: str) -> str:
    """Remove sensitive patterns from text."""
    for pattern in _SCRUB_PATTERNS:
        text = pattern.sub(_SCRUB_REPLACEMENT, text)
    return text


class SecretScrubberFilter(logging.Filter):
    """Logging filter that scrubs secrets from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_secrets(record.msg)
        if record.args:
            # Scrub string args too
            if isinstance(record.args, tuple):
                record.args = tuple(
                    scrub_secrets(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: scrub_secrets(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


# ---------------------------------------------------------------------------
# Structured JSON Formatter
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter.

    Output fields: timestamp, level, event (logger name), message,
    plus any extra fields from the log record.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.name,
            "message": record.getMessage(),
        }

        # Add optional fields if present
        for attr in ("mission_id", "execution_id", "request_id", "duration_ms", "status", "error_code"):
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)

        # Add exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Scrub secrets from the output
        output = json.dumps(log_entry, default=str)
        return scrub_secrets(output)


# ---------------------------------------------------------------------------
# Request Context Filter (Phase 10)
# ---------------------------------------------------------------------------

class RequestContextFilter(logging.Filter):
    """Injects request_id and mission_id into log records.

    When attached to a logger, ensures correlation IDs propagate
    through background threads when set via threading.local().
    """

    _context = threading.local()

    @classmethod
    def set_context(cls, request_id: str = "", mission_id: str = "") -> None:
        """Set the current request context (thread-local)."""
        cls._context.request_id = request_id
        cls._context.mission_id = mission_id

    @classmethod
    def clear_context(cls) -> None:
        """Clear the current request context."""
        cls._context.request_id = ""
        cls._context.mission_id = ""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = getattr(self._context, "request_id", "")
        if not hasattr(record, "mission_id"):
            record.mission_id = getattr(self._context, "mission_id", "")
        return True


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_structured_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application.

    Args:
        level: logging level (DEBUG, INFO, WARNING, ERROR)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add structured handler
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    handler.addFilter(SecretScrubberFilter())
    root_logger.addHandler(handler)

    # Suppress noisy loggers
    for name in ("uvicorn.access", "uvicorn.error", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)
