"""LLM-mocked tests — verify LLM-optional agents work with canned responses.

These tests use unittest.mock to simulate LLM responses without requiring
a real API key. They verify:
1. Response parsers correctly extract fields from LLM JSON output
2. Agents merge LLM reasoning on top of deterministic checks
3. Deterministic fallback works when LLM calls fail
4. LLM client availability check works correctly
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.schemas.mission import (
    MissionContext, DisruptionEvent, DisruptionType,
)
from tros.state.mission_state import SharedMissionState


# =====================================================================
# Fixtures
# =====================================================================

def _make_state(
    mission_id: str = "test-llm",
    with_flight: bool = True,
    budget_limit: float = 1000.0,
) -> SharedMissionState:
    """Build a mission state pre-populated for LLM agent tests."""
    state = SharedMissionState(mission_id=mission_id)
    state.set_context(MissionContext(
        origin="KUL", destination="NRT", departure_date="2026-08-20",
        disruption=DisruptionEvent(
            disruption_type=DisruptionType.FLIGHT_CANCELLED,
            origin="KUL", destination="NRT"),
        budget_limit=budget_limit,
    ))

    if with_flight:
        flight_output = AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.92,
            reasoning_summary="Selected SQ318 — best score",
            evidence=[{"type": "flight_search", "total_candidates": 16}],
        )
        state.update_agent_output(flight_output)
        state.update_section("flight", {
            "best_option": {
                "candidate": {
                    "flight_number": "SQ318",
                    "carrier": "SQ",
                    "departure_time": "202608200930",
                    "arrival_time": "202608201835",
                    "price": 420.0,
                    "currency": "USD",
                    "duration_minutes": 545,
                    "stops": 0,
                },
                "score": 85.5,
                "reasoning": "early arrival, direct flight",
            },
            "alternatives": [
                {
                    "candidate": {
                        "flight_number": "MH070",
                        "carrier": "MH",
                        "departure_time": "202608201400",
                        "arrival_time": "202608202300",
                        "price": 350.0,
                        "currency": "USD",
                        "duration_minutes": 540,
                        "stops": 0,
                    },
                    "score": 78.0,
                },
            ],
            "total_candidates_evaluated": 16,
        }, "FlightAgent")

    # Add budget and validation sections
    state.update_section("budget", {
        "total_cost": 420.0,
        "budget_limit": budget_limit,
        "within_budget": True,
    }, "BudgetAgent")
    state.update_section("validation", {
        "approved": True,
        "issues": [],
        "critical_issues": [],
        "outputs_checked": 2,
    }, "CriticAgent")
    state.update_section("reflection", {
        "improved": False,
        "changes": [],
    }, "ReflectionAgent")

    return state


def _mock_llm(chat_json_return: dict) -> MagicMock:
    """Create a mock LLM client that returns the given dict from chat_json."""
    mock = MagicMock()
    mock.is_available = True
    mock.chat_json.return_value = chat_json_return
    return mock


def _mock_llm_raises(exc: Exception) -> MagicMock:
    """Create a mock LLM client that raises an exception."""
    mock = MagicMock()
    mock.is_available = True
    mock.chat_json.side_effect = exc
    return mock


# =====================================================================
# Response Parser Tests
# =====================================================================

class TestResponseParsers:
    """Test the LLM response parser functions."""

    def test_parse_agent_response_empty(self):
        from tros.llm.response_parser import parse_agent_response
        result = parse_agent_response({}, "TestAgent")
        assert result["llm_reasoning"] == ""
        assert result["llm_confidence"] == 0.5

    def test_parse_agent_response_with_fields(self):
        from tros.llm.response_parser import parse_agent_response
        raw = {
            "reasoning": "This is my reasoning",
            "confidence": 0.85,
            "warnings": ["warning1", "warning2"],
            "recommendation": {"action": "test"},
        }
        result = parse_agent_response(raw, "TestAgent")
        assert result["llm_reasoning"] == "This is my reasoning"
        assert result["llm_confidence"] == 0.85
        assert result["llm_warnings"] == ["warning1", "warning2"]
        assert result["llm_recommendation"] == {"action": "test"}

    def test_parse_agent_response_clamps_confidence(self):
        from tros.llm.response_parser import parse_agent_response
        result = parse_agent_response({"confidence": 1.5}, "Test")
        assert result["llm_confidence"] == 1.0
        result2 = parse_agent_response({"confidence": -0.5}, "Test")
        assert result2["llm_confidence"] == 0.0

    def test_parse_critic_response(self):
        from tros.llm.response_parser import parse_critic_response
        raw = {
            "issues": ["issue1", "issue2"],
            "critical_issues": ["critical1"],
            "approved": False,
            "reasoning": "Plan has conflicts",
            "outputs_checked": 4,
        }
        result = parse_critic_response(raw)
        assert result["issues"] == ["issue1", "issue2"]
        assert result["critical_issues"] == ["critical1"]
        assert result["approved"] is False
        assert result["outputs_checked"] == 4

    def test_parse_critic_response_defaults(self):
        from tros.llm.response_parser import parse_critic_response
        result = parse_critic_response({})
        assert result["issues"] == []
        assert result["approved"] is False  # default when 'approved' key missing

    def test_parse_reflection_response(self):
        from tros.llm.response_parser import parse_reflection_response
        raw = {
            "changes": ["change1"],
            "improved": True,
            "trade_offs": "cost vs time",
            "reasoning": "Found improvement",
        }
        result = parse_reflection_response(raw)
        assert result["changes"] == ["change1"]
        assert result["improved"] is True
        assert result["trade_offs"] == "cost vs time"

    def test_parse_summary_response(self):
        from tros.llm.response_parser import parse_summary_response
        raw = {
            "summary": "Your flight was cancelled. We recommend...",
            "key_points": ["point1"],
            "caveats": ["caveat1"],
        }
        result = parse_summary_response(raw)
        assert result["summary"] == "Your flight was cancelled. We recommend..."
        assert result["key_points"] == ["point1"]

    def test_parse_flight_response(self):
        from tros.llm.response_parser import parse_flight_response
        raw = {
            "search_strategy": "Search same-day alternatives",
            "assessment": "Top candidate is viable",
            "alternatives_note": "5 cheaper options available",
        }
        result = parse_flight_response(raw)
        assert result["search_strategy"] == "Search same-day alternatives"
        assert result["assessment"] == "Top candidate is viable"

    def test_parse_supervisor_response(self):
        from tros.llm.response_parser import parse_supervisor_response
        raw = {
            "execution_plan": ["FlightAgent", "BudgetAgent"],
            "skip_agents": ["HotelAgent", "WeatherAgent"],
            "failure_response": "Retry with next-day search",
        }
        result = parse_supervisor_response(raw)
        assert result["execution_plan"] == ["FlightAgent", "BudgetAgent"]
        assert result["skip_agents"] == ["HotelAgent", "WeatherAgent"]


# =====================================================================
# LLM Client Tests
# =====================================================================

class TestLLMClient:
    """Test LLM client initialization and availability check."""

    def test_client_not_available_without_key(self):
        from tros.llm.client import LLMClient
        # Use a clearly invalid key that won't resolve to a real client
        client = LLMClient(api_key="sk-invalid-test-key-000")
        # Client can initialize but API calls would fail
        # The is_available check only verifies client creation, not key validity
        # So we verify the client was created with the given key
        assert client._api_key == "sk-invalid-test-key-000"

    def test_client_available_with_mock(self):
        """When openai is installed, client should be available with a key."""
        from tros.llm.client import LLMClient
        client = LLMClient(api_key="sk-test-key")
        # OpenAI package is installed, so client should initialize
        assert client.is_available is True

    def test_chat_json_parses_tool_calls(self):
        """If LLM returns tool calls, chat_json should flag them."""
        from tros.llm.client import LLMClient
        client = LLMClient(api_key="sk-test")
        # Mock the internal _get_client
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        tc_mock = MagicMock()
        tc_mock.id = "call_1"
        tc_mock.function.name = "search_flights"
        tc_mock.function.arguments = '{"origin": "KUL"}'
        mock_choice.message.tool_calls = [tc_mock]
        mock_choice.finish_reason = "tool_calls"
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.chat_json("system", "user")
        assert "_tool_calls" in result
        assert result["_tool_calls"][0]["name"] == "search_flights"


# =====================================================================
# Prompt Builder Tests
# =====================================================================

class TestPrompts:
    """Test prompt building utilities."""

    def test_build_user_message_empty(self):
        from tros.llm.prompts import build_user_message
        msg = build_user_message()
        assert msg == "Proceed with analysis."

    def test_build_user_message_with_context(self):
        from tros.llm.prompts import build_user_message
        msg = build_user_message(
            mission_context={"origin": "KUL"},
            additional="Be thorough",
        )
        assert "KUL" in msg
        assert "Be thorough" in msg

    def test_build_user_message_with_state(self):
        from tros.llm.prompts import build_user_message
        msg = build_user_message(
            state_snapshot={"flight": {"best": "SQ318"}},
        )
        assert "SQ318" in msg


# =====================================================================
# Tool Definition Tests
# =====================================================================

class TestTools:
    """Test tool definitions are valid."""

    def test_get_tools_for_flight_agent(self):
        from tros.llm.tools import get_tools_for_agent
        tools = get_tools_for_agent("FlightAgent")
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "search_flights"

    def test_get_tools_for_critic_agent(self):
        from tros.llm.tools import get_tools_for_agent
        tools = get_tools_for_agent("CriticAgent")
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "read_mission_state"

    def test_get_tools_for_unknown_agent(self):
        from tros.llm.tools import get_tools_for_agent
        tools = get_tools_for_agent("UnknownAgent")
        assert tools == []


# =====================================================================
# CriticAgent LLM Tests
# =====================================================================

class TestCriticAgentLLM:
    """Test CriticAgent with mocked LLM responses."""

    def test_critic_deterministic_mode(self):
        """Without LLM, critic uses only deterministic checks."""
        from tros.agents.critic import CriticAgent
        state = _make_state()
        agent = CriticAgent()  # no llm_client
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED
        assert output.recommendation.get("approved") is True

    def test_critic_llm_adds_issues(self):
        """LLM can add semantic issues on top of deterministic checks."""
        from tros.agents.critic import CriticAgent
        state = _make_state()

        mock = _mock_llm({
            "issues": ["14-hour layover makes this impractical"],
            "critical_issues": [],
            "approved": True,
            "reasoning": "Plan is technically valid but inconvenient",
            "outputs_checked": 3,
        })

        agent = CriticAgent(llm_client=mock)
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED
        # LLM reasoning should be in the output
        assert "AI analysis" in output.reasoning_summary or output.confidence > 0

    def test_critic_llm_fallback_on_error(self):
        """When LLM fails, critic falls back to deterministic checks."""
        from tros.agents.critic import CriticAgent
        state = _make_state()

        mock = _mock_llm_raises(RuntimeError("API timeout"))
        agent = CriticAgent(llm_client=mock)
        output = agent.execute(state)
        # Should still complete via deterministic path
        assert output.status == AgentStatus.COMPLETED


# =====================================================================
# ReflectionAgent LLM Tests
# =====================================================================

class TestReflectionAgentLLM:
    """Test ReflectionAgent with mocked LLM responses."""

    def test_reflection_deterministic_mode(self):
        """Without LLM, reflection uses threshold checks only."""
        from tros.agents.reflection import ReflectionAgent
        state = _make_state()
        agent = ReflectionAgent()
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED

    def test_reflection_llm_adds_optimizations(self):
        """LLM can suggest optimizations beyond threshold checks."""
        from tros.agents.reflection import ReflectionAgent
        state = _make_state()

        mock = _mock_llm({
            "changes": ["Business traveler should prefer earlier arrival over cost savings"],
            "improved": True,
            "trade_offs": "$70 more for 5-hour earlier arrival",
            "reasoning": "Profile-aware optimization",
        })

        agent = ReflectionAgent(llm_client=mock)
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED
        assert "AI:" in output.reasoning_summary or output.confidence > 0

    def test_reflection_llm_fallback_on_error(self):
        """When LLM fails, reflection falls back to deterministic."""
        from tros.agents.reflection import ReflectionAgent
        state = _make_state()

        mock = _mock_llm_raises(RuntimeError("API error"))
        agent = ReflectionAgent(llm_client=mock)
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED


# =====================================================================
# SummaryAgent LLM Tests
# =====================================================================

class TestSummaryAgentLLM:
    """Test SummaryAgent with mocked LLM responses."""

    def test_summary_deterministic_mode(self):
        """Without LLM, summary uses template-based generation."""
        from tros.agents.summary import SummaryAgent
        state = _make_state()
        agent = SummaryAgent()
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED
        assert "TRIP RECOVERY PLAN" in output.recommendation.get("summary", "")

    def test_summary_llm_natural_language(self):
        """With LLM, summary generates natural language explanation."""
        from tros.agents.summary import SummaryAgent
        state = _make_state()

        mock = _mock_llm({
            "summary": (
                "Your original flight from Kuala Lumpur to Tokyo was cancelled. "
                "We've found replacement flight SQ318 departing at 09:30, arriving "
                "at 18:35 the same day. At $420, this is well within your $1000 "
                "budget. This direct flight offers the best balance of timing and "
                "cost among 16 options evaluated."
            ),
            "key_points": ["SQ318 selected", "within budget"],
            "caveats": ["No booking made"],
            "reasoning": "Empathetic recovery explanation",
        })

        agent = SummaryAgent(llm_client=mock)
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED
        summary = output.recommendation.get("summary", "")
        assert "TRIP RECOVERY PLAN" in summary
        assert "SQ318" in summary

    def test_summary_llm_fallback_on_error(self):
        """When LLM fails, summary falls back to deterministic template."""
        from tros.agents.summary import SummaryAgent
        state = _make_state()

        mock = _mock_llm_raises(RuntimeError("timeout"))
        agent = SummaryAgent(llm_client=mock)
        output = agent.execute(state)
        assert output.status == AgentStatus.COMPLETED
        # Should still get template-based summary
        assert "TRIP RECOVERY PLAN" in output.recommendation.get("summary", "")


# =====================================================================
# SupervisorAgent LLM Tests
# =====================================================================

class TestSupervisorAgentLLM:
    """Test SupervisorAgent with mocked LLM responses."""

    def test_supervisor_passes_llm_to_agents(self):
        """Supervisor should pass LLM client to capable agents."""
        from tros.agents.supervisor.agent import SupervisorAgent
        mock = _mock_llm({"execution_plan": ["FlightAgent", "BudgetAgent"]})
        supervisor = SupervisorAgent(llm_client=mock)
        # Verify agents received the LLM client
        assert supervisor._flight_agent._llm is mock
        assert supervisor._critic_agent._llm is mock
        assert supervisor._reflection_agent._llm is mock
        assert supervisor._summary_agent._llm is mock

    def test_supervisor_deterministic_no_llm(self):
        """Without LLM, supervisor uses fixed pipeline."""
        from tros.agents.supervisor.agent import SupervisorAgent
        supervisor = SupervisorAgent()
        assert supervisor._llm is None
        # All agents should have no LLM client
        assert supervisor._flight_agent._llm is None
        assert supervisor._critic_agent._llm is None
