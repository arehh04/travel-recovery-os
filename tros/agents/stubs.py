"""Stub agents for milestone 1: Hotel, Budget, Policy, Transport, Weather.

These provide clean interfaces that can be replaced with real
implementations without architectural changes.
"""

from __future__ import annotations

from typing import Any

from tros.agents.base import BaseAgent
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.state.mission_state import SharedMissionState


class StubAgent(BaseAgent):
    """Base for stub agents that return structured placeholders."""

    STUB_MESSAGE = "Not yet implemented in milestone 1"

    def think(self, ctx: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        return {"action": "stub"}

    def act(self, plan: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        return {"stub": True}

    def evaluate(self, observation: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        return {**observation, "complete": True}

    def commit(self, result: dict[str, Any], state: SharedMissionState) -> AgentOutput:
        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.SKIPPED,
            confidence=0.0,
            reasoning_summary=self.STUB_MESSAGE,
            warnings=[self.STUB_MESSAGE],
        )


class HotelAgent(StubAgent):
    NAME = "HotelAgent"
    STUB_MESSAGE = "Hotel recovery not yet integrated"


class BudgetAgent(BaseAgent):
    """Budget agent — computes structured budget assessment (Phase 5).

    Numerical calculations are always deterministic.
    LLM may explain budget implications but may not alter:
    price, budget limit, remaining budget, within_budget.
    """
    NAME = "BudgetAgent"

    def think(self, ctx: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        return {"action": "calculate_budget"}

    def act(self, plan: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        flight = state.flight
        best_option = flight.get("best_option", {})
        candidate = best_option.get("candidate", {})
        best_price = candidate.get("price", 0)
        flight_number = candidate.get("flight_number", "N/A")
        currency = candidate.get("currency", "USD")
        budget_limit = state.context.budget_limit if state.context else 1000.0
        within_budget = best_price <= budget_limit
        remaining = budget_limit - best_price
        margin_pct = ((budget_limit - best_price) / budget_limit * 100) if budget_limit > 0 else 0.0

        # Build per-candidate assessments from alternatives
        alternatives = flight.get("alternatives", [])
        assessments: list[dict[str, Any]] = []
        for alt in alternatives:
            alt_c = alt.get("candidate", {})
            alt_price = alt_c.get("price", 0)
            assessments.append({
                "flight_number": alt_c.get("flight_number", ""),
                "price": alt_price,
                "currency": alt_c.get("currency", "USD"),
                "budget_limit": budget_limit,
                "remaining_budget": budget_limit - alt_price,
                "within_budget": alt_price <= budget_limit,
                "margin_percentage": round(
                    ((budget_limit - alt_price) / budget_limit * 100)
                    if budget_limit > 0 else 0.0, 2
                ),
            })

        return {
            # Legacy fields (backward compatible)
            "flight_cost": best_price,
            "hotel_cost": 0,
            "transport_cost": 0,
            "total_cost": best_price,
            "budget_limit": budget_limit,
            "within_budget": within_budget,
            # Phase 5 structured assessment
            "assessment": {
                "flight_number": flight_number,
                "price": best_price,
                "currency": currency,
                "budget_limit": budget_limit,
                "remaining_budget": remaining,
                "within_budget": within_budget,
                "margin_percentage": round(margin_pct, 2),
            },
            "alternative_assessments": assessments,
        }

    def evaluate(self, observation: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        return observation

    def commit(self, result: dict[str, Any], state: SharedMissionState) -> AgentOutput:
        state.update_section("budget", result, self.NAME)
        # Also write Phase 5 structured assessment
        assessment = result.get("assessment", {})
        state.update_section("budget_assessment", assessment, self.NAME)

        within = result.get("within_budget")
        confidence = 0.90 if within else 0.60
        price = result.get("total_cost", 0)
        limit = result.get("budget_limit", 0)
        margin = assessment.get("margin_percentage", 0)

        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            reasoning_summary=(
                f"Total recovery cost: ${price:.2f}. "
                f"Budget: ${limit:.2f}. "
                f"{'Within budget' if within else 'Exceeds budget'} "
                f"(margin: {margin:.1f}%)."
            ),
            recommendation=result,
            result=result,
        )


class PolicyAgent(StubAgent):
    NAME = "PolicyAgent"
    STUB_MESSAGE = "Airline policy lookup not yet integrated"


class TransportAgent(StubAgent):
    NAME = "TransportAgent"
    STUB_MESSAGE = "Ground transport not yet integrated"


class WeatherAgent(StubAgent):
    NAME = "WeatherAgent"
    STUB_MESSAGE = "Weather risk assessment not yet integrated"
