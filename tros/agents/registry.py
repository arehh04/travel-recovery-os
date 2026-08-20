"""Agent registry — maps agent names to their classes (Arch §4.7)."""

from __future__ import annotations


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
