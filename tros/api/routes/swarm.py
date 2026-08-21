"""Swarm API Routes — Agent Swarm execution & consensus endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from tros.swarm.orchestrator import SwarmOrchestrator
from tros.swarm.state import DisruptionEvent

router = APIRouter(prefix="/api/v1/swarm", tags=["swarm"])
_orchestrator = SwarmOrchestrator()


class SwarmRunRequest(BaseModel):
    pnr: str = Field(..., json_schema_extra={"example": "PNR789"})
    original_flight: str = Field(..., json_schema_extra={"example": "BA100"})
    disruption_type: str = Field(default="CANCELLED", json_schema_extra={"example": "CANCELLED"})
    delay_minutes: int = Field(default=240, json_schema_extra={"example": 240})
    affected_passengers: list[str] = Field(default_factory=lambda: ["Alice Smith"])
    passenger_context: dict[str, Any] | None = None
    auto_execute: bool = Field(default=False, description="Auto-execute if consensus is APPROVED")


class SwarmApproveRequest(BaseModel):
    state: dict[str, Any]


class SwarmRejectRequest(BaseModel):
    state: dict[str, Any]
    reason: str = Field(default="Declined by passenger")


@router.post("/run", response_model=dict[str, Any])
async def run_swarm(request: SwarmRunRequest) -> dict[str, Any]:
    """Execute the multi-agent swarm on a disruption event."""
    disruption: DisruptionEvent = {
        "pnr": request.pnr,
        "original_flight": request.original_flight,
        "disruption_type": request.disruption_type,
        "delay_minutes": request.delay_minutes,
        "affected_passengers": request.affected_passengers,
    }

    result = await _orchestrator.execute(
        disruption=disruption,
        passenger_context=request.passenger_context,
        auto_execute_if_approved=request.auto_execute,
    )
    return result


@router.post("/approve", response_model=dict[str, Any])
async def approve_swarm(request: SwarmApproveRequest) -> dict[str, Any]:
    """Approve a PENDING recovery option and execute booking."""
    result = await _orchestrator.approve_and_execute(request.state)  # type: ignore[arg-type]
    return result


@router.post("/reject", response_model=dict[str, Any])
async def reject_swarm(request: SwarmRejectRequest) -> dict[str, Any]:
    """Reject a recovery option."""
    result = await _orchestrator.reject(request.state, reason=request.reason)  # type: ignore[arg-type]
    return result
