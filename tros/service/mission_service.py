"""MissionService — API/service boundary for mission execution (Phase 7).

Responsibilities:
- Request validation
- Execution context creation
- Idempotency check
- Lifecycle management
- Cancellation support
- Error mapping
- Calling SupervisorAgent
- Building sanitized MissionResult

SupervisorAgent remains focused on mission orchestration.
MissionService handles the API/service boundary concerns.

Future HTTP endpoints will call:
    POST /missions       → service.run(request)
    GET  /missions/{id}  → service.get_result(mission_id)
    GET  /missions/{id}/status → service.get_status(mission_id)
"""

from __future__ import annotations

import time
from typing import Any, Optional

from tros.agents.supervisor import SupervisorAgent
from tros.execution.cancellation import CancellationToken
from tros.execution.context import ExecutionContext
from tros.execution.errors import (
    MissionError,
    ValidationError,
    InternalMissionError,
)
from tros.execution.idempotency import IdempotencyStore
from tros.execution.lifecycle import ExecutionStatus, validate_transition
from tros.execution.logging import get_structured_logger
from tros.execution.performance import PerformanceMetrics, PerfTimer
from tros.schemas.mission import (
    MissionContext, DisruptionEvent, DisruptionType, TravelerProfile, TravelerType,
)
from tros.service.result import MissionResult, ExecutionMetadata
from tros.state.mission_state import SharedMissionState
from tros.utils.logging import get_logger

logger = get_logger("MissionService")
structured_log = get_structured_logger()


