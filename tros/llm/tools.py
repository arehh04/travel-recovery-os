"""Tool definitions for LLM function calling (Arch §5.6).

Defines the tools available to LLM-driven agents.
Each tool is a JSON schema matching the OpenAI function calling format.

Tools are executed by deterministic code — the LLM only requests them.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Flight Search Tool — used by FlightAgent
# ---------------------------------------------------------------------------

SEARCH_FLIGHTS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_flights",
        "description": (
            "Search live alternative flights through the Atlas Flight Booking service. "
            "Returns ranked candidates with deterministic scores based on arrival time, "
            "cost, duration, stops, and airline preference. "
            "This is a READ-ONLY search; it does not book or modify any state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin airport IATA code (e.g. KUL)",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination airport IATA code (e.g. NRT)",
                },
                "departure_date": {
                    "type": "string",
                    "description": "Departure date in YYYY-MM-DD format",
                },
                "adults": {
                    "type": "integer",
                    "description": "Number of adult passengers",
                    "default": 1,
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code for pricing (e.g. USD)",
                    "default": "USD",
                },
            },
            "required": ["origin", "destination", "departure_date"],
        },
    },
}


# ---------------------------------------------------------------------------
# Read Mission State Tool — used by Critic, Reflection, Summary
# ---------------------------------------------------------------------------

READ_MISSION_STATE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_mission_state",
        "description": (
            "Read the current Shared Mission State. Returns the requested "
            "sections as JSON for analysis. Read-only — does not modify state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "description": "Which state sections to read",
                    "items": {
                        "type": "string",
                        "enum": [
                            "context", "flight", "hotel", "budget",
                            "policy", "transport", "weather",
                            "validation", "reflection",
                            "agent_outputs", "recommendation",
                        ],
                    },
                },
            },
            "required": ["sections"],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool registry — maps tool names to their definitions
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "search_flights": SEARCH_FLIGHTS_TOOL,
    "read_mission_state": READ_MISSION_STATE_TOOL,
}


def get_tools_for_agent(agent_name: str) -> list[dict[str, Any]]:
    """Return the tool definitions available to a specific agent."""
    agent_tools: dict[str, list[str]] = {
        "FlightAgent": ["search_flights"],
        "CriticAgent": ["read_mission_state"],
        "ReflectionAgent": ["read_mission_state"],
        "SummaryAgent": ["read_mission_state"],
        "SupervisorAgent": ["read_mission_state"],
    }
    tool_names = agent_tools.get(agent_name, [])
    return [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]
