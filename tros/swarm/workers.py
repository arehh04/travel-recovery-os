"""TR-OS Swarm Workers.

Specialized autonomous workers that operate on the AgentSwarmState.
Scout workers run concurrently and emit partial state updates with candidate routes
and reasoning logs that are combined via operator.add state reduction.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List

from tros.swarm.state import AgentSwarmState, CandidateRoute


class ContextWorker:
    """Extracts and enriches passenger context and constraints from disruption info."""

    NAME = "ContextWorker"

    async def run(self, state: AgentSwarmState) -> Dict[str, Any]:
        disruption = state["disruption"]
        pnr = disruption.get("pnr", "UNKNOWN")
        passengers = disruption.get("affected_passengers", ["Passenger 1"])
        
        # Synthesize / enrich passenger profile from PNR
        tier = "Gold" if "VIP" in pnr or pnr.startswith("G") else "Standard"
        passenger_ctx = {
            "pnr": pnr,
            "traveler_count": len(passengers),
            "passengers": passengers,
            "loyalty_tier": tier,
            "max_acceptable_delay_hours": 12,
            "requires_wheelchair": False,
            "cabin_preference": "Economy",
            "preferred_carrier": disruption.get("original_flight", "BA")[:2],
        }

        log = f"[{self.NAME}] Enriched context for {len(passengers)} traveler(s) (PNR: {pnr}, Loyalty: {tier})"
        return {
            "passenger_context": passenger_ctx,
            "agent_logs": [log],
        }


class DirectFlightScout:
    """Scouts for same-carrier and direct non-stop replacement flights."""

    NAME = "DirectFlightScout"

    async def run(self, state: AgentSwarmState) -> Dict[str, Any]:
        disruption = state["disruption"]
        carrier = disruption.get("original_flight", "BA100")[:2]
        now = datetime.datetime.now(datetime.timezone.utc)

        # Generate direct candidate flights
        dep_1 = (now + datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        arr_1 = (now + datetime.timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%SZ")
        dep_2 = (now + datetime.timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        arr_2 = (now + datetime.timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ")

        candidates: List[CandidateRoute] = [
            {
                "flight_number": f"{carrier}112",
                "departure_time": dep_1,
                "arrival_time": arr_1,
                "price_differential": 0.0,
                "score": 0.92,
                "carrier": carrier,
            },
            {
                "flight_number": f"{carrier}118",
                "departure_time": dep_2,
                "arrival_time": arr_2,
                "price_differential": 45.0,
                "score": 0.85,
                "carrier": carrier,
            },
        ]

        log = f"[{self.NAME}] Discovered {len(candidates)} direct flights on {carrier}"
        return {
            "inventory_candidates": candidates,
            "agent_logs": [log],
        }


class AlliancePartnerScout:
    """Scouts for alliance codeshares & partner airline inventory."""

    NAME = "AlliancePartnerScout"

    async def run(self, state: AgentSwarmState) -> Dict[str, Any]:
        disruption = state["disruption"]
        original = disruption.get("original_flight", "BA100")
        carrier = original[:2]

        # Determine partner alliance
        partner_carrier = "AA" if carrier == "BA" else ("DL" if carrier == "AF" else "UA")
        now = datetime.datetime.now(datetime.timezone.utc)

        dep_time = (now + datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        arr_time = (now + datetime.timedelta(hours=10, minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

        candidates: List[CandidateRoute] = [
            {
                "flight_number": f"{partner_carrier}890",
                "departure_time": dep_time,
                "arrival_time": arr_time,
                "price_differential": 65.0,
                "score": 0.81,
                "carrier": partner_carrier,
            }
        ]

        log = f"[{self.NAME}] Discovered {len(candidates)} partner codeshare option(s) on {partner_carrier}"
        return {
            "inventory_candidates": candidates,
            "agent_logs": [log],
        }


class IntermodalScout:
    """Scouts for alternative nearby hubs and intermodal rail-air routes."""

    NAME = "IntermodalScout"

    async def run(self, state: AgentSwarmState) -> Dict[str, Any]:
        now = datetime.datetime.now(datetime.timezone.utc)
        dep_time = (now + datetime.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        arr_time = (now + datetime.timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")

        candidates: List[CandidateRoute] = [
            {
                "flight_number": "TRAIN-AIR-704",
                "departure_time": dep_time,
                "arrival_time": arr_time,
                "price_differential": -30.0,  # cheaper
                "score": 0.76,
                "carrier": "Eurostar/LH",
            }
        ]

        log = f"[{self.NAME}] Discovered {len(candidates)} intermodal co-terminal option(s)"
        return {
            "inventory_candidates": candidates,
            "agent_logs": [log],
        }


class CriticRankingWorker:
    """Ranks all inventory candidate routes and selects the optimal solution."""

    NAME = "CriticRankingWorker"

    async def run(self, state: AgentSwarmState) -> Dict[str, Any]:
        candidates = state.get("inventory_candidates", [])
        if not candidates:
            log = f"[{self.NAME}] No candidate routes available to evaluate."
            return {
                "selected_solution": None,
                "agent_logs": [log],
            }

        passenger_ctx = state.get("passenger_context", {})
        preferred_carrier = passenger_ctx.get("preferred_carrier", "")

        scored_candidates: List[CandidateRoute] = []
        for cand in candidates:
            c = dict(cand)
            # Recompute weighted multi-criteria score
            # Base score + penalty for price diff + bonus for preferred carrier
            base_score = float(c.get("score", 0.7))
            price_diff = float(c.get("price_differential", 0.0))
            price_penalty = min(0.3, max(0.0, price_diff / 500.0))
            carrier_bonus = 0.08 if c.get("carrier") == preferred_carrier else 0.0

            composite_score = round(max(0.1, min(1.0, base_score - price_penalty + carrier_bonus)), 3)
            c["score"] = composite_score
            scored_candidates.append(c)  # type: ignore[arg-type]

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        best = scored_candidates[0]

        log = (
            f"[{self.NAME}] Evaluated {len(candidates)} candidate(s). "
            f"Selected top route {best['flight_number']} ({best['carrier']}) with score {best['score']} "
            f"(Price Diff: ${best['price_differential']:.2f})"
        )

        return {
            "selected_solution": best,
            "agent_logs": [log],
        }


class HumanConsensusWorker:
    """Evaluates whether the selected solution can be auto-approved or requires human sign-off."""

    NAME = "HumanConsensusWorker"

    async def run(self, state: AgentSwarmState) -> Dict[str, Any]:
        best = state.get("selected_solution")
        if not best:
            log = f"[{self.NAME}] No solution selected. Setting consensus to REJECTED."
            return {
                "human_consensus_status": "REJECTED",
                "agent_logs": [log],
            }

        price_diff = best.get("price_differential", 0.0)
        # Policy: Auto-approve if price differential <= $0 (no additional cost)
        # Otherwise, require human traveler consensus
        if price_diff <= 0:
            consensus = "APPROVED"
            log = f"[{self.NAME}] Solution {best['flight_number']} has zero/negative cost differential. Auto-APPROVED."
        else:
            consensus = "PENDING"
            log = f"[{self.NAME}] Solution {best['flight_number']} incurs +${price_diff:.2f}. Status: PENDING traveler consensus."

        return {
            "human_consensus_status": consensus,
            "agent_logs": [log],
        }


class ExecutionWorker:
    """Issues confirmed booking and generates execution receipt upon approval."""

    NAME = "ExecutionWorker"

    async def run(self, state: AgentSwarmState) -> Dict[str, Any]:
        consensus = state.get("human_consensus_status")
        if consensus != "APPROVED":
            log = f"[{self.NAME}] Consensus status is {consensus}. Execution blocked."
            return {
                "execution_receipt": None,
                "agent_logs": [log],
            }

        solution = state.get("selected_solution")
        if not solution:
            log = f"[{self.NAME}] Missing selected solution. Cannot book."
            return {
                "execution_receipt": None,
                "agent_logs": [log],
            }

        pnr = state.get("disruption", {}).get("pnr", "UNKNOWN")
        receipt_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        e_ticket = f"ETK-{uuid.uuid4().hex[:10].upper()}"

        receipt = {
            "receipt_id": receipt_id,
            "pnr": pnr,
            "rebooked_flight": solution["flight_number"],
            "carrier": solution["carrier"],
            "departure_time": solution["departure_time"],
            "arrival_time": solution["arrival_time"],
            "e_ticket_number": e_ticket,
            "status": "CONFIRMED",
            "booked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "cost_incurred": max(0.0, solution["price_differential"]),
        }

        log = f"[{self.NAME}] Successfully rebooked onto {solution['flight_number']}! E-ticket: {e_ticket} (Receipt: {receipt_id})"
        return {
            "execution_receipt": receipt,
            "agent_logs": [log],
        }
