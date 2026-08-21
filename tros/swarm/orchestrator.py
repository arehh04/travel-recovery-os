"""TR-OS Swarm Orchestrator.

Coordinates concurrent agent scout execution, operator.add state reduction,
critic evaluation, human-in-the-loop consensus gates, and ticketing execution.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from tros.swarm.state import (
    AgentSwarmState,
    DisruptionEvent,
    apply_swarm_update,
    create_initial_swarm_state,
)
from tros.swarm.workers import (
    AlliancePartnerScout,
    ContextWorker,
    CriticRankingWorker,
    DirectFlightScout,
    ExecutionWorker,
    HumanConsensusWorker,
    IntermodalScout,
)


class SwarmOrchestrator:
    """Orchestrates the multi-agent swarm workflow."""

    def __init__(self) -> None:
        self.context_worker = ContextWorker()
        self.direct_scout = DirectFlightScout()
        self.alliance_scout = AlliancePartnerScout()
        self.intermodal_scout = IntermodalScout()
        self.critic_worker = CriticRankingWorker()
        self.consensus_worker = HumanConsensusWorker()
        self.execution_worker = ExecutionWorker()

    async def execute(
        self,
        disruption: DisruptionEvent,
        passenger_context: dict[str, Any] | None = None,
        auto_execute_if_approved: bool = True,
    ) -> AgentSwarmState:
        """Run the complete agent swarm pipeline synchronously/asynchronously."""
        state = create_initial_swarm_state(disruption, passenger_context)

        # 1. Context Worker
        ctx_update = await self.context_worker.run(state)
        state = apply_swarm_update(state, ctx_update)

        # 2. Parallel Route Scouting Swarm (Fan-out)
        scout_results = await asyncio.gather(
            self.direct_scout.run(state),
            self.alliance_scout.run(state),
            self.intermodal_scout.run(state),
            return_exceptions=False,
        )

        # 3. State Reduction (Fan-in with operator.add)
        for scout_update in scout_results:
            state = apply_swarm_update(state, scout_update)

        # 4. Critic Evaluation & Multi-Criteria Ranking
        critic_update = await self.critic_worker.run(state)
        state = apply_swarm_update(state, critic_update)

        # 5. Human Consensus Gate
        consensus_update = await self.consensus_worker.run(state)
        state = apply_swarm_update(state, consensus_update)

        # 6. Optional Execution if auto-approved
        if auto_execute_if_approved and state.get("human_consensus_status") == "APPROVED":
            exec_update = await self.execution_worker.run(state)
            state = apply_swarm_update(state, exec_update)

        return state

    async def approve_and_execute(self, state: AgentSwarmState) -> AgentSwarmState:
        """Approve a PENDING recovery solution and execute rebooking."""
        solution = state.get("selected_solution")
        flight_no = solution["flight_number"] if solution else "unknown"
        
        approval_update = {
            "human_consensus_status": "APPROVED",
            "agent_logs": [f"[HumanConsensus] Traveler explicitly APPROVED recovery plan on {flight_no}"],
        }
        updated_state = apply_swarm_update(state, approval_update)

        # Execute booking
        exec_update = await self.execution_worker.run(updated_state)
        return apply_swarm_update(updated_state, exec_update)

    async def reject(self, state: AgentSwarmState, reason: str = "Passenger declined") -> AgentSwarmState:
        """Reject the current selected recovery solution."""
        rejection_update = {
            "human_consensus_status": "REJECTED",
            "agent_logs": [f"[HumanConsensus] Traveler REJECTED solution: {reason}"],
        }
        return apply_swarm_update(state, rejection_update)

    async def stream(
        self,
        disruption: DisruptionEvent,
        passenger_context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream step-by-step state progress for real-time UI/SSE rendering."""
        state = create_initial_swarm_state(disruption, passenger_context)
        yield {"step": "INITIALIZED", "state": state}

        # Context
        ctx_update = await self.context_worker.run(state)
        state = apply_swarm_update(state, ctx_update)
        yield {"step": "CONTEXT_ENRICHED", "update": ctx_update, "state": state}

        # Scouts
        scouts = [
            ("DIRECT_SCOUT", self.direct_scout),
            ("ALLIANCE_SCOUT", self.alliance_scout),
            ("INTERMODAL_SCOUT", self.intermodal_scout),
        ]
        for name, scout in scouts:
            res = await scout.run(state)
            state = apply_swarm_update(state, res)
            yield {"step": f"SCOUT_{name}", "update": res, "state": state}

        # Critic
        critic_update = await self.critic_worker.run(state)
        state = apply_swarm_update(state, critic_update)
        yield {"step": "CRITIC_RANKED", "update": critic_update, "state": state}

        # Consensus
        consensus_update = await self.consensus_worker.run(state)
        state = apply_swarm_update(state, consensus_update)
        yield {"step": "CONSENSUS_EVALUATED", "update": consensus_update, "state": state}

        # Execution if approved
        if state.get("human_consensus_status") == "APPROVED":
            exec_update = await self.execution_worker.run(state)
            state = apply_swarm_update(state, exec_update)
            yield {"step": "EXECUTION_CONFIRMED", "update": exec_update, "state": state}
