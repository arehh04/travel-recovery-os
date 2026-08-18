"""Summary Agent — generates user-facing explanation (Arch §7.11).

Transforms structured technical outputs into an understandable
recovery plan for the traveler.

LLM-optional: When an LLMClient is provided, generates natural-language
recovery explanation instead of template-based text.
"""

from __future__ import annotations

from typing import Any

from tros.agents.base import BaseAgent
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.state.mission_state import SharedMissionState


class SummaryAgent(BaseAgent):
    NAME = "SummaryAgent"

    def __init__(self, llm_client: Any | None = None) -> None:
        super().__init__()
        self._llm = llm_client

    def think(self, ctx: dict[str, Any],
              state: SharedMissionState) -> dict[str, Any]:
        self.logger.info("Thinking: generating recovery summary")
        return {"action": "generate_summary"}

    def act(self, plan: dict[str, Any],
            state: SharedMissionState) -> dict[str, Any]:
        """Collect all agent results for the final summary (always deterministic)."""
        flight = state.flight
        validation = state.validation
        reflection = state.reflection
        ctx = state.context

        best = flight.get("best_option", {})
        candidate = best.get("candidate", {})
        alternatives = flight.get("alternatives", [])

        # Phase 5 data
        mission_decision = state.mission_decision or {}
        conflict_report = state.conflict_report or {}
        budget_assessment = state.budget_assessment or {}
        critic_report = state.critic_report or {}

        # Phase 6 data
        recovery_state = state.recovery_state or {}
        recovery_history = state.recovery_history or []
        evidence_versions = state.evidence_versions or []

        return {
            "best_flight": candidate,
            "best_score": best.get("score", 0),
            "best_reasoning": best.get("reasoning", ""),
            "alternatives_count": len(alternatives),
            "alternatives": [
                {
                    "flight_number": a.get("candidate", {}).get("flight_number", ""),
                    "price": a.get("candidate", {}).get("price", 0),
                    "score": a.get("score", 0),
                }
                for a in alternatives[:4]
            ],
            "total_evaluated": flight.get("total_candidates_evaluated", 0),
            "validation_approved": validation.get("approved", False),
            "validation_issues": validation.get("issues", []),
            "reflection_changes": reflection.get("changes", []),
            "origin": ctx.origin if ctx else "",
            "destination": ctx.destination if ctx else "",
            "departure_date": ctx.departure_date if ctx else "",
            "disruption_type": ctx.disruption.disruption_type.value if ctx else "",
            "traveler_type": ctx.traveler.traveler_type if ctx else "standard",
            # Phase 5
            "mission_decision": mission_decision,
            "conflicts": conflict_report.get("conflicts", []),
            "budget_assessment": budget_assessment,
            "critic_report": critic_report,
            "confidence": mission_decision.get("confidence", self._compute_confidence({})),
            # Phase 6
            "recovery_state": recovery_state,
            "recovery_history": recovery_history,
            "evidence_versions": evidence_versions,
        }

    def evaluate(self, observation: dict[str, Any],
                 state: SharedMissionState) -> dict[str, Any]:
        """Ensure all required information is present."""
        has_flight = bool(observation.get("best_flight"))
        return {**observation, "complete": has_flight}

    def commit(self, result: dict[str, Any],
               state: SharedMissionState) -> AgentOutput:
        """Generate the final user-facing recovery recommendation."""
        if self._llm and self._llm.is_available:
            return self._llm_commit(result, state)
        return self._deterministic_commit(result, state)

    # ------------------------------------------------------------------
    # Deterministic mode (template-based — existing logic)
    # ------------------------------------------------------------------

    def _deterministic_commit(self, result: dict[str, Any],
                              state: SharedMissionState) -> AgentOutput:
        """Generate summary using deterministic templates."""
        best = result.get("best_flight", {})
        flight_num = best.get("flight_number", "N/A")
        carrier = best.get("carrier", "N/A")
        dep_time = _fmt_time(best.get("departure_time", ""))
        arr_time = _fmt_time(best.get("arrival_time", ""))
        price = best.get("price", 0)
        currency = best.get("currency", "USD")
        duration = best.get("duration_minutes", 0)
        score = result.get("best_score", 0)
        reasoning = result.get("best_reasoning", "")
        disruption = result.get("disruption_type", "disruption")

        lines = []
        lines.append("TRIP RECOVERY PLAN")
        lines.append(f"{'=' * 50}")
        lines.append("")
        lines.append(f"Disruption: {disruption}")
        lines.append(f"Route: {result.get('origin', '')} -> {result.get('destination', '')}")
        lines.append(f"Date: {result.get('departure_date', '')}")
        lines.append("")
        lines.append("RECOMMENDED FLIGHT")
        lines.append(f"  Flight:    {flight_num} ({carrier})")
        stops = best.get("stops", 0)
        stops_label = "Direct" if stops == 0 else f"{stops} stop(s)"
        lines.append(f"  Route:     {stops_label}")
        lines.append(f"  Departure: {dep_time}")
        lines.append(f"  Arrival:   {arr_time}")
        lines.append(f"  Duration:  {_fmt_duration(duration)}")
        lines.append(f"  Price:     {currency} {price:.2f}")
        lines.append(f"  Score:     {score}/100")
        lines.append("")
        lines.append("WHY THIS FLIGHT?")
        lines.append(f"  {reasoning}")
        lines.append(f"  Evaluated {result.get('total_evaluated', 0)} options.")

        if result.get("alternatives_count", 0) > 0:
            lines.append("")
            lines.append(f"ALTERNATIVES: {result['alternatives_count']} other options available")

        if result.get("validation_approved"):
            lines.append("")
            lines.append("VALIDATION: Plan approved by quality check")
        else:
            issues = result.get("validation_issues", [])
            lines.append("")
            lines.append(f"VALIDATION: Note -- {len(issues)} issue(s) flagged")
            for issue in issues[:3]:
                lines.append(f"  - {issue}")

        changes = result.get("reflection_changes", [])
        if changes:
            lines.append("")
            lines.append("OPTIMIZATION NOTES:")
            for change in changes[:3]:
                lines.append(f"  - {change}")

        lines.append("")
        lines.append(f"{'=' * 50}")
        lines.append(f"Confidence: {self._compute_confidence(result):.0%}")
        lines.append("")
        lines.append("This is a recommendation only.")
        lines.append("No booking has been made. Please review and confirm.")

        summary_text = "\n".join(lines)
        return self._build_output(summary_text, result, state)

    # ------------------------------------------------------------------
    # LLM mode (natural-language generation)
    # ------------------------------------------------------------------

    def _llm_commit(self, result: dict[str, Any],
                    state: SharedMissionState) -> AgentOutput:
        """Generate summary using LLM natural language."""
        try:
            from tros.llm.prompts import SUMMARY_SYSTEM_PROMPT, build_user_message
            from tros.llm.response_parser import parse_summary_response

            best = result.get("best_flight", {})
            state_snapshot = {
                "disruption": result.get("disruption_type"),
                "route": f"{result.get('origin', '')} to {result.get('destination', '')}",
                "date": result.get("departure_date"),
                "recommended_flight": {
                    "flight_number": best.get("flight_number"),
                    "carrier": best.get("carrier"),
                    "departure": _fmt_time(best.get("departure_time", "")),
                    "arrival": _fmt_time(best.get("arrival_time", "")),
                    "duration": _fmt_duration(best.get("duration_minutes", 0)),
                    "price": f"{best.get('currency', 'USD')} {best.get('price', 0):.2f}",
                    "stops": best.get("stops", 0),
                    "score": result.get("best_score"),
                    "reasoning": result.get("best_reasoning"),
                },
                "alternatives_available": result.get("alternatives_count", 0),
                "total_options_evaluated": result.get("total_evaluated", 0),
                "validation": "approved" if result.get("validation_approved") else "issues found",
                "traveler_type": result.get("traveler_type", "standard"),
            }

            if result.get("reflection_changes"):
                state_snapshot["optimization_notes"] = result["reflection_changes"][:3]

            user_msg = build_user_message(
                state_snapshot=state_snapshot,
                additional=(
                    "Generate a clear, empathetic recovery plan for the traveler. "
                    "Explain what happened, why this flight was chosen, and what "
                    "they should do next. Keep it concise but complete."
                ),
            )

            raw_llm = self._llm.chat_json(SUMMARY_SYSTEM_PROMPT, user_msg)
            llm_parsed = parse_summary_response(raw_llm)

            # Use LLM summary if we got meaningful content
            llm_summary = llm_parsed.get("summary", "")
            if llm_summary and len(llm_summary) > 50:
                # Wrap with header/footer
                summary_text = (
                    f"TRIP RECOVERY PLAN\n{'=' * 50}\n\n"
                    f"{llm_summary}\n\n"
                    f"{'=' * 50}\n"
                    f"Confidence: {self._compute_confidence(result):.0%}\n\n"
                    f"This is a recommendation only.\n"
                    f"No booking has been made. Please review and confirm."
                )
                self.logger.info("LLM summary generated (%d chars)", len(llm_summary))
                return self._build_output(summary_text, result, state,
                                           llm_reasoning=llm_parsed.get("llm_reasoning"))

        except Exception as exc:
            self.logger.warning("LLM summary failed, falling back to template: %s", exc)

        # Fallback to deterministic
        return self._deterministic_commit(result, state)

    def _build_output(self, summary_text: str, result: dict[str, Any],
                      state: SharedMissionState,
                      llm_reasoning: str = "") -> AgentOutput:
        """Build the final AgentOutput with the summary text and RecoveryPlan."""
        best = result.get("best_flight", {})
        mission_decision = result.get("mission_decision", {})
        confidence = mission_decision.get(
            "confidence", self._compute_confidence(result)
        )

        recommendation = {
            "summary": summary_text,
            "flight_number": best.get("flight_number", "N/A"),
            "carrier": best.get("carrier", "N/A"),
            "departure": _fmt_time(best.get("departure_time", "")),
            "arrival": _fmt_time(best.get("arrival_time", "")),
            "price": best.get("price", 0),
            "currency": best.get("currency", "USD"),
            "confidence": confidence,
            "alternatives_available": result.get("alternatives_count", 0),
        }
        if llm_reasoning:
            recommendation["llm_analysis"] = llm_reasoning

        state.update_section("recommendation", recommendation, self.NAME)

        # Phase 5: Build structured RecoveryPlan
        recovery_plan = {
            "status": mission_decision.get("status", "completed"),
            "recommended_flight": {
                "flight_number": best.get("flight_number", ""),
                "carrier": best.get("carrier", ""),
                "price": best.get("price", 0),
                "currency": best.get("currency", "USD"),
                "score": result.get("best_score", 0),
            } if best else None,
            "alternatives": result.get("alternatives", []),
            "budget_assessment": result.get("budget_assessment", {}),
            "critic_summary": result.get("critic_report", {}),
            "conflicts": result.get("conflicts", []),
            "confidence": confidence,
            "explanation": summary_text,
            # Phase 6: Recovery information
            "recovery_occurred": result.get("recovery_state", {}).get("recovered", False),
            "recovery_history": result.get("recovery_history", []),
            "evidence_versions": result.get("evidence_versions", []),
            "recovery_attempts": mission_decision.get("recovery_attempts", 0),
            "final_validation": mission_decision.get("final_validation",
                                                     mission_decision.get("validation_result", {}).get("valid", False)),
        }
        state.update_section("recovery_plan", recovery_plan, self.NAME)

        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.COMPLETED,
            confidence=round(confidence, 2),
            reasoning_summary=summary_text,
            recommendation=recommendation,
        )

    def _compute_confidence(self, result: dict[str, Any]) -> float:
        """Deterministic confidence calculation (always used)."""
        base = 0.80
        if result.get("validation_approved"):
            base += 0.10
        if result.get("total_evaluated", 0) > 10:
            base += 0.05
        if result.get("best_score", 0) > 70:
            base += 0.03
        return min(round(base, 2), 0.98)


def _fmt_time(t: str) -> str:
    """Format time to HH:MM, or 'Aug DD HH:MM' for full datetime strings."""
    if len(t) >= 12:
        try:
            month = int(t[4:6])
            day = int(t[6:8])
            hh = t[8:10]
            mm = t[10:12]
            months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return f"{months[month]} {day} {hh}:{mm}"
        except (ValueError, IndexError):
            pass
    if len(t) >= 4:
        t = t[-4:]
        return f"{t[:2]}:{t[2:]}"
    return t


def _fmt_duration(minutes: int) -> str:
    """Format duration in minutes to a human-readable string."""
    if minutes <= 0:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    if hours >= 24:
        days = hours // 24
        rem_hours = hours % 24
        parts = [f"{days}d"]
        if rem_hours:
            parts.append(f"{rem_hours}h")
        if mins:
            parts.append(f"{mins}m")
        return " ".join(parts)
    if hours > 0:
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    return f"{mins}m"
