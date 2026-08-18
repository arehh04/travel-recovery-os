"""State ownership enforcement (Arch §6.8).

Defines which agent owns write access to which state section.
"""

from __future__ import annotations

# Ownership matrix: section -> agent that may write to it
OWNERSHIP_MATRIX: dict[str, str] = {
    "context": "ContextAgent",
    "flight": "FlightAgent",
    "hotel": "HotelAgent",
    "budget": "BudgetAgent",
    "policy": "PolicyAgent",
    "transport": "TransportAgent",
    "weather": "WeatherAgent",
    "validation": "CriticAgent",
    "reflection": "ReflectionAgent",
    "recommendation": "SummaryAgent",
}

# The Supervisor owns runtime metadata sections
SUPERVISOR_SECTIONS = {
    "execution_graph", "completed_agents", "failed_agents",
}


def check_ownership(section: str, agent: str) -> bool:
    """Return True if the agent is allowed to write to this section."""
    if section in SUPERVISOR_SECTIONS and agent == "SupervisorAgent":
        return True
    owner = OWNERSHIP_MATRIX.get(section)
    if owner is None:
        return False
    return owner == agent