class MissionService:
    """Service layer for TR-OS mission execution.

    Sits between HTTP API (future) and SupervisorAgent.
    Handles cross-cutting concerns: idempotency, lifecycle, error mapping.
    """

    def __init__(
        self,
        llm_client: Any | None = None,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        self._supervisor = SupervisorAgent(llm_client=llm_client)
        self._idempotency = idempotency_store or IdempotencyStore()
        self._results: dict[str, MissionResult] = {}

    def run(
        self,
        request: dict[str, Any],
        idempotency_key: str = "",
        cancellation_token: CancellationToken | None = None,
    ) -> MissionResult:
        """Execute a mission with full Phase 7 infrastructure.

        Args:
            request: Raw mission request (origin, destination, date, etc.)
            idempotency_key: Optional key for deduplication
            cancellation_token: Optional token for cooperative cancellation

        Returns:
            Sanitized MissionResult
        """
        token = cancellation_token or CancellationToken()
        metrics = PerformanceMetrics()

        # Idempotency check
        if idempotency_key and self._idempotency.exists(idempotency_key):
            existing = self._idempotency.get(idempotency_key)
            if existing:
                structured_log.event("IDEMPOTENCY_HIT", request_key=idempotency_key)
                return existing.result

        # Create execution context
        ctx = ExecutionContext.create(
            mission_id=request.get("mission_id", ""),
            request_id=idempotency_key or "",
        )

        structured_log.set_context(
            mission_id=ctx.mission_id,
            execution_id=ctx.execution_id,
            request_id=ctx.request_id,
        )
        structured_log.event("MISSION_STARTED", phase="service")

        # Validate request
        try:
            self._validate_request(request)
        except MissionError as exc:
            structured_log.event("MISSION_FAILED", phase="validation",
                                 error_code=exc.error_code)
            result = self._build_error_result(ctx, exc, metrics)
            if idempotency_key:
                self._idempotency.set(idempotency_key, result, status="failed")
            self._results[ctx.mission_id] = result
            return result

        # Check cancellation before execution
        if token.is_cancelled():
            return self._build_cancelled_result(ctx, metrics)

        # Execute mission
        status = ExecutionStatus.PENDING
        try:
            with PerfTimer(metrics, "total_ms"):
                # Build state
                state = self._build_state(ctx, request)

                # Transition: PENDING → RUNNING
                validate_transition(status, ExecutionStatus.RUNNING)
                status = ExecutionStatus.RUNNING
                structured_log.event("MISSION_RUNNING", phase="supervisor")

                # Run supervisor
                with PerfTimer(metrics, "supervisor_ms"):
                    state = self._supervisor.run_mission(state, request)

                # Check for recovery
                recovery_state = state.recovery_state or {}
                if recovery_state.get("recovered"):
                    status = ExecutionStatus.RECOVERING

                # Final status
                mission_decision = state.mission_decision or {}
                if mission_decision.get("status") == "approved":
                    validate_transition(
                        ExecutionStatus.RUNNING if status == ExecutionStatus.RUNNING
                        else status,
                        ExecutionStatus.COMPLETED,
                    )
                    final_status = ExecutionStatus.COMPLETED
                elif mission_decision.get("status") == "conditional":
                    final_status = ExecutionStatus.CONDITIONAL
                else:
                    final_status = ExecutionStatus.COMPLETED

                # Build result
                result = MissionResult.from_state(state, ctx)
                result.execution_metadata.duration_ms = metrics.total_ms
                result.execution_metadata.status = final_status.value

            structured_log.event(
                "MISSION_COMPLETED",
                phase="service",
                duration_ms=metrics.total_ms,
            )

            # Cache for idempotency
            if idempotency_key:
                self._idempotency.set(idempotency_key, result)

            # Cache for lookup
            self._results[ctx.mission_id] = result

            return result

        except MissionError as exc:
            structured_log.event(
                "MISSION_FAILED",
                phase="execution",
                error_code=exc.error_code,
            )
            result = self._build_error_result(ctx, exc, metrics)
            if idempotency_key:
                self._idempotency.set(idempotency_key, result, status="failed")
            self._results[ctx.mission_id] = result
            return result

        except Exception as exc:
            logger.error("Unexpected error in MissionService: %s", exc)
            result = self._build_error_result(
                ctx,
                InternalMissionError(f"Internal error: {type(exc).__name__}"),
                metrics,
            )
            self._results[ctx.mission_id] = result
            return result

    def get_result(self, mission_id: str) -> Optional[MissionResult]:
        """Retrieve a cached mission result by ID."""
        return self._results.get(mission_id)

    def get_status(self, mission_id: str) -> Optional[str]:
        """Get the status of a cached mission."""
        result = self._results.get(mission_id)
        return result.status if result else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_request(request: dict[str, Any]) -> None:
        """Validate incoming request has required fields."""
        required = ["origin", "destination", "departure_date"]
        for field in required:
            if not request.get(field):
                raise ValidationError(
                    f"Missing required field: {field}",
                    phase="validation",
                )

    @staticmethod
    def _build_state(ctx: ExecutionContext, request: dict[str, Any]) -> SharedMissionState:
        """Build SharedMissionState from request."""
        state = SharedMissionState(mission_id=ctx.mission_id)
        return state

    @staticmethod
    def _build_error_result(
        ctx: ExecutionContext, error: MissionError, metrics: PerformanceMetrics,
    ) -> MissionResult:
        """Build a failed MissionResult from a MissionError."""
        return MissionResult(
            mission_id=ctx.mission_id,
            execution_id=ctx.execution_id,
            status="failed",
            execution_metadata=ExecutionMetadata(
                mission_id=ctx.mission_id,
                execution_id=ctx.execution_id,
                request_id=ctx.request_id,
                status="failed",
                duration_ms=metrics.total_ms,
            ),
        )

    @staticmethod
    def _build_cancelled_result(
        ctx: ExecutionContext, metrics: PerformanceMetrics,
    ) -> MissionResult:
        """Build a cancelled MissionResult."""
        return MissionResult(
            mission_id=ctx.mission_id,
            execution_id=ctx.execution_id,
            status="cancelled",
            execution_metadata=ExecutionMetadata(
                mission_id=ctx.mission_id,
                execution_id=ctx.execution_id,
                request_id=ctx.request_id,
                status="cancelled",
                duration_ms=metrics.total_ms,
            ),
        )
