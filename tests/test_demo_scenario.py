"""End-to-end test for the cancelled flight demo scenario."""

import pytest
from tros.schemas.mission import MissionStatus
from tros.schemas.agent_output import AgentStatus


class TestDemoScenario:
    """Integration test — runs the full pipeline without Atlas CLI."""

    def test_mission_state_structure(self):
        """Verify that the mission state has correct structure."""
        from tros.state.mission_state import SharedMissionState
        state = SharedMissionState(mission_id="test-e2e")
        assert state.status == MissionStatus.CREATED
        assert state.flight == {}
        assert state.agent_outputs == {}

    def test_context_agent_validates(self):
        """Test Context Agent with valid input."""
        from tros.agents.context import ContextAgent
        from tros.state.mission_state import SharedMissionState

        state = SharedMissionState(mission_id="test-ctx")
        state.update_section("flight", {
            "_raw_input": {
                "origin": "KUL",
                "destination": "NRT",
                "departure_date": "2026-08-20",
                "disruption_type": "FlightCancelled",
            }
        }, "System")

        agent = ContextAgent()
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED
        assert output.confidence > 0.9
        assert state.context is not None
        assert state.context.origin == "KUL"

    def test_context_agent_fails_missing_data(self):
        """Test Context Agent fails with missing required fields."""
        from tros.agents.context import ContextAgent
        from tros.state.mission_state import SharedMissionState

        state = SharedMissionState(mission_id="test-ctx-fail")
        state.update_section("flight", {
            "_raw_input": {"origin": "KUL"}  # Missing destination & date
        }, "System")

        agent = ContextAgent()
        output = agent.execute(state)
        assert output.status == AgentStatus.FAILED

    def test_critic_agent(self):
        """Test Critic Agent with a flight output present."""
        from tros.agents.critic import CriticAgent
        from tros.state.mission_state import SharedMissionState
        from tros.schemas.agent_output import AgentOutput

        state = SharedMissionState(mission_id="test-critic")
        flight_output = AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.92,
            evidence=[{"type": "flight_search"}],
        )
        state.update_agent_output(flight_output)
        state.update_section("flight", {
            "best_option": {"candidate": {"price": 400}}
        }, "FlightAgent")

        from tros.schemas.mission import MissionContext, DisruptionEvent, DisruptionType
        state.set_context(MissionContext(
            origin="KUL", destination="NRT", departure_date="2026-08-20",
            disruption=DisruptionEvent(
                disruption_type=DisruptionType.FLIGHT_CANCELLED,
                origin="KUL", destination="NRT"),
            budget_limit=1000.0,
        ))

        critic = CriticAgent()
        output = critic.execute(state)
        assert output.status == AgentStatus.COMPLETED
        assert output.recommendation.get("approved") is True

    def test_summary_agent_produces_text(self):
        """Test that Summary Agent generates a recovery plan."""
        from tros.agents.summary import SummaryAgent
        from tros.state.mission_state import SharedMissionState
        from tros.schemas.mission import MissionContext, DisruptionEvent, DisruptionType

        state = SharedMissionState(mission_id="test-summary")
        state.set_context(MissionContext(
            origin="KUL", destination="NRT", departure_date="2026-08-20",
            disruption=DisruptionEvent(
                disruption_type=DisruptionType.FLIGHT_CANCELLED,
                origin="KUL", destination="NRT"),
        ))
        state.update_section("flight", {
            "best_option": {
                "candidate": {
                    "flight_number": "SQ318",
                    "carrier": "SQ",
                    "departure_time": "0930",
                    "arrival_time": "1835",
                    "price": 420.0,
                    "currency": "USD",
                    "duration_minutes": 545,
                },
                "score": 85.5,
                "reasoning": "early arrival, direct flight",
            },
            "alternatives": [],
            "total_candidates_evaluated": 15,
        }, "FlightAgent")
        state.update_section("validation", {"approved": True, "issues": []}, "CriticAgent")
        state.update_section("reflection", {"changes": [], "improved": False}, "ReflectionAgent")

        summary = SummaryAgent()
        output = summary.execute(state)
        assert output.status == AgentStatus.COMPLETED
        assert "SQ318" in output.recommendation.get("summary", "")
        assert "TRIP RECOVERY PLAN" in output.recommendation.get("summary", "")
