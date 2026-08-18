"""TR-OS LLM reasoning layer.

Provides the LLM client, tool definitions, prompt templates,
response parsing, and tool execution for agentic reasoning
on top of the deterministic execution layer.
"""

from tros.llm.client import LLMClient, LLMError
from tros.llm.react_models import ReActTraceStep, ToolObservation, ReActFinalDecision
from tros.llm.response_parser import parse_agent_response
from tros.llm.tool_executor import ToolExecutor

__all__ = [
    "LLMClient",
    "LLMError",
    "parse_agent_response",
    "ReActTraceStep",
    "ToolObservation",
    "ReActFinalDecision",
    "ToolExecutor",
]
