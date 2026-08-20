"""Phase 4 ReAct FlightAgent tests — mocked LLM and adapter.

All tests use unittest.mock to simulate LLM responses and Atlas adapter
without requiring real API keys or CLI calls. Verifies:

1. ReAct tool-calling loop works correctly
2. Deterministic tool executor validates and executes
3. Constraint violations are rejected
4. Multi-step search is supported
5. Tool-call budget is bounded
6. LLM failure falls back to deterministic
7. Traces are recorded without secrets
8. Ranking remains unchanged
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from tros.llm.react_models import ReActFinalDecision, ReActTraceStep, ToolObservation
from tros.llm.response_parser import (
    parse_react_flight_response,
    parse_tool_call_response,
)
from tros.llm.tool_executor import ToolExecutor
from tros.schemas.agent_output import AgentStatus
from tros.schemas.mission import (
    DisruptionEvent,
    DisruptionType,
    MissionContext,
    TravelerProfile,
)
from tros.state.mission_state import SharedMissionState

# =====================================================================
# Helpers
# =====================================================================

def _make_state(
    mission_id: str = "test-react",
    budget_limit: float = 1000.0,
) -> SharedMissionState:
    """Build a mission state with KUL->NRT flight cancellation context."""
    state = SharedMissionState(mission_id=mission_id)
    state.set_context(MissionContext(
        origin="KUL",
        destination="NRT",
        departure_date="2026-08-20",
        disruption=DisruptionEvent(
            disruption_type=DisruptionType.FLIGHT_CANCELLED,
            origin="KUL", destination="NRT",
            original_flight_number="MH318",
        ),
        budget_limit=budget_limit,
        traveler=TravelerProfile(airline_preference=None),
    ))
    return state


def _make_mission_context_dict(state: SharedMissionState) -> dict:
    """Extract mission context dict for tool executor."""
    if state.context:
        return state.context.model_dump()
    return {}


def _mock_adapter_search(offer_count: int = 3) -> dict:
    """Build a mock Atlas adapter response with N offers."""
    offers = []
    for i in range(offer_count):
        offers.append({
            "offer_id": f"offer-{i}",
            "segments": [{
                "flight_number": f"TR{870 + i}",
                "carrier": "TR",
                "departure_airport": "KUL",
                "arrival_airport": "NRT",
                "departure_time": f"20260820{8 + i:02d}00",
                "arrival_time": f"20260820{16 + i:02d}55",
                "duration_minutes": 535 + i * 10,
                "cabin_class": 1,
                "operating_carrier": "TR",
            }],
            "total_price": 400.0 + i * 50,
            "currency": "USD",
            "passenger_prices": [{
                "base_fare_per_passenger": 350.0 + i * 40,
                "tax_per_passenger": 50.0 + i * 10,
            }],
            "bookable": i < 2,
            "price_status": "current" if i < 2 else "reference",
        })
    return {
        "code": "OK",
        "status": "ok",
        "data": {
            "search_id": "search-123",
            "offer_count": offer_count,
            "offers": offers,
        },
    }


def _make_tool_call_chat_result(
    call_id: str = "call_1",
    name: str = "search_flights",
    arguments: dict | None = None,
) -> dict:
    """Build a mock LLMClient.chat() result with a tool call."""
    return {
        "content": "",
        "tool_calls": [{
            "id": call_id,
            "name": name,
            "arguments": arguments or {
                "origin": "KUL",
                "destination": "NRT",
                "departure_date": "2026-08-20",
                "adults": 1,
                "currency": "USD",
            },
        }],
        "finish_reason": "tool_calls",
    }


def _make_final_chat_result(
    reasoning: str = "Best candidate is within budget.",
    flight_number: str = "TR870",
    confidence: float = 0.90,
) -> dict:
    """Build a mock LLMClient.chat() result with a final decision."""
    final_json = json.dumps({
        "type": "final",
        "thought": reasoning,
        "decision": "recommend",
        "reasoning_summary": reasoning,
        "confidence": confidence,
        "selected_flight_number": flight_number,
    })
    return {
        "content": final_json,
        "tool_calls": [],
        "finish_reason": "stop",
    }


def _make_mock_llm(call_sequence: list[dict]) -> MagicMock:
    """Create a mock LLM that returns different results on successive calls.

    call_sequence: list of dicts, each returned by chat() in order.
    """
    mock = MagicMock()
    mock.is_available = True
    mock.chat = MagicMock(side_effect=call_sequence)
    mock.chat_json = MagicMock()
    return mock


def _make_mock_adapter() -> MagicMock:
    """Create a mock AtlasFlightAdapter that returns test data."""
    adapter = MagicMock()
    adapter.search_flights.return_value = _mock_adapter_search(5)
    return adapter


# =====================================================================
# ToolExecutor Tests
# =====================================================================

class TestToolExecutor:
    """Test the deterministic tool executor."""

    def test_unknown_tool_returns_error(self):
        executor = ToolExecutor()
        obs = executor.execute_tool("unknown_tool", {}, {})
        assert obs.success is False
        assert obs.error_code == "UNKNOWN_TOOL"

    def test_validates_missing_origin(self):
        executor = ToolExecutor(adapter=_make_mock_adapter())
        obs = executor.execute_tool("search_flights", {
            "destination": "NRT", "departure_date": "2026-08-20",
        }, _make_mission_context_dict(_make_state()))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "origin" in obs.message.lower()

    def test_validates_missing_destination(self):
        executor = ToolExecutor(adapter=_make_mock_adapter())
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "departure_date": "2026-08-20",
        }, _make_mission_context_dict(_make_state()))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "destination" in obs.message.lower()

    def test_validates_invalid_date_format(self):
        executor = ToolExecutor(adapter=_make_mock_adapter())
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "20-Aug-2026",
        }, _make_mission_context_dict(_make_state()))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "date" in obs.message.lower() or "YYYY" in obs.message

    def test_validates_origin_constraint(self):
        """LLM tries to search from a different origin."""
        executor = ToolExecutor(adapter=_make_mock_adapter())
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "SIN", "destination": "NRT",
            "departure_date": "2026-08-20",
        }, _make_mission_context_dict(state))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "SIN" in obs.message

    def test_validates_destination_constraint(self):
        """LLM tries to search to a different destination."""
        executor = ToolExecutor(adapter=_make_mock_adapter())
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "HND",
            "departure_date": "2026-08-20",
        }, _make_mission_context_dict(state))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "HND" in obs.message

    def test_validates_date_outside_window(self):
        """LLM tries a date more than 3 days from mission date."""
        executor = ToolExecutor(adapter=_make_mock_adapter())
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-30",  # 10 days away
        }, _make_mission_context_dict(state))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "window" in obs.message.lower() or "days" in obs.message.lower()

    def test_validates_date_within_window(self):
        """Date 2 days from mission date should pass validation."""
        adapter = _make_mock_adapter()
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-22",  # 2 days from Aug 20
        }, _make_mission_context_dict(state))
        assert obs.success is True
        adapter.search_flights.assert_called_once()

    def test_search_flights_success(self):
        """Successful search returns ranked candidates."""
        adapter = _make_mock_adapter()
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-20", "adults": 1,
        }, _make_mission_context_dict(state))
        assert obs.success is True
        assert obs.tool == "search_flights"
        assert obs.candidate_count > 0
        assert len(obs.candidates) > 0
        # Candidates should have deterministic_score
        assert "deterministic_score" in obs.candidates[0]

    def test_adapter_error_returns_observation(self):
        """Atlas adapter failure returns error observation, not exception."""
        from tros.adapters.flight import AtlasAdapterError
        adapter = MagicMock()
        adapter.search_flights.side_effect = AtlasAdapterError("CLI failed")
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-20",
        }, _make_mission_context_dict(state))
        assert obs.success is False
        assert obs.error_code == "ATLAS_ERROR"

    def test_observation_no_secrets(self):
        """Observation must not contain API keys or credentials."""
        adapter = _make_mock_adapter()
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-20",
        }, _make_mission_context_dict(state))
        obs_str = json.dumps(obs.model_dump())
        assert "sk-" not in obs_str
        assert "api_key" not in obs_str.lower()
        assert "password" not in obs_str.lower()


# =====================================================================
# Response Parser Tests
# =====================================================================

class TestReActParsers:
    """Test ReAct-specific response parsers."""

    def test_parse_react_tool_call(self):
        raw = {
            "type": "tool_call",
            "thought": "Need to search flights",
            "tool": "search_flights",
            "arguments": {"origin": "KUL", "destination": "NRT"},
        }
        result = parse_react_flight_response(raw)
        assert result["type"] == "tool_call"
        assert result["tool"] == "search_flights"
        assert result["arguments"]["origin"] == "KUL"

    def test_parse_react_final_decision(self):
        raw = {
            "type": "final",
            "thought": "Evidence is sufficient",
            "decision": "recommend",
            "reasoning_summary": "TR874 is the best option",
            "confidence": 0.92,
            "selected_flight_number": "TR874",
        }
        result = parse_react_flight_response(raw)
        assert result["type"] == "final"
        assert result["decision"] == "recommend"
        assert result["confidence"] == 0.92
        assert result["selected_flight_number"] == "TR874"

    def test_parse_react_final_clamps_confidence(self):
        raw = {"type": "final", "confidence": 1.5}
        result = parse_react_flight_response(raw)
        assert result["confidence"] == 1.0

    def test_parse_react_final_defaults(self):
        result = parse_react_flight_response({})
        assert result["type"] == "final"
        assert result["confidence"] == 0.5

    def test_parse_tool_call_response_with_calls(self):
        result = {
            "tool_calls": [{
                "id": "call_123",
                "name": "search_flights",
                "arguments": {"origin": "KUL"},
            }],
            "content": "",
        }
        tc = parse_tool_call_response(result)
        assert tc is not None
        assert tc["name"] == "search_flights"
        assert tc["call_id"] == "call_123"

    def test_parse_tool_call_response_no_calls(self):
        result = {"tool_calls": [], "content": "some text"}
        tc = parse_tool_call_response(result)
        assert tc is None


# =====================================================================
# FlightAgent ReAct Tests
# =====================================================================

class TestFlightAgentReAct:
    """Test the FlightAgent ReAct loop with mocked LLM and adapter."""

    def test_react_tool_call_executes_search(self):
        """LLM requests tool call -> executor runs Atlas -> observation."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        adapter.search_flights.assert_called_once()

    def test_react_observation_contains_ranked_candidates(self):
        """Observation contains candidates with deterministic scores."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        # Check that the recommendation contains ranked data
        rec = output.recommendation
        assert "best_option" in rec
        assert rec["best_option"]["score"] > 0

    def test_react_final_decision_after_one_search(self):
        """LLM returns final after receiving observation."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(reasoning="TR870 is within budget"),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        assert "TR870" in output.reasoning_summary or output.confidence > 0
        # Should only have called search once
        assert adapter.search_flights.call_count == 1

    def test_react_second_search_when_needed(self):
        """LLM requests two searches sequentially."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(call_id="call_1"),
            _make_tool_call_chat_result(call_id="call_2"),
            _make_final_chat_result(reasoning="Second search confirmed best option"),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        assert adapter.search_flights.call_count == 2

    def test_react_max_tool_calls_enforced(self):
        """LLM keeps requesting tools -> loop stops at max."""
        adapter = _make_mock_adapter()
        # Smart mock: returns tool_calls when tools offered, final when tools=None
        tool_calls_made = [0]

        def mock_chat(system_prompt, user_message, tools=None, tool_results=None):
            if tools is not None and tool_calls_made[0] < 10:
                tool_calls_made[0] += 1
                return _make_tool_call_chat_result(call_id=f"call_{tool_calls_made[0]}")
            # No tools or exhausted: return final decision
            return _make_final_chat_result(reasoning="Forced decision after max calls")

        llm = MagicMock()
        llm.is_available = True
        llm.chat = MagicMock(side_effect=mock_chat)

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        # Adapter should have been called at most LLM_MAX_TOOL_CALLS times (3)
        assert adapter.search_flights.call_count <= 3

    def test_react_constraint_violation_origin_changed(self):
        """LLM tries wrong origin -> rejected, agent continues."""
        adapter = _make_mock_adapter()
        # First: LLM tries wrong origin, then correct origin, then final
        llm = _make_mock_llm([
            _make_tool_call_chat_result(
                call_id="call_1",
                arguments={"origin": "SIN", "destination": "NRT",
                           "departure_date": "2026-08-20", "adults": 1},
            ),
            _make_tool_call_chat_result(
                call_id="call_2",
                arguments={"origin": "KUL", "destination": "NRT",
                           "departure_date": "2026-08-20", "adults": 1},
            ),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        # Should succeed because the LLM recovered with valid args
        assert output.status == AgentStatus.COMPLETED
        # Only one real Atlas call (the valid one)
        assert adapter.search_flights.call_count == 1

    def test_react_llm_failure_falls_back_deterministic(self):
        """LLM raises exception -> deterministic flow runs."""
        adapter = _make_mock_adapter()
        llm = MagicMock()
        llm.is_available = True
        llm.chat.side_effect = RuntimeError("API timeout")

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        # Should fall back to deterministic mode
        assert output.status in (AgentStatus.COMPLETED, AgentStatus.FAILED)
        # Deterministic mode still calls adapter
        adapter.search_flights.assert_called()

    def test_react_no_api_key_uses_deterministic(self):
        """No LLM client -> deterministic FlightAgent works."""
        adapter = _make_mock_adapter()

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=None)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        adapter.search_flights.assert_called_once()

    def test_react_trace_recorded_in_llm_metadata(self):
        """Trace steps stored in state.llm_metadata['react_trace']."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        agent.execute(state)

        react_trace = state.llm_metadata.get("react_trace")
        assert react_trace is not None
        assert isinstance(react_trace, list)
        assert len(react_trace) > 0
        # Each step should have step_number and phase
        for step in react_trace:
            assert "step_number" in step
            assert "phase" in step

    def test_react_trace_no_secrets(self):
        """No API key or credential in any trace step."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        agent.execute(state)

        trace_str = json.dumps(state.llm_metadata.get("react_trace", []))
        assert "sk-" not in trace_str
        assert "api_key" not in trace_str.lower()
        assert "password" not in trace_str.lower()

    def test_react_ranking_unchanged(self):
        """Deterministic scores are identical whether using ReAct or deterministic."""
        adapter = _make_mock_adapter()

        # Deterministic mode
        from tros.agents.flight.agent import FlightAgent
        agent_det = FlightAgent(adapter=adapter, llm_client=None)
        state_det = _make_state(mission_id="det")
        output_det = agent_det.execute(state_det)

        # Reset adapter mock
        adapter2 = _make_mock_adapter()

        # ReAct mode
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])
        agent_react = FlightAgent(adapter=adapter2, llm_client=llm)
        state_react = _make_state(mission_id="react")
        output_react = agent_react.execute(state_react)

        # Both should complete
        assert output_det.status == AgentStatus.COMPLETED
        assert output_react.status == AgentStatus.COMPLETED

        # Best option scores should be comparable (same data, same ranking)
        det_score = output_det.recommendation.get("best_option", {}).get("score", 0)
        react_score = output_react.recommendation.get("best_option", {}).get("score", 0)
        assert abs(det_score - react_score) < 0.01

    def test_react_commit_produces_flight_recommendation(self):
        """Final output is a valid FlightRecommendation."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        rec = output.recommendation
        # Validate FlightRecommendation structure
        assert "best_option" in rec
        assert "alternatives" in rec
        assert "total_candidates_evaluated" in rec
        assert rec["best_option"]["candidate"]["flight_number"] != ""
        assert rec["best_option"]["candidate"]["price"] > 0

    def test_react_invalid_tool_args_rejected(self):
        """Missing required fields in tool args -> CONSTRAINT_VIOLATION."""
        adapter = _make_mock_adapter()
        # LLM calls with empty args, then with valid args, then final
        llm = _make_mock_llm([
            _make_tool_call_chat_result(
                call_id="call_1",
                arguments={"origin": "", "destination": "", "departure_date": ""},
            ),
            _make_tool_call_chat_result(call_id="call_2"),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        # Only one successful Atlas call (the valid one)
        assert adapter.search_flights.call_count == 1


# =====================================================================
# ReAct Models Tests
# =====================================================================

class TestReActModels:
    """Test the ReAct Pydantic models."""

    def test_trace_step_creation(self):
        step = ReActTraceStep(
            step_number=1, phase="THOUGHT",
            thought="Need to search flights",
        )
        assert step.step_number == 1
        assert step.phase == "THOUGHT"
        assert step.success is True

    def test_tool_observation_success(self):
        obs = ToolObservation(
            tool="search_flights", success=True,
            candidate_count=5, candidates=[{"flight_number": "TR870"}],
        )
        assert obs.candidate_count == 5
        assert obs.error_code is None

    def test_tool_observation_error(self):
        obs = ToolObservation(
            tool="search_flights", success=False,
            error_code="CONSTRAINT_VIOLATION",
            message="Origin mismatch",
        )
        assert obs.success is False
        assert obs.candidate_count == 0

    def test_final_decision_model(self):
        fd = ReActFinalDecision(
            decision="recommend",
            confidence=0.85,
            selected_flight_number="TR874",
        )
        assert fd.decision == "recommend"
        assert fd.confidence == 0.85


# =====================================================================
# Phase 4.1 Regression Tests — THOUGHT trace, step numbering, new constraints
# =====================================================================

class TestToolExecutorConstraints41:
    """Phase 4.1: currency and adults count constraint validation."""

    def test_tool_executor_constraint_violation_currency_changed(self):
        """LLM requests EUR but mission currency is USD -> CONSTRAINT_VIOLATION."""
        adapter = _make_mock_adapter()
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-20", "adults": 1,
            "currency": "EUR",
        }, _make_mission_context_dict(state))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "currency" in obs.message.lower() or "EUR" in obs.message
        # Atlas must NOT be called
        adapter.search_flights.assert_not_called()

    def test_tool_executor_accepts_mission_currency(self):
        """LLM requests USD matching mission currency -> search proceeds."""
        adapter = _make_mock_adapter()
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-20", "adults": 1,
            "currency": "USD",
        }, _make_mission_context_dict(state))
        assert obs.success is True
        adapter.search_flights.assert_called_once()

    def test_tool_executor_constraint_violation_adults_count(self):
        """Mission has 1 traveler, LLM requests adults=2 -> CONSTRAINT_VIOLATION."""
        adapter = _make_mock_adapter()
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-20", "adults": 2,
        }, _make_mission_context_dict(state))
        assert obs.success is False
        assert obs.error_code == "CONSTRAINT_VIOLATION"
        assert "traveler" in obs.message.lower() or "adults" in obs.message.lower()
        adapter.search_flights.assert_not_called()

    def test_tool_executor_accepts_matching_adults_count(self):
        """Mission has 1 traveler, LLM requests adults=1 -> search proceeds."""
        adapter = _make_mock_adapter()
        executor = ToolExecutor(adapter=adapter)
        state = _make_state()
        obs = executor.execute_tool("search_flights", {
            "origin": "KUL", "destination": "NRT",
            "departure_date": "2026-08-20", "adults": 1,
        }, _make_mission_context_dict(state))
        assert obs.success is True
        adapter.search_flights.assert_called_once()


