"""TR-OS core schemas: mission context, traveler, disruption events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class DisruptionType(str, Enum):
    FLIGHT_CANCELLED = "FlightCancelled"
    FLIGHT_DELAYED = "FlightDelayed"
    MISSED_CONNECTION = "MissedConnection"
    SCHEDULE_CHANGE = "ScheduleChange"


class TravelerType(str, Enum):
    BUSINESS = "Business"
    LEISURE = "Leisure"
    FAMILY = "Family"


class BudgetLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class MissionStatus(str, Enum):
    CREATED = "created"
    CONTEXT_LOADED = "context_loaded"
    PLANNING = "planning"
    RUNNING = "running"
    VALIDATION = "validation"
    REFLECTION = "reflection"
    RECOMMENDATION = "recommendation"
    COMPLETED = "completed"
    FAILED = "failed"


class TravelerProfile(BaseModel):
    """Immutable traveler information."""
    traveler_type: TravelerType = TravelerType.BUSINESS
    name: str = "Traveler"
    airline_preference: str | None = None
    seat_preference: str | None = None
    loyalty_program: str | None = None


class DisruptionEvent(BaseModel):
    """The trigger event that initiates a recovery mission."""
    disruption_type: DisruptionType
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    original_flight_number: str | None = None
    original_departure: str | None = None
    original_arrival: str | None = None
    booking_reference: str | None = None
    airline: str | None = None
    description: str = ""


class MissionContext(BaseModel):
    """Immutable mission context populated by the Context Agent.
    Downstream agents must not modify this."""
    origin: str
    destination: str
    departure_date: str  # YYYY-MM-DD
    traveler: TravelerProfile = Field(default_factory=TravelerProfile)
    disruption: DisruptionEvent
    budget_limit: float = 1000.0
    traveler_count: int = 1
    arrival_constraint: str | None = None  # e.g. "Before 21:00"


class AuditEntry(BaseModel):
    """Immutable audit trail entry."""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    agent: str
    action: str
    previous_version: int = 0
    new_version: int = 0
    summary: str = ""


def generate_mission_id() -> str:
    return f"mission-{uuid.uuid4().hex[:12]}"
