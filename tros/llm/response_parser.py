"""Parse LLM responses into validated Pydantic models.

The LLM always returns JSON. This module validates that JSON
against our AgentOutput schema before any state write occurs.

Safety: LLM output is NEVER written to SharedMissionState without
passing through Pydantic validation.
"""

from __future__ import annotations

from typing import Any

from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.utils.logging import get_logger

logger = get_logger("LLMParser")


def parse_agent_response(
    raw: dict[str, Any],
    agent_name: str,
    default_confidence: float = 0.5,
) -> dict[str, Any]:
    """Parse a raw LLM JSON response into a normalized dict.

    This does NOT create an AgentOutput directly — it returns a dict
    that the agent's commit() method can use alongside deterministic data.

    The returned dict contains:
    - "llm_reasoning": str — the LLM's reasoning summary
    - "llm_recommendation": dict — any structured recommendation
    - "llm_warnings": list — issues flagged by the LLM
    - "llm_confidence": float — LLM's self-assessed confidence
    - "raw_response": dict — the full LLM response for audit
    """
    result: dict[str, Any] = {
        "llm_reasoning": "",
        "llm_recommendation": {},
        "llm_warnings": [],
        "llm_confidence": default_confidence,
        "raw_response": raw,
    }

    if not raw:
        return result

    # Extract common fields
    result["llm_reasoning"] = (
        raw.get("reasoning")
        or raw.get("reasoning_summary")
        or raw.get("assessment", "")
    )

    # Extract confidence (clamp to valid range)
    llm_conf = raw.get("confidence", default_confidence)
    if isinstance(llm_conf, (int, float)):
        result["llm_confidence"] = max(0.0, min(1.0, float(llm_conf)))

    # Extract warnings
    warnings = raw.get("warnings", [])
    if isinstance(warnings, list):
        result["llm_warnings"] = [str(w) for w in warnings]

    # Extract agent-specific recommendation data
    result["llm_recommendation"] = raw.get("recommendation", {})
    if not isinstance(result["llm_recommendation"], dict):
        result["llm_recommendation"] = {"value": result["llm_recommendation"]}

    return result


def parse_critic_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse Critic Agent LLM response into validation data."""
    result = parse_agent_response(raw, "CriticAgent")

    issues = raw.get("issues", [])
    critical = raw.get("critical_issues", [])
    approved = raw.get("approved", False)

    if not isinstance(issues, list):
        issues = []
    if not isinstance(critical, list):
        critical = []
    if not isinstance(approved, bool):
        approved = len(critical) == 0

    result["issues"] = [str(i) for i in issues]
    result["critical_issues"] = [str(c) for c in critical]
    result["approved"] = approved
    result["outputs_checked"] = raw.get("outputs_checked", 0)

    return result


def parse_reflection_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse Reflection Agent LLM response into optimization data."""
    result = parse_agent_response(raw, "ReflectionAgent")

    changes = raw.get("changes", [])
    improved = raw.get("improved", False)

    if not isinstance(changes, list):
        changes = []
    if not isinstance(improved, bool):
        improved = len(changes) > 0

    result["changes"] = [str(c) for c in changes]
    result["improved"] = improved
    result["trade_offs"] = raw.get("trade_offs", "")

    return result


def parse_summary_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse Summary Agent LLM response into summary data."""
    result = parse_agent_response(raw, "SummaryAgent")

    result["summary"] = raw.get("summary", "")
    result["key_points"] = raw.get("key_points", [])
    result["caveats"] = raw.get("caveats", [])

    if not isinstance(result["summary"], str):
        result["summary"] = str(result["summary"])

    return result


def parse_flight_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse Flight Agent LLM response into search strategy data."""
    result = parse_agent_response(raw, "FlightAgent")

    result["search_strategy"] = raw.get("search_strategy", "")
    result["assessment"] = raw.get("assessment", "")
    result["alternatives_note"] = raw.get("alternatives_note", "")

    return result


def parse_supervisor_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse Supervisor Agent LLM response into execution plan data."""
    result = parse_agent_response(raw, "SupervisorAgent")

    execution_plan = raw.get("execution_plan", [])
    skip_agents = raw.get("skip_agents", [])
    failure_response = raw.get("failure_response", "")

    if not isinstance(execution_plan, list):
        execution_plan = []
    if not isinstance(skip_agents, list):
        skip_agents = []

    result["execution_plan"] = [str(a) for a in execution_plan]
    result["skip_agents"] = [str(a) for a in skip_agents]
    result["failure_response"] = str(failure_response)

    return result


# ---------------------------------------------------------------------------
# Phase 4: ReAct Flight Agent response parsers
# ---------------------------------------------------------------------------

def parse_react_flight_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse a FlightAgent ReAct response.

    Handles two shapes:
    - Tool call: LLM requests a tool execution
    - Final decision: LLM provides final recommendation

    Returns a normalized dict with 'type' indicating the response kind.
    """
    resp_type = raw.get("type", "final")

    if resp_type == "tool_call":
        return {
            "type": "tool_call",
            "thought": str(raw.get("thought", "")),
            "tool": str(raw.get("tool", "search_flights")),
            "arguments": raw.get("arguments", {}),
        }

    # Default: final decision
    confidence = raw.get("confidence", 0.5)
    if isinstance(confidence, (int, float)):
        confidence = max(0.0, min(1.0, float(confidence)))
    else:
        confidence = 0.5

    return {
        "type": "final",
        "thought": str(raw.get("thought", "")),
        "decision": str(raw.get("decision", "recommend")),
        "reasoning_summary": str(raw.get("reasoning_summary", "")),
        "confidence": confidence,
        "selected_flight_number": raw.get("selected_flight_number"),
    }


def parse_tool_call_response(result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract tool call details from an LLMClient.chat() result.

    The LLMClient returns tool_calls as a list of dicts with
    'id', 'name', and 'arguments' keys.

    Returns the first tool call dict or None if no tool calls.
    """
    tool_calls = result.get("tool_calls", [])
    if not tool_calls:
        return None

    tc = tool_calls[0]
    return {
        "call_id": tc.get("id", ""),
        "name": tc.get("name", ""),
        "arguments": tc.get("arguments", {}),
    }