class TestReActTrace41:
    """Phase 4.1: THOUGHT trace phase and contiguous step numbering."""

    def test_react_trace_contains_thought_phase(self):
        """ReAct trace must include at least one THOUGHT phase."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        agent.execute(state)

        react_trace = state.llm_metadata.get("react_trace", [])
        phases = [s["phase"] for s in react_trace]
        assert "THOUGHT" in phases

    def test_react_trace_step_numbers_are_contiguous(self):
        """Step numbers must be 1, 2, 3, ... with no gaps or duplicates."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        agent.execute(state)

        steps = state.llm_metadata.get("react_trace", [])
        numbers = [s["step_number"] for s in steps]
        assert numbers == list(range(1, len(numbers) + 1))

    def test_react_trace_order_is_valid(self):
        """THOUGHT must appear before ACTION and before FINAL."""
        adapter = _make_mock_adapter()
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        agent.execute(state)

        steps = state.llm_metadata.get("react_trace", [])
        phases = [s["phase"] for s in steps]
        # Must contain THOUGHT, ACTION, OBSERVATION, FINAL
        assert "THOUGHT" in phases
        assert "ACTION" in phases
        assert "OBSERVATION" in phases
        assert "FINAL" in phases
        # THOUGHT must appear before first ACTION
        first_thought = phases.index("THOUGHT")
        first_action = phases.index("ACTION")
        assert first_thought < first_action
        # THOUGHT must appear before FINAL
        first_final = phases.index("FINAL")
        assert first_thought < first_final

    def test_react_trace_does_not_fabricate_thought(self):
        """When LLM returns empty content with tool call, thought must be empty."""
        adapter = _make_mock_adapter()
        # _make_tool_call_chat_result has content="" -> no thought should be fabricated
        llm = _make_mock_llm([
            _make_tool_call_chat_result(),
            _make_final_chat_result(),
        ])

        from tros.agents.flight.agent import FlightAgent
        agent = FlightAgent(adapter=adapter, llm_client=llm)
        state = _make_state()
        agent.execute(state)

        steps = state.llm_metadata.get("react_trace", [])
        thought_steps = [s for s in steps if s["phase"] == "THOUGHT"]
        # The first THOUGHT (pre-action) should have empty thought
        # since the mock LLM returns empty content with tool calls
        assert len(thought_steps) >= 1
        # Pre-action THOUGHT must be empty (no fabrication)
        assert thought_steps[0]["thought"] == ""
