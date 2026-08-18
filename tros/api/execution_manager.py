"""ExecutionManager — async background mission execution (Phase 8).

Runs MissionService in a background thread so the API can return
HTTP 202 immediately. Tracks running missions, their cancellation
tokens, phase progress, and final results.

Architecture:
    API routes
       ↓
    ExecutionManager.submit()
       ↓ (background thread)
    MissionService.run()
       ↓
    SupervisorAgent.run_mission()
"""

from __future__ import annotations

import hashlib
import json
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from tros.execution.cancellation import CancellationToken
from tros.execution.context import ExecutionContext
from tros.execution.errors import MissionError
from tros.llm.client import LLMClient
from tros.service.mission_service import MissionService
from tros.service.result import MissionResult


# Mission execution phases (maps roughly to Supervisor pipeline)
PHASES = [
    "CONTEXT",
    "PLANNING",
    "FLIGHT_SEARCH",
    "BUDGET",
    "CRITIC",
    "REFLECTION",
    "VALIDATION",
    "RECOVERY",
    "SUMMARY",
    "COMPLETED",
]

PHASE_PROGRESS: dict[str, float] = {
    "CONTEXT": 0.05,
    "PLANNING": 0.10,
    "FLIGHT_SEARCH": 0.30,
    "BUDGET": 0.40,
    "CRITIC": 0.55,
    "REFLECTION": 0.65,
    "VALIDATION": 0.75,
    "RECOVERY": 0.80,
    "SUMMARY": 0.90,
    "COMPLETED": 1.0,
}


@dataclass
class MissionExecution:
    """Tracks a single mission execution."""
    mission_id: str
    execution_id: str
    status: str = "PENDING"
    phase: str = ""
    progress: float = 0.0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    result: Optional[MissionResult] = None
    error: Optional[str] = None
    events: queue.Queue = field(default_factory=queue.Queue)
    _request_hash: str = ""


