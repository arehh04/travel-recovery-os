"""Tests for TR-OS Agent Swarm Architecture."""

import asyncio

import pytest
from starlette.testclient import TestClient

from tros.api.app import create_app
from tros.swarm import (
    AlliancePartnerScout,
    CandidateRoute,
    ContextWorker,
    CriticRankingWorker,
    DirectFlightScout,
    DisruptionEvent,
    IntermodalScout,
    SwarmOrchestrator,
    apply_swarm_update,
    create_initial_swarm_state,
)


@pytest.fixture
def sample_disruption() -> DisruptionEvent:
    return {
        "pnr": "TEST-12345",
        "original_flight": "BA100",
        "disruption_type": "CANCELLED",
        "delay_minutes": 180,
        "affected_passengers": ["John Doe", "Jane Doe"],
    }


def test_initial_state_creation(sample_disruption):
    state = create_initial_swarm_state(sample_disruption)
    assert state["disruption"]["pnr"] == "TEST-12345"
    assert state["inventory_candidates"] == []
    assert state["selected_solution"] is None
    assert state["human_consensus_status"] == "PENDING"
    assert len(state["agent_logs"]) == 1


def test_state_reducer_operator_add(sample_disruption):
    state = create_initial_swarm_state(sample_disruption)

    route_1: CandidateRoute = {
        "flight_number": "BA102",
        "departure_time": "2026-08-21T10:00:00Z",
        "arrival_time": "2026-08-21T17:00:00Z",
        "price_differential": 0.0,
        "score": 0.9,
        "carrier": "BA",
    }
    route_2: CandidateRoute = {
        "flight_number": "AA800",
        "departure_time": "2026-08-21T11:00:00Z",
        "arrival_time": "2026-08-21T18:00:00Z",
        "price_differential": 50.0,
        "score": 0.85,
        "carrier": "AA",
    }

    # Worker 1 adds route 1
    update1 = {
        "inventory_candidates": [route_1],
        "agent_logs": ["Worker 1 found route 1"],
    }
    state = apply_swarm_update(state, update1)
    assert len(state["inventory_candidates"]) == 1
    assert len(state["agent_logs"]) == 2

    # Worker 2 adds route 2 (accumulated via operator.add)
    update2 = {
        "inventory_candidates": [route_2],
        "agent_logs": ["Worker 2 found route 2"],
    }
    state = apply_swarm_update(state, update2)
    assert len(state["inventory_candidates"]) == 2
    assert state["inventory_candidates"][0]["flight_number"] == "BA102"
    assert state["inventory_candidates"][1]["flight_number"] == "AA800"
    assert len(state["agent_logs"]) == 3


def test_context_worker(sample_disruption):
    async def _test():
        worker = ContextWorker()
        state = create_initial_swarm_state(sample_disruption)
        update = await worker.run(state)
        assert "passenger_context" in update
        assert update["passenger_context"]["traveler_count"] == 2
        assert "agent_logs" in update

    asyncio.run(_test())


def test_scout_workers(sample_disruption):
    async def _test():
        state = create_initial_swarm_state(sample_disruption)
        
        direct_scout = DirectFlightScout()
        alliance_scout = AlliancePartnerScout()
        intermodal_scout = IntermodalScout()

        res_direct = await direct_scout.run(state)
        res_alliance = await alliance_scout.run(state)
        res_intermodal = await intermodal_scout.run(state)

        assert len(res_direct["inventory_candidates"]) >= 1
        assert len(res_alliance["inventory_candidates"]) >= 1
        assert len(res_intermodal["inventory_candidates"]) >= 1

    asyncio.run(_test())


def test_critic_and_ranking(sample_disruption):
    async def _test():
        state = create_initial_swarm_state(sample_disruption)
        state = apply_swarm_update(
            state,
            {
                "passenger_context": {"preferred_carrier": "BA"},
                "inventory_candidates": [
                    {
                        "flight_number": "AA100",
                        "departure_time": "T1",
                        "arrival_time": "T2",
                        "price_differential": 100.0,
                        "score": 0.8,
                        "carrier": "AA",
                    },
                    {
                        "flight_number": "BA200",
                        "departure_time": "T1",
                        "arrival_time": "T2",
                        "price_differential": 0.0,
                        "score": 0.9,
                        "carrier": "BA",
                    },
                ],
            },
        )

        critic = CriticRankingWorker()
        update = await critic.run(state)
        assert update["selected_solution"] is not None
        assert update["selected_solution"]["flight_number"] == "BA200"

    asyncio.run(_test())


def test_consensus_and_execution_lifecycle(sample_disruption):
    async def _test():
        orchestrator = SwarmOrchestrator()

        # Full execution
        res_state = await orchestrator.execute(sample_disruption, auto_execute_if_approved=False)
        assert len(res_state["inventory_candidates"]) >= 3
        assert res_state["selected_solution"] is not None

        # If pending, approve and execute
        if res_state["human_consensus_status"] == "PENDING":
            final_state = await orchestrator.approve_and_execute(res_state)
            assert final_state["human_consensus_status"] == "APPROVED"
            assert final_state["execution_receipt"] is not None
            assert final_state["execution_receipt"]["status"] == "CONFIRMED"

    asyncio.run(_test())


def test_rejection_flow(sample_disruption):
    async def _test():
        orchestrator = SwarmOrchestrator()
        state = await orchestrator.execute(sample_disruption, auto_execute_if_approved=False)
        rejected_state = await orchestrator.reject(state, reason="Schedule conflict")
        assert rejected_state["human_consensus_status"] == "REJECTED"
        assert "Schedule conflict" in rejected_state["agent_logs"][-1]

    asyncio.run(_test())


def test_stream_flow(sample_disruption):
    async def _test():
        orchestrator = SwarmOrchestrator()
        steps = []
        async for item in orchestrator.stream(sample_disruption):
            steps.append(item["step"])

        assert "INITIALIZED" in steps
        assert "CONTEXT_ENRICHED" in steps
        assert "CRITIC_RANKED" in steps
        assert "CONSENSUS_EVALUATED" in steps

    asyncio.run(_test())


def test_swarm_api_endpoints():
    app = create_app()
    client = TestClient(app)

    # 1. Run swarm endpoint
    payload = {
        "pnr": "API-TEST",
        "original_flight": "BA117",
        "disruption_type": "CANCELLED",
        "delay_minutes": 120,
        "affected_passengers": ["Agent Smith"],
        "auto_execute": False,
    }
    resp = client.post("/api/v1/swarm/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["disruption"]["pnr"] == "API-TEST"
    assert len(data["inventory_candidates"]) >= 3
    assert data["selected_solution"] is not None

    # 2. Approve endpoint
    approve_resp = client.post("/api/v1/swarm/approve", json={"state": data})
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["human_consensus_status"] == "APPROVED"
    assert approved_data["execution_receipt"] is not None
    assert approved_data["execution_receipt"]["pnr"] == "API-TEST"
