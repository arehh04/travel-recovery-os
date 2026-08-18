"""ReAct trace and tool observation models (Phase 4).

Structured Pydantic models for recording the ReAct loop:
- ReActTraceStep captures each thought/action/observation/final step
- ToolObservation captures the result of a deterministic tool execution

These models are stored in SharedMissionState.llm_metadata["react_trace"]
for audit and demo visualization.

Safety: No secrets (API keys, tokens) are ever stored in these models.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ReActTraceStep(BaseModel):
    """A single step in the ReAct reasoning loop.

    Phases:
    - THOUGHT: LLM reasoning about what to do next
    - ACTION: LLM requests a tool call
    - OBSERVATION: Deterministic tool execution result
    - FINAL: LLM produces final decision
    """
    step_number: int
    phase: str  # THOUGHT | ACTION | OBSERVATION | FINAL
    thought: str = ""
    tool_name: Optional[str] = None
    tool_arguments: Optional[dict[str, Any]] = None
    observation: Optional[dict[str, Any]] = None
    duration_ms: int = 0
    success: bool = True


class ToolObservation(BaseModel):
    """Structured result from a deterministic tool execution.

    The LLM receives this as an observation to reason over.
    Contains real Atlas data only — never fabricated candidates.
    """
    tool: str
    success: bool
    search_id: Optional[str] = None
    candidate_count: int = 0
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    error_code: Optional[str] = None
    message: Optional[str] = None


class ReActFinalDecision(BaseModel):
    """The LLM's final decision after the ReAct loop.

    Produced when the LLM determines the evidence is sufficient
    or when the tool-call budget is exhausted.
    """
    thought: str = ""
    decision: str = "recommend"  # recommend | no_viable_option
    reasoning_summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    selected_flight_number: Optional[str] = None
