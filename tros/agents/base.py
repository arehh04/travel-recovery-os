"""BaseAgent — ReAct lifecycle contract (Arch Ch.5, ADR-008).

Every tool-enabled agent MUST implement this execution lifecycle:
  Context Loading → Thought → Action → Observation → Evaluation → Commit

No agent may bypass this lifecycle.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.state.mission_state import SharedMissionState
from tros.utils.logging import get_logger


class BaseAgent(ABC):
    """Abstract base class implementing the ReAct execution contract."""

    NAME: str = "BaseAgent"

    def __init__(self) -> None:
        self.logger = get_logger(self.NAME)

    # ------------------------------------------------------------------
    # ReAct six-phase lifecycle (Arch §5.4)
    # ------------------------------------------------------------------

    def execute(self, state: SharedMissionState) -> AgentOutput:
        """Run the full ReAct lifecycle and return structured output."""
        start = time.time()
        self.logger.info("Starting execution for mission %s", state.mission_id)

        try:
            # Phase 1 — Context Loading
            ctx = self.load_context(state)

            # Phase 2 — Thought
            plan = self.think(ctx, state)

            # Phase 3 + 4 — Action + Observation (may loop)
            observation = self.act(plan, state)

            # Phase 5 — Evaluation
            result = self.evaluate(observation, state)

            # Phase 6 — Commit
            output = self.commit(result, state)
            elapsed = time.time() - start
            self.logger.info("Completed in %.2fs (confidence=%.2f)",
                             elapsed, output.confidence)
            return output

        except Exception as exc:
            self.logger.error("Agent %s failed: %s", self.NAME, exc)
            return AgentOutput(
                agent=self.NAME,
                status=AgentStatus.FAILED,
                confidence=0.0,
                reasoning_summary=f"Agent failed: {exc}",
                warnings=[str(exc)],
            )

    # ------------------------------------------------------------------
    # Phase implementations — subclasses override as needed
    # ------------------------------------------------------------------

    def load_context(self, state: SharedMissionState) -> dict[str, Any]:
        """Phase 1: Load mission context and relevant state."""
        ctx: dict[str, Any] = {}
        if state.context:
            ctx["mission_context"] = state.context.model_dump()
        ctx["agent_outputs"] = {
            k: v.model_dump() for k, v in state.agent_outputs.items()
        }
        return ctx

    @abstractmethod
    def think(self, ctx: dict[str, Any],
              state: SharedMissionState) -> dict[str, Any]:
        """Phase 2: Generate an execution plan (Thought)."""
        ...

    @abstractmethod
    def act(self, plan: dict[str, Any],
            state: SharedMissionState) -> dict[str, Any]:
        """Phase 3-4: Execute actions and collect observations."""
        ...

    @abstractmethod
    def evaluate(self, observation: dict[str, Any],
                 state: SharedMissionState) -> dict[str, Any]:
        """Phase 5: Evaluate whether the result satisfies constraints."""
        ...

    @abstractmethod
    def commit(self, result: dict[str, Any],
               state: SharedMissionState) -> AgentOutput:
        """Phase 6: Build and return the standardized AgentOutput."""
        ...
