"""API schemas — Pydantic request/response models (Phase 8).

These are the public API schemas, distinct from internal domain models.
Maps to/from MissionService inputs and MissionResult outputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# Requests
# -------------------------------------------------------------------

class MissionRequest(BaseModel):
    """Request body for POST /api/v1/missions."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    traveler_count: int = Field(default=1, ge=1, le=10, description="Number of travelers")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code")
    traveler_type: str = Field(default="Business", description="Traveler type")
    disruption_type: str = Field(default="FlightCancelled", description="Disruption type")
    budget_limit: float = Field(default=1000.0, ge=0, description="Budget limit in currency")


# -------------------------------------------------------------------
# Responses
# -------------------------------------------------------------------

class MissionCreatedResponse(BaseModel):
    """Response for POST /api/v1/missions (HTTP 202)."""
    mission_id: str
    execution_id: str
    status: str = "PENDING"


class FlightInfoResponse(BaseModel):
    """Sanitized flight recommendation."""
    flight_number: str = ""
    carrier: str = ""
    departure: str = ""
    arrival: str = ""
    duration_minutes: int = 0
    stops: int = 0
    price: float = 0.0
    currency: str = "USD"
    score: float = 0.0


class RecoveryInfoResponse(BaseModel):
    """Public recovery summary."""
    occurred: bool = False
    attempts: int = 0
    reason: str = ""
    recovered: bool = False


class ConflictInfoResponse(BaseModel):
    """Public conflict summary."""
    count: int = 0
    has_critical: bool = False


class ExecutionMetadataResponse(BaseModel):
    """Public execution metadata."""
    mission_id: str = ""
    execution_id: str = ""
    request_id: str = ""
    status: str = ""
    duration_ms: int = 0


class MissionResultResponse(BaseModel):
    """Full mission result (GET /api/v1/missions/:id)."""
    mission_id: str
    execution_id: str
    status: str
    recommendation: Optional[FlightInfoResponse] = None
    alternatives: list[FlightInfoResponse] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    recovery: RecoveryInfoResponse = Field(default_factory=RecoveryInfoResponse)
    conflicts: ConflictInfoResponse = Field(default_factory=ConflictInfoResponse)
    execution_metadata: ExecutionMetadataResponse = Field(default_factory=ExecutionMetadataResponse)


class MissionStatusResponse(BaseModel):
    """Mission status (GET /api/v1/missions/:id/status)."""
    mission_id: str
    execution_id: str = ""
    status: str
    phase: str = ""
    progress: float = 0.0
    started_at: str = ""
    elapsed_ms: int = 0


class CancelResponse(BaseModel):
    """Response for POST /api/v1/missions/:id/cancel."""
    mission_id: str
    status: str = "CANCELLED"
    message: str = ""


# -------------------------------------------------------------------
# Error response
# -------------------------------------------------------------------

class ApiError(BaseModel):
    """Structured API error response."""
    code: str
    message: str
    retryable: bool = False
    request_id: str = ""


class ErrorResponse(BaseModel):
    """Wrapper for error responses."""
    error: ApiError


# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

class HealthCheckItem(BaseModel):
    """Single health check."""
    name: str
    status: str
    message: str = ""


class HealthResponse(BaseModel):
    """Health/readiness response."""
    status: str
    checks: list[HealthCheckItem] = Field(default_factory=list)
    # Phase 10 build info
    version: str = ""
    commit: str = ""
    build_time: str = ""
