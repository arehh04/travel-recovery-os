"""Mission routes — POST/GET/cancel endpoints (Phase 8).

All routes go through:
- AuthContext (authentication boundary)
- ExecutionManager (async background execution)
- MissionService (via ExecutionManager)

The API layer is transport only. It never directly manipulates
SupervisorAgent, SharedMissionState, RecoveryEngine, ToolExecutor,
or Atlas adapter.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from tros.api.auth import AuthContext, require_auth
from tros.api.deps import get_execution_manager
from tros.api.execution_manager import ExecutionManager
from tros.api.models import (
    CancelResponse,
    MissionCreatedResponse,
    MissionRequest,
    MissionResultResponse,
    MissionStatusResponse,
)

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

_IATA_RE = re.compile(r"^[A-Z]{3}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_request(req: MissionRequest) -> None:
    """Transport-level validation (IATA codes, date format, origin != dest)."""
    if not _IATA_RE.match(req.origin.upper()):
        raise HTTPException(status_code=400, detail={
            "error": {"code": "VALIDATION_ERROR", "message": f"Invalid origin IATA code: {req.origin}", "retryable": False},
        })
    if not _IATA_RE.match(req.destination.upper()):
        raise HTTPException(status_code=400, detail={
            "error": {"code": "VALIDATION_ERROR", "message": f"Invalid destination IATA code: {req.destination}", "retryable": False},
        })
    if not _DATE_RE.match(req.departure_date):
        raise HTTPException(status_code=400, detail={
            "error": {"code": "VALIDATION_ERROR", "message": f"Invalid date format (expected YYYY-MM-DD): {req.departure_date}", "retryable": False},
        })
    if req.origin.upper() == req.destination.upper():
        raise HTTPException(status_code=422, detail={
            "error": {"code": "CONSTRAINT_VIOLATION", "message": "Origin and destination must be different", "retryable": False},
        })


def _result_to_response(result, mission_id: str | None = None) -> MissionResultResponse:
    """Convert a MissionResult to the API response model."""
    rec = None
    if result.recommendation:
        rec = {
            "flight_number": result.recommendation.flight_number,
            "carrier": result.recommendation.carrier,
            "departure": result.recommendation.departure,
            "arrival": result.recommendation.arrival,
            "duration_minutes": result.recommendation.duration_minutes,
            "stops": result.recommendation.stops,
            "price": result.recommendation.price,
            "currency": result.recommendation.currency,
            "score": result.recommendation.score,
        }
        
    # Mock Gamification Data for Hackathon
    budget_limit = result.budget.get("limit", 1000.0) if result.budget else 1000.0
    flight_price = result.recommendation.price if result.recommendation else budget_limit
    money_saved = round(max(0.0, budget_limit - flight_price + 150.0), 2)  # +150 for avoiding rebooking fees
    time_saved_minutes = 210  # 3.5 hours of airport queueing avoided
    carbon_offset_kg = 24.5  # Example eco impact

    return MissionResultResponse(
        mission_id=mission_id or result.mission_id,
        execution_id=result.execution_id,
        status=result.status,
        recommendation=rec,
        alternatives=[
            {
                "flight_number": a.flight_number,
                "carrier": a.carrier,
                "price": a.price,
                "currency": a.currency,
                "score": a.score,
            }
            for a in result.alternatives
        ],
        budget=result.budget,
        confidence=result.confidence,
        recovery={
            "occurred": result.recovery.occurred,
            "attempts": result.recovery.attempts,
            "reason": result.recovery.reason,
            "recovered": result.recovery.recovered,
        },
        conflicts={
            "count": result.conflicts.count,
            "has_critical": result.conflicts.has_critical,
        },
        execution_metadata={
            "mission_id": result.execution_metadata.mission_id,
            "execution_id": result.execution_metadata.execution_id,
            "request_id": result.execution_metadata.request_id,
            "status": result.execution_metadata.status,
            "duration_ms": result.execution_metadata.duration_ms,
        },
        gamification={
            "time_saved_minutes": time_saved_minutes,
            "money_saved": money_saved,
            "carbon_offset_kg": carbon_offset_kg,
        },
    )


# -------------------------------------------------------------------
# POST /api/v1/missions
# -------------------------------------------------------------------

@router.post("", status_code=202, response_model=MissionCreatedResponse)
async def create_mission(
    request: MissionRequest,
    auth: AuthContext = Depends(require_auth),
    manager: ExecutionManager = Depends(get_execution_manager),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Create and start a new mission.

    Returns HTTP 202 Accepted with mission_id. The mission executes
    asynchronously in the background.
    """
    _validate_request(request)

    # Build internal request dict
    req_dict = {
        "origin": request.origin.upper(),
        "destination": request.destination.upper(),
        "departure_date": request.departure_date,
        "traveler_count": request.traveler_count,
        "currency": request.currency.upper(),
        "traveler_type": request.traveler_type,
        "disruption_type": request.disruption_type,
        "budget_limit": request.budget_limit,
    }

    try:
        execution = manager.submit(req_dict, idempotency_key=idempotency_key or "")
    except ValueError as exc:
        # Idempotency conflict
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": str(exc),
                    "retryable": False,
                },
            },
        )

    return MissionCreatedResponse(
        mission_id=execution.mission_id,
        execution_id=execution.execution_id,
        status=execution.status,
    )


