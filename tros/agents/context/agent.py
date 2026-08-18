"""Context Agent — validates and normalizes mission input (Arch §7.2).

Responsibilities:
- Validate required information
- Normalize travel data
- Extract mission constraints
- Populate Shared Mission State
"""

from __future__ import annotations

from typing import Any

from tros.agents.base import BaseAgent
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.schemas.mission import MissionContext
from tros.state.mission_state import SharedMissionState


class ContextAgent(BaseAgent):
    NAME = "ContextAgent"

    def think(self, ctx: dict[str, Any],
              state: SharedMissionState) -> dict[str, Any]:
        """Plan: validate required fields and build mission context."""
        self.logger.info("Thinking: validating mission context inputs")
        return {"action": "validate_and_build_context"}

    def act(self, plan: dict[str, Any],
            state: SharedMissionState) -> dict[str, Any]:
        """Validate and build the MissionContext from state metadata."""
        # The mission context should have been pre-populated
        # by the caller (demo/engine) with raw input in state.flight
        raw = state.flight.get("_raw_input", {})
        warnings: list[str] = []

        origin = raw.get("origin", "")
        destination = raw.get("destination", "")
        departure_date = raw.get("departure_date", "")

        if not origin:
            warnings.append("Missing origin")
        if not destination:
            warnings.append("Missing destination")
        if not departure_date:
            warnings.append("Missing departure_date")

        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "budget_limit": raw.get("budget_limit", 1000.0),
            "warnings": warnings,
            "raw_input": raw,
        }

    def evaluate(self, observation: dict[str, Any],
                 state: SharedMissionState) -> dict[str, Any]:
        """Check completeness of the context."""
        warnings = observation.get("warnings", [])
        has_required = (
            observation.get("origin")
            and observation.get("destination")
            and observation.get("departure_date")
        )
        return {
            **observation,
            "complete": bool(has_required),
            "warnings": warnings,
        }

    def commit(self, result: dict[str, Any],
               state: SharedMissionState) -> AgentOutput:
        """Build and publish the mission context."""
        if not result.get("complete"):
            return AgentOutput(
                agent=self.NAME,
                status=AgentStatus.FAILED,
                confidence=0.0,
                reasoning_summary="Context incomplete: " + ", ".join(result.get("warnings", [])),
                warnings=result.get("warnings", []),
            )

        # Build MissionContext from the raw input
        raw = result.get("raw_input", {})
        from tros.schemas.mission import DisruptionEvent, TravelerProfile, TravelerType

        disruption = DisruptionEvent(
            disruption_type=raw.get("disruption_type", "FlightCancelled"),
            origin=result["origin"],
            destination=result["destination"],
            original_flight_number=raw.get("original_flight_number"),
            original_departure=raw.get("original_departure"),
            original_arrival=raw.get("original_arrival"),
            airline=raw.get("airline"),
            description=raw.get("description", ""),
        )

        traveler = TravelerProfile(
            traveler_type=raw.get("traveler_type", TravelerType.BUSINESS),
            name=raw.get("traveler_name", "Traveler"),
            airline_preference=raw.get("airline_preference"),
        )

        ctx = MissionContext(
            origin=result["origin"],
            destination=result["destination"],
            departure_date=result["departure_date"],
            traveler=traveler,
            disruption=disruption,
            budget_limit=result.get("budget_limit", 1000.0),
            arrival_constraint=raw.get("arrival_constraint"),
        )

        # Write to blackboard
        state.set_context(ctx, self.NAME)

        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.COMPLETED,
            confidence=0.98,
            reasoning_summary=f"Context validated: {ctx.origin} -> {ctx.destination} on {ctx.departure_date}",
            recommendation={"mission_context": ctx.model_dump()},
            evidence=[{"type": "context", "origin": ctx.origin,
                        "destination": ctx.destination, "date": ctx.departure_date}],
        )
