"""TR-OS core schemas: mission context, traveler, disruption events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

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
    airline_preference: Optional[str] = None
    seat_preference: Optional[str] = None
    loyalty_program: Optional[str] = None


class DisruptionEvent(BaseModel):
    """The trigger event that initiates a recovery mission."""
    disruption_type: DisruptionType
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    original_flight_number: Optional[str] = None
    original_departure: Optional[str] = None
    original_arrival: Optional[str] = None
    booking_reference: Optional[str] = None
    airline: Optional[str] = None
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
    arrival_constraint: Optional[str] = None  # e.g. "Before 21:00"


class AuditEntry(BaseModel):
    """Immutable audit trail entry."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str
    action: str
    previous_version: int = 0
    new_version: int = 0
    summary: str = ""


def generate_mission_id() -> str:
    return f"mission-{uuid.uuid4().hex[:12]}"