# -------------------------------------------------------------------
# GET /api/v1/missions (List all missions)
# -------------------------------------------------------------------

@router.get("", response_model=list[dict[str, Any]])
async def list_missions(
    limit: int = 50,
    auth: AuthContext = Depends(require_auth),
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """List all tracked recovery missions for history and dashboard."""
    executions = manager.get_all_missions()
    results = []
    for ex in executions[-limit:]:
        rec = ex.result.recommendation if (ex.result and ex.result.recommendation) else None
        results.append({
            "mission_id": ex.mission_id,
            "execution_id": ex.execution_id,
            "status": ex.status,
            "phase": ex.phase,
            "progress": ex.progress,
            "started_at": ex.started_at.isoformat(),
            "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
            "has_result": ex.result is not None,
            "recommended_flight": rec.flight_number if rec else None,
            "carrier": rec.carrier if rec else None,
            "price": rec.price if rec else None,
            "currency": rec.currency if rec else "USD",
            "confidence": ex.result.confidence if ex.result else 0.0,
        })
    return list(reversed(results))


# -------------------------------------------------------------------
# GET /api/v1/missions/:mission_id
# -------------------------------------------------------------------

@router.get("/{mission_id}", response_model=MissionResultResponse)
async def get_mission(
    mission_id: str,
    auth: AuthContext = Depends(require_auth),
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """Get the full result of a mission.

    Returns 404 if mission not found.
    Returns the result even if still running (partial result).
    """
    execution = manager.get_execution(mission_id)
    if not execution:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "MISSION_NOT_FOUND",
                    "message": f"Mission {mission_id} not found",
                    "retryable": False,
                },
            },
        )

    if execution.result:
        return _result_to_response(execution.result, mission_id=execution.mission_id)

    # Mission still running or failed — return current status as partial result
    return MissionResultResponse(
        mission_id=execution.mission_id,
        execution_id=execution.execution_id,
        status=execution.status,
    )


# -------------------------------------------------------------------
# GET /api/v1/missions/:mission_id/status
# -------------------------------------------------------------------

@router.get("/{mission_id}/status", response_model=MissionStatusResponse)
async def get_mission_status(
    mission_id: str,
    auth: AuthContext = Depends(require_auth),
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """Get the current status/progress of a mission."""
    execution = manager.get_execution(mission_id)
    if not execution:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "MISSION_NOT_FOUND",
                    "message": f"Mission {mission_id} not found",
                    "retryable": False,
                },
            },
        )

    elapsed_ms = int((
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        - execution.started_at
    ).total_seconds() * 1000)

    return MissionStatusResponse(
        mission_id=execution.mission_id,
        execution_id=execution.execution_id,
        status=execution.status,
        phase=execution.phase,
        progress=execution.progress,
        started_at=execution.started_at.isoformat(),
        elapsed_ms=elapsed_ms,
    )


# -------------------------------------------------------------------
# POST /api/v1/missions/:mission_id/cancel
# -------------------------------------------------------------------

@router.post("/{mission_id}/cancel", response_model=CancelResponse)
async def cancel_mission(
    mission_id: str,
    auth: AuthContext = Depends(require_auth),
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """Request cancellation of a running mission.

    Uses the existing Phase 7 CancellationToken.
    """
    execution = manager.get_execution(mission_id)
    if not execution:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "MISSION_NOT_FOUND",
                    "message": f"Mission {mission_id} not found",
                    "retryable": False,
                },
            },
        )

    if execution.status in ("COMPLETED", "FAILED", "CANCELLED"):
        return CancelResponse(
            mission_id=mission_id,
            status=execution.status,
            message=f"Mission already {execution.status.lower()}",
        )

    cancelled = manager.cancel(mission_id)
    return CancelResponse(
        mission_id=mission_id,
        status="CANCELLING" if cancelled else execution.status,
        message="Cancellation requested" if cancelled else "Cancellation failed",
    )
