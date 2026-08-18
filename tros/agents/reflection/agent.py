"""Reflection Agent — optimization pass after Critic validation (Arch §7.10).

Reviews validated recommendations and asks:
- Can arrival time be improved?
- Can cost be reduced?
- Is another option objectively better?
- Can traveler inconvenience be minimized?

LLM-optional: When an LLMClient is provided, uses LLM reasoning for
contextual trade-off analysis on top of deterministic threshold checks.
"""

from __future__ import annotations

from typing import Any

from tros.agents.base import BaseAgent
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.state.mission_state import SharedMissionState


class ReflectionAgent(BaseAgent):
    NAME = "ReflectionAgent"

    def __init__(self, llm_client: Any | None = None) -> None:
        super().__init__()
        self._llm = llm_client

    def think(self, ctx: dict[str, Any],
              state: SharedMissionState) -> dict[str, Any]:
        if self._llm and self._llm.is_available:
            return self._llm_think(ctx, state)
        return self._deterministic_think(ctx, state)

    def act(self, plan: dict[str, Any],
            state: SharedMissionState) -> dict[str, Any]:
        if self._llm and self._llm.is_available:
            return self._llm_act(plan, state)
        return self._deterministic_act(plan, state)

    def evaluate(self, observation: dict[str, Any],
                 state: SharedMissionState) -> dict[str, Any]:
        """Determine if the plan was improved (always deterministic merge)."""
        changes = observation.get("changes", [])
        insights = observation.get("insights", [])
        return {
            **observation,
            "improved": len(changes) > 0,
            "optimization_notes": changes,
            "insights": insights,
        }

    def commit(self, result: dict[str, Any],
               state: SharedMissionState) -> AgentOutput:
        """Publish reflection report."""
        improved = result.get("improved", False)
        changes = result.get("optimization_notes", [])
        llm_reasoning = result.get("llm_reasoning", "")
        insights = result.get("insights", [])

        reflection_data = {
            "improved": improved,
            "changes": changes,
            "original_best": result.get("best", {}).get("candidate", {}).get("flight_number", ""),
            "insights": insights,
        }
        if llm_reasoning:
            reflection_data["llm_analysis"] = llm_reasoning
        state.update_section("reflection", reflection_data, self.NAME)

        confidence = 0.97 if not improved else 0.98

        summary = (
            f"Reflection complete. "
            f"{'Found ' + str(len(changes)) + ' optimization(s).' if improved else 'Current plan is optimal.'}"
        )
        if llm_reasoning:
            summary += f" AI: {llm_reasoning[:100]}"

        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            reasoning_summary=summary,
            recommendation=reflection_data,
            result=reflection_data,
        )

    # ------------------------------------------------------------------
    # Deterministic mode (existing threshold-based logic)
    # ------------------------------------------------------------------

    def _deterministic_think(self, ctx: dict[str, Any],
                             state: SharedMissionState) -> dict[str, Any]:
        self.logger.info("Thinking: evaluating optimization opportunities")
        return {"action": "optimize_plan", "mode": "deterministic"}

    def _deterministic_act(self, plan: dict[str, Any],
                           state: SharedMissionState) -> dict[str, Any]:
        """Analyze the current recommendation for improvements."""
        changes: list[str] = []
        insights: list[dict[str, Any]] = []
        flight_data = state.flight
        alternatives = flight_data.get("alternatives", [])
        best = flight_data.get("best_option", {})

        if not best:
            return {
                "changes": [], "insights": [],
                "best": best, "alternatives": alternatives,
            }

        best_price = best.get("candidate", {}).get("price", 999999)
        best_arrival = best.get("candidate", {}).get("arrival_time", "")
        best_score = best.get("score", 0)
        best_flight = best.get("candidate", {}).get("flight_number", "?")
        best_duration = best.get("candidate", {}).get("duration_minutes", 0)
        best_stops = best.get("candidate", {}).get("stops", 0)

        # Build evidence-based insight for the selected candidate
        insights.append({
            "category": "selected_candidate",
            "priority": "info",
            "observation": (
                f"Recommended: {best_flight}, price=${best_price}, "
                f"score={best_score}, stops={best_stops}, "
                f"duration={best_duration}min"
            ),
            "recommended_action": "Review alternatives for potential improvements",
            "evidence_based": True,
        })

        # Check if an alternative is significantly cheaper
        for alt in alternatives:
            alt_candidate = alt.get("candidate", {})
            alt_price = alt_candidate.get("price", best_price)
            alt_score = alt.get("score", 0)
            alt_flight = alt_candidate.get("flight_number", "?")

            if alt_price < best_price * 0.85 and alt_score >= best_score * 0.90:
                changes.append(
                    f"Consider {alt_flight}: ${alt_price} "
                    f"(save ${best_price - alt_price:.0f}, "
                    f"score {alt_score})")
                insights.append({
                    "category": "cost_optimization",
                    "priority": "medium",
                    "observation": (
                        f"{alt_flight} is ${best_price - alt_price:.0f} cheaper "
                        f"with comparable score ({alt_score} vs {best_score})"
                    ),
                    "recommended_action": f"Consider switching to {alt_flight}",
                    "evidence_based": True,
                    "alternative_flight": alt_flight,
                })

            # Check if alternative has earlier arrival with similar price
            alt_arrival = alt_candidate.get("arrival_time", "")
            if (alt_arrival < best_arrival
                    and abs(alt_price - best_price) < best_price * 0.10
                    and alt_score > best_score * 0.95):
                changes.append(
                    f"Consider {alt_flight}: earlier arrival at "
                    f"{_fmt_time(alt_arrival)} (similar price)")
                insights.append({
                    "category": "arrival_optimization",
                    "priority": "medium",
                    "observation": (
                        f"{alt_flight} arrives earlier at "
                        f"{_fmt_time(alt_arrival)} at similar price"
                    ),
                    "recommended_action": f"Consider switching to {alt_flight}",
                    "evidence_based": True,
                    "alternative_flight": alt_flight,
                })

        # Budget margin insight
        if state.context:
            budget = state.context.budget_limit
            if budget > 0:
                margin = ((budget - best_price) / budget) * 100
                insights.append({
                    "category": "budget_margin",
                    "priority": "low" if margin > 20 else "medium",
                    "observation": (
                        f"Budget margin: {margin:.1f}% "
                        f"(${budget - best_price:.0f} remaining of ${budget:.0f})"
                    ),
                    "recommended_action": (
                        "Sufficient budget margin" if margin > 20
                        else "Tight budget — limited room for upgrades"
                    ),
                    "evidence_based": True,
                })

        return {
            "changes": changes, "insights": insights,
            "best": best, "alternatives": alternatives,
        }

    # ------------------------------------------------------------------
    # LLM mode (contextual trade-off reasoning + deterministic safety net)
    # ------------------------------------------------------------------

    def _llm_think(self, ctx: dict[str, Any],
                   state: SharedMissionState) -> dict[str, Any]:
        """LLM plans optimization focus based on traveler profile."""
        self.logger.info("Thinking (LLM): planning optimization analysis")
        return {"action": "optimize_plan", "mode": "llm"}

    def _llm_act(self, plan: dict[str, Any],
                 state: SharedMissionState) -> dict[str, Any]:
        """Run deterministic checks + LLM contextual optimization."""
        # Always run deterministic threshold checks first
        deterministic_result = self._deterministic_act(plan, state)

        # Add LLM contextual analysis
        try:
            from tros.llm.prompts import REFLECTION_SYSTEM_PROMPT, build_user_message
            from tros.llm.response_parser import parse_reflection_response

            state_snapshot = self._build_state_snapshot(state)
            traveler_info = ""
            if state.context:
                traveler = state.context.traveler
                traveler_info = (
                    f"Traveler type: {traveler.traveler_type}. "
                    f"Preferences: airline={traveler.airline_preference}, "
                    f"seat={traveler.seat_preference}."
                )

            user_msg = build_user_message(
                mission_context=state.context.model_dump() if state.context else None,
                state_snapshot=state_snapshot,
                additional=(
                    f"{traveler_info}\n\n"
                    f"Deterministic analysis found: {deterministic_result['changes'] or 'no optimizations'}.\n"
                    "Consider trade-offs that matter to THIS traveler. "
                    "A business traveler values time over cost. "
                    "A budget traveler values cost over convenience."
                ),
            )

            raw_llm = self._llm.chat_json(REFLECTION_SYSTEM_PROMPT, user_msg)
            llm_parsed = parse_reflection_response(raw_llm)

            # Merge LLM suggestions with deterministic ones
            all_changes = list(deterministic_result["changes"])
            for llm_change in llm_parsed.get("changes", []):
                if llm_change not in all_changes:
                    all_changes.append(llm_change)

            deterministic_result["changes"] = all_changes
            deterministic_result["llm_reasoning"] = llm_parsed.get("llm_reasoning", "")
            deterministic_result["mode"] = "llm"

            self.logger.info("LLM added %d optimization(s): %s",
                             len(llm_parsed.get("changes", [])),
                             llm_parsed.get("llm_reasoning", "")[:80])

        except Exception as exc:
            self.logger.warning("LLM optimization failed, using deterministic only: %s", exc)
            deterministic_result["llm_reasoning"] = f"LLM unavailable: {exc}"

        return deterministic_result

    def _build_state_snapshot(self, state: SharedMissionState) -> dict[str, Any]:
        """Build a serializable snapshot for LLM analysis."""
        snapshot: dict[str, Any] = {}

        flight_data = state.flight
        best = flight_data.get("best_option", {})
        if best:
            c = best.get("candidate", {})
            snapshot["recommended_flight"] = {
                "flight_number": c.get("flight_number"),
                "price": c.get("price"),
                "arrival_time": c.get("arrival_time"),
                "duration_minutes": c.get("duration_minutes"),
                "stops": c.get("stops"),
                "score": best.get("score"),
            }

        alternatives = flight_data.get("alternatives", [])
        snapshot["alternatives"] = [
            {
                "flight_number": a.get("candidate", {}).get("flight_number"),
                "price": a.get("candidate", {}).get("price"),
                "arrival_time": a.get("candidate", {}).get("arrival_time"),
                "score": a.get("score"),
            }
            for a in alternatives[:4]  # Limit to top 4 for token budget
        ]

        if state.budget:
            snapshot["budget"] = dict(state.budget)

        if state.validation:
            snapshot["validation"] = dict(state.validation)

        return snapshot


def _fmt_time(t: str) -> str:
    if len(t) >= 4:
        t = t[-4:]
        return f"{t[:2]}:{t[2:]}"
    return t
