"""Execution lifecycle — deterministic state machine (Phase 7).

Valid states: PENDING → RUNNING → (RECOVERING → RUNNING) → COMPLETED
                                       ↘ CONDITIONAL → RECOVERING → (COMPLETED | FAILED)
                                       ↘ FAILED
                                       ↘ CANCELLED
                                       ↘ TIMEOUT

Invalid transitions (e.g. COMPLETED → RUNNING) are rejected.
"""

from __future__ import annotations

from enum import Enum


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    CONDITIONAL = "CONDITIONAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


# Valid transitions: from_status → set of allowed next statuses
_VALID_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.FAILED,
    },
    ExecutionStatus.RUNNING: {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.CONDITIONAL,
        ExecutionStatus.RECOVERING,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMEOUT,
    },
    ExecutionStatus.CONDITIONAL: {
        ExecutionStatus.RECOVERING,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.RECOVERING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMEOUT,
    },
    ExecutionStatus.COMPLETED: set(),  # terminal
    ExecutionStatus.FAILED: set(),  # terminal
    ExecutionStatus.CANCELLED: set(),  # terminal
    ExecutionStatus.TIMEOUT: set(),  # terminal
}


def is_valid_transition(from_status: ExecutionStatus, to_status: ExecutionStatus) -> bool:
    """Check if a lifecycle transition is valid."""
    return to_status in _VALID_TRANSITIONS.get(from_status, set())


def validate_transition(from_status: ExecutionStatus, to_status: ExecutionStatus) -> None:
    """Validate and raise on invalid lifecycle transitions."""
    if not is_valid_transition(from_status, to_status):
        raise ValueError(
            f"Invalid lifecycle transition: {from_status.value} → {to_status.value}"
        )
