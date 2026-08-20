"""Recovery models — structured recovery decisions (Phase 6).

The LLM may propose a recovery action, but Python validates whether
that action is allowed. All safety-critical decisions are deterministic.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecoveryActionType(str, Enum):
    """Supported recovery action types."""
    RESEARCH_FLIGHTS = "RESEARCH_FLIGHTS"
    REEVALUATE_CANDIDATES = "REEVALUATE_CANDIDATES"
    USE_NEXT_VALID_CANDIDATE = "USE_NEXT_VALID_CANDIDATE"
    TERMINATE_NO_SOLUTION = "TERMINATE_NO_SOLUTION"


class RecoveryAction(BaseModel):
    """A single recovery decision — proposed by LLM or deterministic logic,
    validated by Python before execution."""
    action_type: RecoveryActionType
    reason: str = ""
    triggering_conflicts: list[str] = Field(default_factory=list)
    target_constraint: str = ""
    search_modifications: dict[str, Any] = Field(default_factory=dict)
    attempt_number: int = 0
    provenance: str = "deterministic"  # deterministic | llm_proposed


class RecoveryResult(BaseModel):
    """Structured result from the recovery process."""
    recovered: bool = False
    terminated: bool = False
    reason: str = ""
    final_validation_valid: bool = False
    attempts_used: int = 0
    final_candidate: str | None = None
    final_confidence: float = 0.0
    actions_taken: list[RecoveryAction] = Field(default_factory=list)


class RecoveryHistoryEntry(BaseModel):
    """One entry in the recovery history — records each recovery attempt."""
    attempt_number: int
    triggering_reason: str = ""
    detected_conflicts: list[str] = Field(default_factory=list)
    action: RecoveryActionType = RecoveryActionType.TERMINATE_NO_SOLUTION
    search_parameters: dict[str, Any] = Field(default_factory=dict)
    result: str = ""  # success | failed | terminated
    candidates_found: int = 0
    validation_valid: bool = False
