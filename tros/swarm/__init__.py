"""TR-OS Swarm Module.

Exposes AgentSwarmState, DisruptionEvent, CandidateRoute, and SwarmOrchestrator.
"""

from tros.swarm.orchestrator import SwarmOrchestrator
from tros.swarm.state import (
    AgentSwarmState,
    CandidateRoute,
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

__all__ = [
    "AgentSwarmState",
    "CandidateRoute",
    "DisruptionEvent",
    "SwarmOrchestrator",
    "create_initial_swarm_state",
    "apply_swarm_update",
    "ContextWorker",
    "DirectFlightScout",
    "AlliancePartnerScout",
    "IntermodalScout",
    "CriticRankingWorker",
    "HumanConsensusWorker",
    "ExecutionWorker",
]
