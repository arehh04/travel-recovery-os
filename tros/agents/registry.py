"""Agent registry — maps agent names to their classes (Arch §4.7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tros.agents.base import BaseAgent


def get_agent_registry() -> dict[str, str]:
    """Return the agent registry with responsibilities."""
    return {
        "SupervisorAgent": "Mission orchestration",
        "ContextAgent": "Mission initialization",
        "FlightAgent": "Flight recovery",
        "HotelAgent": "Accommodation recovery",
        "BudgetAgent": "Cost optimization",
        "PolicyAgent": "Airline rules",
        "TransportAgent": "Ground transport",
        "WeatherAgent": "Environmental risk",
        "CriticAgent": "Validation",
        "ReflectionAgent": "Optimization",
        "SummaryAgent": "User explanation",
    }
