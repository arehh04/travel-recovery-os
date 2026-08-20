"""Idempotency store — prevents duplicate execution (Phase 7).

In-memory implementation suitable for single-process use.
The interface makes future Redis/database replacement straightforward.

An idempotency key maps to an execution result. Repeated requests
with the same key return the cached result without re-execution.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class IdempotencyEntry:
    """Cached execution result for an idempotency key."""
    key: str
    result: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "completed"


class IdempotencyStore:
    """Thread-safe in-memory idempotency store.

    Interface:
        store.get(key) → IdempotencyEntry | None
        store.set(key, result) → IdempotencyEntry
        store.exists(key) → bool
    """

    def __init__(self) -> None:
        self._store: dict[str, IdempotencyEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> IdempotencyEntry | None:
        """Retrieve cached result for a key, or None if not found."""
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, result: Any, status: str = "completed") -> IdempotencyEntry:
        """Store an execution result for a key."""
        entry = IdempotencyEntry(key=key, result=result, status=status)
        with self._lock:
            self._store[key] = entry
        return entry

    def exists(self, key: str) -> bool:
        """Check if a key already has a cached result."""
        with self._lock:
            return key in self._store

    def clear(self) -> None:
        """Clear all entries (for testing)."""
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        """Number of cached entries."""
        with self._lock:
            return len(self._store)
