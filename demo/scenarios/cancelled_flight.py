"""Demo scenario: Cancelled flight KUL → NRT.

Demonstrates the full TR-OS vertical slice:
  FlightCancelled → Mission → Supervisor → Context → Flight → Atlas →
  Ranking → Budget → Critic → Reflection → Summary → Recovery Plan

With LLM (when TR_OS_LLM_API_KEY is set):
  Agents use LLM reasoning on top of deterministic checks.
  Thought traces are captured in state for display.
"""

from __future__ import annotations

from tros.agents.supervisor import SupervisorAgent
from tros.config import LLM_API_KEY
from tros.engine.events import flight_cancelled
from tros.engine.mission import MissionEngine
from tros.state.mission_state import SharedMissionState


def run_cancelled_flight_demo() -> SharedMissionState:
    """Execute the cancelled flight demo scenario.

    Scenario:
    - Original flight MH318 KUL → NRT on 2026-08-20 has been cancelled
    - Traveler is a business traveler
    - Budget limit: $1000 USD
    - System must find and rank alternative flights

    When TR_OS_LLM_API_KEY is set, the Supervisor and all LLM-capable
    agents use LLM reasoning (deterministic checks always run as safety net).
    """
    # Step 1: Create the disruption event
    event = flight_cancelled(
        origin="KUL",
        destination="NRT",
        flight_number="MH318",
        airline="Malaysia Airlines",
        departure="08:30",
        arrival="16:45",
        booking_ref="ABC123",
        description="Flight MH318 from KUL to NRT has been cancelled by the airline.",
    )

    # Step 2: Create mission via Mission Engine
    engine = MissionEngine()
    state = engine.create_mission(
        event=event,
        departure_date="2026-08-20",
        budget_limit=1000.0,
    )

    # Step 3: Prepare raw input for the Context Agent
    raw_input = {
        "origin": "KUL",
        "destination": "NRT",
        "departure_date": "2026-08-20",
        "disruption_type": "FlightCancelled",
        "original_flight_number": "MH318",
        "original_departure": "0830",
        "original_arrival": "1645",
        "airline": "Malaysia Airlines",
        "booking_reference": "ABC123",
        "description": "Flight MH318 from KUL to NRT has been cancelled by the airline.",
        "traveler_type": "Business",
        "traveler_name": "Business Traveler",
        "airline_preference": "MH",
        "budget_limit": 1000.0,
    }

    # Step 4: Optionally create LLM client
    llm_client = None
    if LLM_API_KEY:
        from tros.llm.client import LLMClient
        llm_client = LLMClient()
        if llm_client.is_available:
            import logging
            logging.getLogger("TROS").info(
                "LLM mode enabled (model=%s)", llm_client._model)
        else:
            llm_client = None

    # Step 5: Run the Supervisor (with or without LLM)
    supervisor = SupervisorAgent(llm_client=llm_client)
    state = supervisor.run_mission(state, raw_input)

    return state
