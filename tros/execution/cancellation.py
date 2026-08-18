"""Cancellation token — safe cooperative cancellation (Phase 7).

Long-running loops check the token periodically:
- ReAct loop
- Recovery loop
- Supervisor pipeline
- Retry loop

On cancellation:
- Stop safely
- Do not corrupt state
- Mark execution CANCELLED
- Preserve evidence and recovery history
"""

from __future__ import annotations

import threading


class CancellationToken:
    """Thread-safe cooperative cancellation token.

    Usage:
        token = CancellationToken()
        # ... pass token to long-running operations ...
        if token.is_cancelled():
            # stop gracefully
    """

    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._reason: str = ""

    def cancel(self, reason: str = "User requested cancellation") -> None:
        """Signal cancellation."""
        self._reason = reason
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled.is_set()

    @property
    def reason(self) -> str:
        """The reason for cancellation."""
        return self._reason

    def throw_if_cancelled(self) -> None:
        """Raise CancellationError if cancelled."""
        if self._cancelled.is_set():
            from tros.execution.errors import CancellationError
            raise CancellationError(self._reason)
