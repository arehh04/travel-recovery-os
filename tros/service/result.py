"""Public MissionResult — sanitized API-facing result model (Phase 7).

Exposes only safe, user-relevant information.
Never includes: raw LLM messages, prompts, internal tool arguments,
debug traces, internal exceptions, API credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FlightInfo:
    """Public flight recommendation."""
    flight_number: str = ""
    carrier: str = ""
    departure: str = ""
    arrival: str = ""
    duration_minutes: int = 0
    stops: int = 0
    price: float = 0.0
    currency: str = "USD"
    score: float = 0.0


@dataclass
class RecoveryInfo:
    """Public recovery summary."""
    occurred: bool = False
    attempts: int = 0
    reason: str = ""
    recovered: bool = False


@dataclass
class ConflictInfo:
    """Public conflict summary."""
    count: int = 0
    has_critical: bool = False


@dataclass
class ExecutionMetadata:
    """Public execution metadata (no secrets)."""
    mission_id: str = ""
    execution_id: str = ""
    request_id: str = ""
    status: str = ""
    duration_ms: int = 0


@dataclass
class MissionResult:
    """Sanitized public result of a mission execution.

    This is the model returned by MissionService and suitable for
    JSON serialization in a future HTTP API.
    """
    mission_id: str = ""
    execution_id: str = ""
    status: str = ""
    recommendation: FlightInfo | None = None
    alternatives: list[FlightInfo] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    recovery: RecoveryInfo = field(default_factory=RecoveryInfo)
    conflicts: ConflictInfo = field(default_factory=ConflictInfo)
    execution_metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON API response."""
        rec = self.recommendation
        return {
            "mission_id": self.mission_id,
            "execution_id": self.execution_id,
            "status": self.status,
            "recommendation": {
                "flight_number": rec.flight_number if rec else "",
                "carrier": rec.carrier if rec else "",
                "departure": rec.departure if rec else "",
                "arrival": rec.arrival if rec else "",
                "duration_minutes": rec.duration_minutes if rec else 0,
                "stops": rec.stops if rec else 0,
                "price": rec.price if rec else 0.0,
                "currency": rec.currency if rec else "USD",
                "score": rec.score if rec else 0.0,
            } if rec else None,
            "alternatives": [
                {
                    "flight_number": a.flight_number,
                    "carrier": a.carrier,
                    "price": a.price,
                    "currency": a.currency,
                    "score": a.score,
                }
                for a in self.alternatives
            ],
            "budget": self.budget,
            "confidence": self.confidence,
            "recovery": {
                "occurred": self.recovery.occurred,
                "attempts": self.recovery.attempts,
                "recovered": self.recovery.recovered,
                "reason": self.recovery.reason,
            },
            "conflicts": {
                "count": self.conflicts.count,
                "has_critical": self.conflicts.has_critical,
            },
            "execution_metadata": {
                "mission_id": self.execution_metadata.mission_id,
                "execution_id": self.execution_metadata.execution_id,
                "request_id": self.execution_metadata.request_id,
                "status": self.execution_metadata.status,
                "duration_ms": self.execution_metadata.duration_ms,
            },
        }

    @classmethod
    def from_state(cls, state: Any, execution_context: Any = None) -> MissionResult:
        """Build a sanitized MissionResult from internal SharedMissionState."""
        flight = state.flight or {}
        best = flight.get("best_option", {})
        candidate = best.get("candidate", {})
        alternatives_raw = flight.get("alternatives", [])

        mission_decision = state.mission_decision or {}
        recovery_state = state.recovery_state or {}
        conflict_report = state.conflict_report or {}
        budget_assessment = state.budget_assessment or {}

        # Build recommendation
        rec = FlightInfo(
            flight_number=candidate.get("flight_number", ""),
            carrier=candidate.get("carrier", ""),
            departure=candidate.get("departure_time", ""),
            arrival=candidate.get("arrival_time", ""),
            duration_minutes=candidate.get("duration_minutes", 0),
            stops=candidate.get("stops", 0),
            price=candidate.get("price", 0.0),
            currency=candidate.get("currency", "USD"),
            score=best.get("score", 0.0),
        ) if candidate.get("flight_number") else None

        # Build alternatives
        alts = [
            FlightInfo(
                flight_number=a.get("candidate", {}).get("flight_number", ""),
                carrier=a.get("candidate", {}).get("carrier", ""),
                price=a.get("candidate", {}).get("price", 0.0),
                currency=a.get("candidate", {}).get("currency", "USD"),
                score=a.get("score", 0.0),
            )
            for a in alternatives_raw[:4]
        ]

        # Execution metadata
        meta = ExecutionMetadata(
            mission_id=execution_context.mission_id if execution_context else state.mission_id,
            execution_id=execution_context.execution_id if execution_context else "",
            request_id=execution_context.request_id if execution_context else "",
            status=mission_decision.get("status", state.status.value if hasattr(state.status, 'value') else ""),
            duration_ms=0,
        )

        return cls(
            mission_id=meta.mission_id,
            execution_id=meta.execution_id,
            status=meta.status,
            recommendation=rec,
            alternatives=alts,
            budget=budget_assessment,
            confidence=mission_decision.get("confidence", 0.0),
            recovery=RecoveryInfo(
                occurred=recovery_state.get("recovered", False),
                attempts=recovery_state.get("attempts_used", 0),
                reason=recovery_state.get("reason", ""),
                recovered=recovery_state.get("recovered", False),
            ),
            conflicts=ConflictInfo(
                count=len(conflict_report.get("conflicts", [])),
                has_critical=conflict_report.get("has_critical_conflict", False),
            ),
            execution_metadata=meta,
        )
