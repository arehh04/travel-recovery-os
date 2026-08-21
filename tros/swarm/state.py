"""TR-OS Agent Swarm State Definition & Reducer Logic.

Implements TypedDict models for disruption events, candidate routes, and swarm state
with support for Annotated[List[T], operator.add] state reduction across parallel workers.
"""

from __future__ import annotations

import copy
import operator
from typing import Annotated, Any

from typing_extensions import TypedDict


class DisruptionEvent(TypedDict):
    """Event representing a flight or itinerary disruption."""

    pnr: str
    original_flight: str
    disruption_type: str  # 'CANCELLED', 'DELAY_MISSED_CONN', etc.
    delay_minutes: int
    affected_passengers: list[str]


class CandidateRoute(TypedDict):
    """A viable recovery flight or multi-modal journey option found by the swarm."""

    flight_number: str
    departure_time: str
    arrival_time: str
    price_differential: float
    score: float
    carrier: str


class AgentSwarmState(TypedDict):
    """Central blackboard state for the Agent Swarm.

    Uses Annotated[List, operator.add] to cleanly accumulate findings from parallel
    scout agents and collect append-only audit traces from all participating workers.
    """

    disruption: DisruptionEvent
    passenger_context: dict[str, Any]
    inventory_candidates: Annotated[list[CandidateRoute], operator.add]
    selected_solution: CandidateRoute | None
    human_consensus_status: str  # 'PENDING', 'APPROVED', 'REJECTED'
    execution_receipt: dict[str, Any] | None
    agent_logs: Annotated[list[str], operator.add]


def create_initial_swarm_state(
    disruption: DisruptionEvent,
    passenger_context: dict[str, Any] | None = None,
) -> AgentSwarmState:
    """Create a new initialized AgentSwarmState."""
    return {
        "disruption": disruption,
        "passenger_context": passenger_context or {},
        "inventory_candidates": [],
        "selected_solution": None,
        "human_consensus_status": "PENDING",
        "execution_receipt": None,
        "agent_logs": [f"Swarm initialized for PNR {disruption.get('pnr', 'UNKNOWN')}"],
    }


def apply_swarm_update(
    current_state: AgentSwarmState,
    update: dict[str, Any],
) -> AgentSwarmState:
    """Merge a partial state update into the current AgentSwarmState.

    Correctly handles Annotated[List, operator.add] fields by concatenating lists
    instead of overwriting them.
    """
    new_state = copy.deepcopy(current_state)

    # Reducer fields that accumulate additions
    additive_fields = {"inventory_candidates", "agent_logs"}

    for key, value in update.items():
        if key in additive_fields and isinstance(value, list):
            existing_list = new_state.get(key, [])
            new_state[key] = operator.add(existing_list, value)  # type: ignore[literal-required]
        elif key == "passenger_context" and isinstance(value, dict):
            existing_ctx = new_state.get("passenger_context", {})
            new_ctx = copy.deepcopy(existing_ctx)
            new_ctx.update(value)
            new_state["passenger_context"] = new_ctx
        else:
            new_state[key] = value  # type: ignore[literal-required]

    return new_state
