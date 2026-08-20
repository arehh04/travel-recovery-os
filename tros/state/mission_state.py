"""Shared Mission State — Blackboard Architecture (Arch Ch.6, ADR-011).

The blackboard is the single source of truth for every mission.
Agents communicate indirectly by reading and updating this state.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, Field

from tros.schemas.agent_output import AgentOutput
from tros.schemas.mission import AuditEntry, MissionContext, MissionStatus


class SharedMissionState(BaseModel):
    """Central blackboard state for one recovery mission (Arch §6.5)."""

    mission_id: str
    version: int = 1
    status: MissionStatus = MissionStatus.CREATED
    trigger_event: str = ""

    # --- Immutable context (written by Context Agent only) ---
    context: MissionContext | None = None

    # --- Agent-owned sections ---
    flight: dict[str, Any] = Field(default_factory=dict)
    hotel: dict[str, Any] = Field(default_factory=dict)
    transport: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    weather: dict[str, Any] = Field(default_factory=dict)

    # --- Agent outputs (standardized) ---
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)

    # --- Validation & reflection ---
    validation: dict[str, Any] = Field(default_factory=dict)
    reflection: dict[str, Any] = Field(default_factory=dict)
    recommendation: dict[str, Any] = Field(default_factory=dict)

    # --- Confidence ---
    confidence: dict[str, float] = Field(default_factory=dict)

    # --- Audit trail (append-only) ---
    audit: list[AuditEntry] = Field(default_factory=list)

    # --- Runtime metadata ---
    execution_graph: dict[str, Any] = Field(default_factory=dict)
    completed_agents: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)

    # --- LLM metadata (Phase 3: agentic reasoning traces) ---
    llm_metadata: dict[str, Any] = Field(default_factory=dict)

    # --- Phase 5: Multi-agent intelligence sections ---
    evidence: dict[str, Any] = Field(default_factory=dict)
    comparison: dict[str, Any] = Field(default_factory=dict)
    budget_assessment: dict[str, Any] = Field(default_factory=dict)
    critic_report: dict[str, Any] = Field(default_factory=dict)
    conflict_report: dict[str, Any] = Field(default_factory=dict)
    mission_decision: dict[str, Any] = Field(default_factory=dict)
    recovery_plan: dict[str, Any] = Field(default_factory=dict)

    # --- Phase 6: Recovery state ---
    recovery_state: dict[str, Any] = Field(default_factory=dict)
    recovery_history: list[Any] = Field(default_factory=list)
    evidence_versions: list[Any] = Field(default_factory=list)

    def _snapshot(self) -> dict[str, Any]:
        """Return a deep copy of current state for versioning."""
        return copy.deepcopy(self.model_dump())

    def transition(self, new_status: MissionStatus, agent: str = "System") -> None:
        """Transition mission to a new lifecycle status (Arch §6.4)."""
        old = self.status
        self.status = new_status
        self._append_audit(agent, "status_transition",
                          f"{old.value} -> {new_status.value}")

    def update_agent_output(self, output: AgentOutput) -> None:
        """Write an agent's standardized output (Arch §6.7).
        Increments version and appends audit entry."""
        prev_version = self.version
        self.agent_outputs[output.agent] = output
        self.confidence[output.agent] = output.confidence
        self.version += 1
        if output.agent not in self.completed_agents:
            if output.status.value == "completed":
                self.completed_agents.append(output.agent)
        self._append_audit(
            output.agent, "output_committed",
            f"status={output.status.value}, confidence={output.confidence}",
            prev_version,
        )

    def update_section(self, section: str, data: dict[str, Any],
                       agent: str) -> None:
        """Write to an owned state section with ownership check."""
        if not hasattr(self, section):
            raise ValueError(f"Unknown state section: {section}")
        prev_version = self.version
        setattr(self, section, data)
        self.version += 1
        self._append_audit(
            agent, f"section_update:{section}",
            f"Updated {section} data",
            prev_version,
        )

    def set_context(self, ctx: MissionContext, agent: str = "ContextAgent") -> None:
        """Set immutable mission context (Context Agent only)."""
        self.context = ctx
        self.trigger_event = ctx.disruption.disruption_type.value
        self.transition(MissionStatus.CONTEXT_LOADED, agent)

    def _append_audit(self, agent: str, action: str, summary: str,
                      prev_version: int = 0) -> None:
        """Append an immutable audit entry (Arch §6.15, ADR-014)."""
        self.audit.append(AuditEntry(
            agent=agent,
            action=action,
            previous_version=prev_version,
            new_version=self.version,
            summary=summary,
        ))
