"""Tests for full production specialist agents and enterprise endpoints."""

import pytest
from fastapi.testclient import TestClient

from tros.adapters.flight.global_search import GlobalFlightSearchEngine
from tros.agents.hotel.agent import HotelAgent
from tros.agents.policy.agent import PolicyAgent
from tros.agents.transport.agent import TransportAgent
from tros.agents.weather.agent import WeatherAgent
from tros.api.app import create_app
from tros.api.db import init_db
from tros.schemas.agent_output import AgentStatus
from tros.schemas.mission import DisruptionEvent, DisruptionType, MissionContext, MissionStatus, TravelerProfile
from tros.state.mission_state import SharedMissionState


@pytest.fixture
def base_state() -> SharedMissionState:
    """Create a sample mission state for testing."""
    state = SharedMissionState(mission_id="test-mission-prod-001")
    state.context = MissionContext(
        origin="LHR",
        destination="JFK",
        departure_date="2026-08-25",
        budget_limit=1500.0,
        traveler_count=2,
        traveler=TravelerProfile(name="Alex Mercer"),
        disruption=DisruptionEvent(
            disruption_type=DisruptionType.FLIGHT_CANCELLED,
            origin="LHR",
            destination="JFK",
            original_flight_number="BA117",
        ),
    )
    return state


def test_weather_agent_evaluation(base_state: SharedMissionState):
    """Verify WeatherAgent assesses origin and destination weather risk."""
    agent = WeatherAgent()
    output = agent.execute(base_state)

    assert output.status == AgentStatus.COMPLETED
    assert output.confidence > 0.5
    assert "origin" in base_state.weather
    assert "destination" in base_state.weather
    assert base_state.weather["origin"]["airport"] == "LHR"
    assert base_state.weather["destination"]["airport"] == "JFK"
    assert "risk_score" in base_state.weather


def test_hotel_agent_provisioning(base_state: SharedMissionState):
    """Verify HotelAgent allocates distress hotel vouchers for cancellations."""
    agent = HotelAgent()
    output = agent.execute(base_state)

    assert output.status == AgentStatus.COMPLETED
    assert base_state.hotel["required"] is True
    vch = base_state.hotel["voucher"]
    assert vch is not None
    assert "HTL-VCH-" in vch["voucher_code"]
    assert vch["airline_duty_of_care_covered"] is True
    assert vch["meal_voucher_allowance_usd"] == 130.0  # 65 * 2 travelers


def test_transport_agent_intermodal():
    """Verify TransportAgent finds Eurostar between LHR/London and CDG/Paris."""
    state = SharedMissionState(mission_id="test-eurostar-001")
    state.context = MissionContext(
        origin="LHR",
        destination="CDG",
        departure_date="2026-08-25",
        budget_limit=800.0,
        traveler_count=1,
        traveler=TravelerProfile(name="Alex Mercer"),
        disruption=DisruptionEvent(
            disruption_type=DisruptionType.FLIGHT_CANCELLED,
            origin="LHR",
            destination="CDG",
            original_flight_number="BA304",
        ),
    )
    agent = TransportAgent()
    output = agent.execute(state)

    assert output.status == AgentStatus.COMPLETED
    base_transit = state.transport.get("transit")
    assert base_transit is not None
    assert "Eurostar" in base_transit["operator_service"]
    assert base_transit["duration_minutes"] == 136
    assert state.transport["carbon_saved_kg"] > 50.0


def test_policy_agent_eu261(base_state: SharedMissionState):
    """Verify PolicyAgent generates statutory EU261 €600 compensation for transatlantic route."""
    agent = PolicyAgent()
    output = agent.execute(base_state)

    assert output.status == AgentStatus.COMPLETED
    assert output.confidence >= 0.95
    claim = base_state.policy["claim"]
    assert claim is not None
    assert claim["amount_per_passenger"] == 600.0
    assert claim["total_compensation"] == 1200.0  # 2 passengers
    assert claim["currency"] == "EUR"
    assert "FORMAL NOTICE OF COMPENSATION CLAIM" in base_state.policy["claim_letter"]


def test_policy_agent_mavcom():
    """Verify PolicyAgent handles Malaysian MAVCOM rights for KUL routes."""
    state = SharedMissionState(mission_id="test-mavcom-001")
    state.context = MissionContext(
        origin="KUL",
        destination="SIN",
        departure_date="2026-08-25",
        budget_limit=500.0,
        traveler_count=1,
        traveler=TravelerProfile(name="Alex Mercer"),
        disruption=DisruptionEvent(
            disruption_type=DisruptionType.FLIGHT_DELAYED,
            origin="KUL",
            destination="SIN",
            original_flight_number="MH601",
        ),
    )
    agent = PolicyAgent()
    output = agent.execute(state)

    assert output.status == AgentStatus.COMPLETED
    claim = state.policy["claim"]
    assert "MAVCOM" in claim["regulation"]
    assert claim["currency"] == "MYR"


def test_global_flight_search_engine():
    """Verify GlobalFlightSearchEngine returns multi-carrier inventory."""
    engine = GlobalFlightSearchEngine()
    results = engine.search_worldwide("KUL", "NRT", "2026-08-25", "USD")

    assert len(results) >= 3
    first = results[0]
    assert first["origin"] == "KUL"
    assert first["destination"] == "NRT"
    assert first["price"] > 0
    assert first["flight_number"].startswith(("MH", "AK", "JL", "NH", "SQ", "BA", "AA", "QR", "EK"))


def test_profile_api_endpoints():
    """Verify GET and PUT /api/v1/profile."""
    init_db()
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/v1/profile")
    assert res.status_code == 200
    data = res.json()
    assert "full_name" in data
    assert "loyalty_accounts" in data

    # Update profile
    data["seat_preference"] = "WINDOW"
    put_res = client.put("/api/v1/profile", json=data)
    assert put_res.status_code == 200
    assert put_res.json()["seat_preference"] == "WINDOW"


def test_claims_api_endpoints():
    """Verify GET /api/v1/claims/{mission_id}."""
    init_db()
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/v1/claims/test-mission-prod-001")
    assert res.status_code == 200
    data = res.json()
    assert "amount" in data
    assert data["amount"] > 0
    assert "regulation" in data

