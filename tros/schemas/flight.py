"""Flight-specific schemas for candidates, ranking, and recommendations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FlightCandidate(BaseModel):
    """A single flight candidate returned by the Atlas adapter."""
    offer_id: str
    flight_number: str
    carrier: str
    departure_airport: str
    arrival_airport: str
    departure_time: str          # HHMM format
    arrival_time: str            # HHMM format
    duration_minutes: int
    stops: int = 0
    cabin_class: int = 1
    price: float
    currency: str = "USD"
    base_fare: float = 0.0
    tax: float = 0.0
    operating_carrier: str | None = None
    bookable: bool = False
    price_status: str = "reference"


class RankedFlight(BaseModel):
    """A flight candidate enriched with a composite ranking score."""
    candidate: FlightCandidate
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    arrival_score: float = 0.0
    cost_score: float = 0.0
    delay_score: float = 0.0
    stops_score: float = 0.0
    preference_score: float = 0.0
    reasoning: str = ""


class FlightRecommendation(BaseModel):
    """The Flight Agent's published recommendation."""
    best_option: RankedFlight
    alternatives: list[RankedFlight] = Field(default_factory=list)
    total_candidates_evaluated: int = 0
    search_origin: str = ""
    search_destination: str = ""
    search_date: str = ""
