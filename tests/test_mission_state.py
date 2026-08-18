"""Tests for Shared Mission State (Blackboard)."""

import pytest
from tros.state.mission_state import SharedMissionState
from tros.schemas.mission import (
    DisruptionEvent, DisruptionType, MissionContext,
    MissionStatus, TravelerProfile,
)
from tros.schemas.agent_output import AgentOutput, AgentStatus


def _make_state() -> SharedMissionState:
    return SharedMissionState(mission_id="test-001")


def _make_context() -> MissionContext:
    return MissionContext(
        origin="KUL",
        destination="NRT",
        departure_date="2026-08-20",
        disruption=DisruptionEvent(
            disruption_type=DisruptionType.FLIGHT_CANCELLED,
            origin="KUL",
            destination="NRT",
        ),
    )


class TestMissionState:
    def test_initial_state(self):
        state = _make_state()
        assert state.mission_id == "test-001"
        assert state.status == MissionStatus.CREATED
        assert state.version == 1
        assert state.context is None
        assert len(state.audit) == 0

    def test_transition(self):
        state = _make_state()
        state.transition(MissionStatus.RUNNING, "TestAgent")
        assert state.status == MissionStatus.RUNNING
        assert len(state.audit) == 1
        assert state.audit[0].agent == "TestAgent"

    def test_set_context(self):
        state = _make_state()
        ctx = _make_context()
        state.set_context(ctx)
        assert state.context is not None
        assert state.context.origin == "KUL"
        assert state.status == MissionStatus.CONTEXT_LOADED

    def test_update_agent_output(self):
        state = _make_state()
        output = AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.92,
            reasoning_summary="Found 3 candidates",
        )
        state.update_agent_output(output)
        assert "FlightAgent" in state.agent_outputs
        assert state.agent_outputs["FlightAgent"].confidence == 0.92
        assert "FlightAgent" in state.completed_agents
        assert state.version == 2

    def test_update_section(self):
        state = _make_state()
        state.update_section("flight", {"best": "SQ318"}, "FlightAgent")
        assert state.flight["best"] == "SQ318"
        assert state.version == 2

    def test_audit_trail(self):
        state = _make_state()
        state.transition(MissionStatus.RUNNING, "Supervisor")
        output = AgentOutput(agent="FlightAgent", confidence=0.9)
        state.update_agent_output(output)
        assert len(state.audit) == 2
        assert state.audit[0].action == "status_transition"
        assert state.audit[1].action == "output_committed"

    def test_version_increments(self):
        state = _make_state()
        assert state.version == 1
        output1 = AgentOutput(agent="FlightAgent", confidence=0.9)
        state.update_agent_output(output1)
        assert state.version == 2
        output2 = AgentOutput(agent="BudgetAgent", confidence=0.8)
        state.update_agent_output(output2)
        assert state.version == 3