class ExecutionManager:
    """Manages background mission execution.

    Thread-safe. Supports concurrent missions (each in its own thread).
    """

    def __init__(
        self,
        llm_client: Any | None = None,
        max_workers: int = 4,
    ) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._missions: dict[str, MissionExecution] = {}
        self._idempotency_keys: dict[str, str] = {}  # key → mission_id
        self._request_hashes: dict[str, str] = {}  # idempotency_key → payload hash
        self._lock = threading.Lock()
        self._service = MissionService(llm_client=llm_client)

    def submit(
        self,
        request: dict[str, Any],
        idempotency_key: str = "",
    ) -> MissionExecution:
        """Submit a mission for background execution.

        Returns the MissionExecution tracker immediately.
        The mission runs in a background thread.

        Raises:
            ValueError: if idempotency_key already used with different payload
        """
        # Idempotency check
        if idempotency_key:
            payload_hash = self._hash_payload(request)
            with self._lock:
                if idempotency_key in self._idempotency_keys:
                    existing_mission_id = self._idempotency_keys[idempotency_key]
                    existing_hash = self._request_hashes.get(idempotency_key, "")
                    if existing_hash and existing_hash != payload_hash:
                        raise ValueError("Idempotency key conflict: same key, different payload")
                    # Same key + same payload: return existing execution
                    existing = self._missions.get(existing_mission_id)
                    if existing:
                        return existing

        # Create execution context
        ctx = ExecutionContext.create(
            mission_id=request.get("mission_id", ""),
            request_id=idempotency_key or "",
        )

        execution = MissionExecution(
            mission_id=ctx.mission_id,
            execution_id=ctx.execution_id,
            status="PENDING",
            phase="CONTEXT",
            progress=0.0,
            _request_hash=self._hash_payload(request) if idempotency_key else "",
        )

        with self._lock:
            self._missions[ctx.mission_id] = execution
            if idempotency_key:
                self._idempotency_keys[idempotency_key] = ctx.mission_id
                self._request_hashes[idempotency_key] = execution._request_hash

        # Emit started event
        self._emit_event(execution, "mission.started", {
            "mission_id": ctx.mission_id,
            "execution_id": ctx.execution_id,
        })

        # Submit to background
        self._executor.submit(self._run_mission, execution, request, idempotency_key)

        return execution

    def get_execution(self, mission_id: str) -> Optional[MissionExecution]:
        """Get a mission execution tracker by ID."""
        with self._lock:
            return self._missions.get(mission_id)

    def cancel(self, mission_id: str) -> bool:
        """Request cancellation of a running mission.

        Returns True if cancellation was requested, False if mission not found
        or already terminal.
        """
        execution = self.get_execution(mission_id)
        if not execution:
            return False
        if execution.status in ("COMPLETED", "FAILED", "CANCELLED"):
            return False

        execution.cancellation_token.cancel("User requested cancellation")
        execution.status = "CANCELLING"
        self._emit_event(execution, "mission.cancelling", {
            "mission_id": mission_id,
        })
        return True

    def get_all_missions(self) -> list[MissionExecution]:
        """Get all tracked missions."""
        with self._lock:
            return list(self._missions.values())

    def _run_mission(
        self,
        execution: MissionExecution,
        request: dict[str, Any],
        idempotency_key: str,
    ) -> None:
        """Background thread: execute the mission via MissionService."""
        try:
            execution.status = "RUNNING"
            self._emit_event(execution, "mission.phase_changed", {
                "phase": "FLIGHT_SEARCH",
                "progress": 0.30,
            })
            execution.phase = "FLIGHT_SEARCH"
            execution.progress = 0.30

            # Run the synchronous MissionService
            result = self._service.run(
                request=request,
                idempotency_key=idempotency_key,
                cancellation_token=execution.cancellation_token,
            )

            # Check if cancelled during execution
            if execution.cancellation_token.is_cancelled():
                execution.status = "CANCELLED"
                execution.phase = "COMPLETED"
                execution.progress = 1.0
                self._emit_event(execution, "mission.cancelled", {
                    "mission_id": execution.mission_id,
                    "reason": execution.cancellation_token.reason,
                })
            elif result.status == "failed":
                execution.status = "FAILED"
                execution.phase = "COMPLETED"
                execution.progress = 1.0
                execution.error = "Mission execution failed"
                execution.result = result
                self._emit_event(execution, "mission.failed", {
                    "mission_id": execution.mission_id,
                })
            else:
                execution.status = "COMPLETED"
                execution.phase = "COMPLETED"
                execution.progress = 1.0
                execution.result = result
                self._emit_event(execution, "mission.completed", {
                    "mission_id": execution.mission_id,
                    "confidence": result.confidence,
                })

        except MissionError as exc:
            execution.status = "FAILED"
            execution.phase = "COMPLETED"
            execution.progress = 1.0
            execution.error = str(exc)
            self._emit_event(execution, "mission.failed", {
                "mission_id": execution.mission_id,
                "error": str(exc),
            })

        except Exception as exc:
            execution.status = "FAILED"
            execution.phase = "COMPLETED"
            execution.progress = 1.0
            execution.error = f"Internal error: {type(exc).__name__}"
            self._emit_event(execution, "mission.failed", {
                "mission_id": execution.mission_id,
                "error": "Internal error",
            })

    def _emit_event(self, execution: MissionExecution, event_type: str, data: dict) -> None:
        """Emit an SSE event to the mission's event queue."""
        event = {
            "type": event_type,
            "mission_id": execution.mission_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        try:
            execution.events.put_nowait(event)
        except queue.Full:
            pass  # drop event if queue is full

    @staticmethod
    def _hash_payload(request: dict[str, Any]) -> str:
        """Create a deterministic hash of the request payload."""
        # Sort keys for determinism, exclude volatile fields
        filtered = {k: v for k, v in sorted(request.items()) if k != "mission_id"}
        payload_str = json.dumps(filtered, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]
