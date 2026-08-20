"""Repository abstraction — protocol-based data access (Phase 9).

Provides protocol-based repository interfaces with in-memory implementations.
These are thin wrappers that can be swapped for persistent backends later.

Repositories:
- ExecutionRepository: mission execution state
- MissionRepository: mission results
- EventRepository: SSE event log
"""

from __future__ import annotations

import threading
from typing import Any, Protocol, runtime_checkable

from tros.api.execution_manager import MissionExecution

# ---------------------------------------------------------------------------
# Repository Protocols
# ---------------------------------------------------------------------------

@runtime_checkable
class ExecutionRepository(Protocol):
    """Protocol for mission execution persistence."""

    def save(self, execution: MissionExecution) -> None: ...
    def get_by_id(self, mission_id: str) -> MissionExecution | None: ...
    def get_all(self) -> list[MissionExecution]: ...
    def delete(self, mission_id: str) -> bool: ...


@runtime_checkable
class MissionRepository(Protocol):
    """Protocol for mission result persistence."""

    def save_result(self, mission_id: str, result: Any) -> None: ...
    def get_result(self, mission_id: str) -> Any | None: ...
    def list_missions(self) -> list[str]: ...


@runtime_checkable
class EventRepository(Protocol):
    """Protocol for event log persistence."""

    def append(self, mission_id: str, event: dict) -> None: ...
    def get_events(self, mission_id: str) -> list[dict]: ...
    def clear(self, mission_id: str) -> None: ...


# ---------------------------------------------------------------------------
# In-Memory Implementations
# ---------------------------------------------------------------------------

class InMemoryExecutionRepository:
    """Thread-safe in-memory execution repository."""

    def __init__(self):
        self._store: dict[str, MissionExecution] = {}
        self._lock = threading.Lock()

    def save(self, execution: MissionExecution) -> None:
        with self._lock:
            self._store[execution.mission_id] = execution

    def get_by_id(self, mission_id: str) -> MissionExecution | None:
        with self._lock:
            return self._store.get(mission_id)

    def get_all(self) -> list[MissionExecution]:
        with self._lock:
            return list(self._store.values())

    def delete(self, mission_id: str) -> bool:
        with self._lock:
            return self._store.pop(mission_id, None) is not None


class InMemoryMissionRepository:
    """Thread-safe in-memory mission result repository."""

    def __init__(self):
        self._results: dict[str, Any] = {}
        self._lock = threading.Lock()

    def save_result(self, mission_id: str, result: Any) -> None:
        with self._lock:
            self._results[mission_id] = result

    def get_result(self, mission_id: str) -> Any | None:
        with self._lock:
            return self._results.get(mission_id)

    def list_missions(self) -> list[str]:
        with self._lock:
            return list(self._results.keys())


class InMemoryEventRepository:
    """Thread-safe in-memory event log repository."""

    def __init__(self):
        self._events: dict[str, list[dict]] = {}
        self._lock = threading.Lock()

    def append(self, mission_id: str, event: dict) -> None:
        with self._lock:
            if mission_id not in self._events:
                self._events[mission_id] = []
            self._events[mission_id].append(event)

    def get_events(self, mission_id: str) -> list[dict]:
        with self._lock:
            return list(self._events.get(mission_id, []))

    def clear(self, mission_id: str) -> None:
        with self._lock:
            self._events.pop(mission_id, None)
