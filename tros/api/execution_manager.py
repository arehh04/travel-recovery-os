"""ExecutionManager — hardened async background mission execution (Phase 9).

Runs MissionService in a background thread so the API can return
HTTP 202 immediately. Tracks running missions, their cancellation
tokens, phase progress, and final results.

Hardened features:
- Configurable max_workers from settings
- Bounded submission queue (rejects 503 when full)
- Timeout enforcement per mission
- Completed mission cleanup (TTL-based)
- Graceful shutdown
- Exception isolation (one failure doesn't crash the pool)
- Metrics tracking (active, completed, failed, duration)

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
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from tros.execution.cancellation import CancellationToken
from tros.execution.context import ExecutionContext
from tros.execution.errors import MissionError
from tros.llm.client import LLMClient
from tros.service.mission_service import MissionService
from tros.service.result import MissionResult

logger = logging.getLogger(__name__)


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
    completed_at: Optional[datetime] = None
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    result: Optional[MissionResult] = None
    error: Optional[str] = None
    events: queue.Queue = field(default_factory=queue.Queue)
    _request_hash: str = ""


class QueueFullError(Exception):
    """Raised when the execution queue is full."""
    pass


class ExecutionManager:
    """Manages background mission execution with hardening.

    Thread-safe. Supports concurrent missions (each in its own thread).
    """

    def __init__(
        self,
        llm_client: Any | None = None,
        max_workers: int = 4,
        max_concurrent_missions: int = 10,
        mission_timeout_sec: int = 120,
        idempotency_ttl_sec: int = 3600,
        execution_repo: Any | None = None,
        mission_repo: Any | None = None,
        event_repo: Any | None = None,
    ) -> None:
        self._max_workers = max_workers
        self._max_concurrent = max_concurrent_missions
        self._mission_timeout = mission_timeout_sec
        self._idempotency_ttl = idempotency_ttl_sec
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._missions: dict[str, MissionExecution] = {}
        self._idempotency_keys: dict[str, str] = {}  # key → mission_id
        self._request_hashes: dict[str, str] = {}  # idempotency_key → payload hash
        self._futures: dict[str, Future] = {}  # mission_id → future
        self._lock = threading.Lock()
        self._service = MissionService(llm_client=llm_client)
        # Optional persistence repositories (Phase 10)
        self._execution_repo = execution_repo
        self._mission_repo = mission_repo
        self._event_repo = event_repo
        # Metrics
        self._metrics = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "total_duration_ms": 0,
        }
        self._metrics_lock = threading.Lock()

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
            QueueFullError: if max concurrent missions reached (503)
        """
        # Capacity check
        with self._lock:
            active_count = sum(
                1 for m in self._missions.values()
                if m.status in ("PENDING", "RUNNING", "CANCELLING")
            )
            if active_count >= self._max_concurrent:
                raise QueueFullError(
                    f"Max concurrent missions reached ({self._max_concurrent})"
                )

        # Idempotency check
        if idempotency_key:
            payload_hash = self._hash_payload(request)
            with self._lock:
                if idempotency_key in self._idempotency_keys:
                    existing_mission_id = self._idempotency_keys[idempotency_key]
                    existing_hash = self._request_hashes.get(idempotency_key, "")
                    if existing_hash and existing_hash != payload_hash:
                        raise ValueError("Idempotency key conflict: same key, different payload")
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
            self._update_metric("total_submitted", 1)

        # Persist execution and idempotency key (Phase 10)
        if self._execution_repo:
            try:
                self._execution_repo.save(execution)
            except Exception:
                logger.debug("Failed to persist execution %s", ctx.mission_id)
        if self._mission_repo and idempotency_key:
            try:
                self._mission_repo.save_idempotency_key(idempotency_key, ctx.mission_id)
            except Exception:
                logger.debug("Failed to persist idempotency key for %s", ctx.mission_id)

        # Emit queued event
        self._emit_event(execution, "mission.queued", {
            "mission_id": ctx.mission_id,
            "execution_id": ctx.execution_id,
        })

        # Submit to background with timeout enforcement
        future = self._executor.submit(self._run_mission, execution, request, idempotency_key)
        with self._lock:
            self._futures[ctx.mission_id] = future

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

    def shutdown(self, wait: bool = True, timeout: float = 10.0) -> None:
        """Gracefully shut down the executor."""
        logger.info("ExecutionManager shutdown initiated (wait=%s)", wait)
        self._executor.shutdown(wait=wait, cancel_futures=not wait)
        logger.info("ExecutionManager shutdown complete")

    def cleanup_completed(self, ttl_sec: Optional[int] = None) -> int:
        """Remove completed/failed/cancelled missions older than TTL.

        Returns the number of missions removed.
        """
        ttl = ttl_sec if ttl_sec is not None else self._idempotency_ttl
        now = datetime.now(timezone.utc)
        removed = 0

        with self._lock:
            to_remove = []
            for mid, execution in self._missions.items():
                if execution.status in ("COMPLETED", "FAILED", "CANCELLED"):
                    if execution.completed_at:
                        age = (now - execution.completed_at).total_seconds()
                        if age > ttl:
                            to_remove.append(mid)
                    else:
                        # No completion timestamp — use started_at as fallback
                        age = (now - execution.started_at).total_seconds()
                        if age > ttl * 2:
                            to_remove.append(mid)

            for mid in to_remove:
                del self._missions[mid]
                # Clean up associated idempotency keys
                keys_to_remove = [
                    k for k, v in self._idempotency_keys.items() if v == mid
                ]
                for k in keys_to_remove:
                    del self._idempotency_keys[k]
                    self._request_hashes.pop(k, None)
                self._futures.pop(mid, None)
                removed += 1

        if removed:
            logger.info("Cleaned up %d completed missions", removed)
        return removed

    def get_metrics(self) -> dict:
        """Return current execution metrics."""
        with self._metrics_lock:
            metrics = dict(self._metrics)
        with self._lock:
            active = sum(
                1 for m in self._missions.values()
                if m.status in ("PENDING", "RUNNING", "CANCELLING")
            )
        metrics["active_missions"] = active
        metrics["total_missions"] = len(self._missions)
        if metrics["total_completed"] > 0:
            metrics["avg_duration_ms"] = (
                metrics["total_duration_ms"] / metrics["total_completed"]
            )
        return metrics

    def _run_mission(
        self,
        execution: MissionExecution,
        request: dict[str, Any],
        idempotency_key: str,
    ) -> None:
        """Background thread: execute the mission via MissionService.

        Includes timeout enforcement and exception isolation.
        """
        try:
            execution.status = "RUNNING"
            self._emit_event(execution, "mission.running", {
                "mission_id": execution.mission_id,
            })
            execution.phase = "FLIGHT_SEARCH"
            execution.progress = 0.30
            # Persist state change (Phase 10)
            self._persist_execution(execution)

            # Run the synchronous MissionService with timeout enforcement
            _timeout_executor = ThreadPoolExecutor(max_workers=1)
            _future = _timeout_executor.submit(
                self._service.run,
                request=request,
                idempotency_key=idempotency_key,
                cancellation_token=execution.cancellation_token,
            )
            try:
                result = _future.result(timeout=self._mission_timeout)
            except FuturesTimeoutError:
                # Mission exceeded the timeout — mark as failed
                execution.status = "FAILED"
                execution.phase = "COMPLETED"
                execution.progress = 1.0
                execution.completed_at = datetime.now(timezone.utc)
                execution.error = f"Mission timed out after {self._mission_timeout}s"
                self._emit_event(execution, "mission.failed", {
                    "mission_id": execution.mission_id,
                    "error": "Timeout",
                })
                self._update_metric("total_failed", 1)
                self._persist_execution(execution)
                _timeout_executor.shutdown(wait=False)
                return
            finally:
                _timeout_executor.shutdown(wait=False)

            # Check if cancelled during execution
            if execution.cancellation_token.is_cancelled():
                execution.status = "CANCELLED"
                execution.phase = "COMPLETED"
                execution.progress = 1.0
                execution.completed_at = datetime.now(timezone.utc)
                self._emit_event(execution, "mission.cancelled", {
                    "mission_id": execution.mission_id,
                    "reason": execution.cancellation_token.reason,
                })
                self._update_metric("total_cancelled", 1)
                self._persist_execution(execution)
            elif result.status == "failed":
                execution.status = "FAILED"
                execution.phase = "COMPLETED"
                execution.progress = 1.0
                execution.completed_at = datetime.now(timezone.utc)
                execution.error = "Mission execution failed"
                execution.result = result
                self._emit_event(execution, "mission.failed", {
                    "mission_id": execution.mission_id,
                })
                self._update_metric("total_failed", 1)
                self._persist_execution(execution)
            else:
                execution.status = "COMPLETED"
                execution.phase = "COMPLETED"
                execution.progress = 1.0
                execution.completed_at = datetime.now(timezone.utc)
                execution.result = result
                self._emit_event(execution, "mission.completed", {
                    "mission_id": execution.mission_id,
                    "confidence": result.confidence,
                })
                self._update_metric("total_completed", 1)
                # Track duration
                duration_ms = int(
                    (execution.completed_at - execution.started_at).total_seconds() * 1000
                )
                self._update_metric("total_duration_ms", duration_ms)
                self._persist_execution(execution)
                # Persist mission result (Phase 10)
                if self._mission_repo and result:
                    try:
                        self._mission_repo.save_result(
                            execution.mission_id,
                            result.model_dump() if hasattr(result, "model_dump") else str(result),
                        )
                    except Exception:
                        logger.debug("Failed to persist mission result %s", execution.mission_id)

        except MissionError as exc:
            execution.status = "FAILED"
            execution.phase = "COMPLETED"
            execution.progress = 1.0
            execution.completed_at = datetime.now(timezone.utc)
            execution.error = str(exc)
            self._emit_event(execution, "mission.failed", {
                "mission_id": execution.mission_id,
                "error": str(exc),
            })
            self._update_metric("total_failed", 1)
            self._persist_execution(execution)

        except Exception as exc:
            # Exception isolation — never crash the thread pool
            logger.exception("Unhandled exception in mission %s", execution.mission_id)
            execution.status = "FAILED"
            execution.phase = "COMPLETED"
            execution.progress = 1.0
            execution.completed_at = datetime.now(timezone.utc)
            execution.error = f"Internal error: {type(exc).__name__}"
            self._emit_event(execution, "mission.failed", {
                "mission_id": execution.mission_id,
                "error": "Internal error",
            })
            self._update_metric("total_failed", 1)
            self._persist_execution(execution)

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
        # Persist event for replay (Phase 10)
        if self._event_repo:
            try:
                self._event_repo.append(execution.mission_id, event)
            except Exception:
                logger.debug("Failed to persist event for %s", execution.mission_id)

    def _persist_execution(self, execution: MissionExecution) -> None:
        """Persist execution state to repository (Phase 10). Silent on failure."""
        if self._execution_repo:
            try:
                self._execution_repo.save(execution)
            except Exception:
                logger.debug("Failed to persist execution %s", execution.mission_id)

    def _update_metric(self, key: str, value: int) -> None:
        """Thread-safe metric update."""
        with self._metrics_lock:
            self._metrics[key] = self._metrics.get(key, 0) + value

    @staticmethod
    def _hash_payload(request: dict[str, Any]) -> str:
        """Create a deterministic hash of the request payload."""
        filtered = {k: v for k, v in sorted(request.items()) if k != "mission_id"}
        payload_str = json.dumps(filtered, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]
