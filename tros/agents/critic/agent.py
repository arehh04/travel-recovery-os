"""Critic Agent — validates plan consistency (Arch §7.9).

Responsibilities:
- Detect conflicts between agent outputs
- Validate mission completeness
- Verify evidence
- Flag low-confidence outputs

LLM-optional: When an LLMClient is provided, uses LLM reasoning for
semantic cross-validation on top of deterministic safety checks.
Without LLM, falls back to deterministic rule-based validation.
"""

from __future__ import annotations

from typing import Any

from tros.agents.base import BaseAgent
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.state.mission_state import SharedMissionState


class CriticAgent(BaseAgent):
    NAME = "CriticAgent"

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
        """Determine if critical issues exist (always deterministic)."""
        issues = observation.get("issues", [])
        findings = observation.get("findings", [])
        critical = [i for i in issues if "Missing" in i or "exceeds budget" in i]
        # Also count findings with severity=critical
        critical_findings = [f for f in findings if f.get("severity") == "critical"]
        all_critical = critical + [f["message"] for f in critical_findings]
        return {
            **observation,
            "critical_issues": all_critical,
            "approved": len(all_critical) == 0,
        }

    def commit(self, result: dict[str, Any],
               state: SharedMissionState) -> AgentOutput:
        """Publish validation report."""
        approved = result.get("approved", False)
        issues = result.get("issues", [])
        critical = result.get("critical_issues", [])
        llm_reasoning = result.get("llm_reasoning", "")
        findings = result.get("findings", [])

        validation_data = {
            "approved": approved,
            "issues": issues,
            "critical_issues": critical,
            "outputs_checked": result.get("outputs_checked", 0),
        }
        if llm_reasoning:
            validation_data["llm_analysis"] = llm_reasoning
        state.update_section("validation", validation_data, self.NAME)

        # Phase 5: Write structured critic_report
        critic_report = {
            "approved": approved,
            "findings": findings,
            "critical_count": len(critical),
            "warning_count": len(issues) - len(critical),
        }
        state.update_section("critic_report", critic_report, self.NAME)

        status = AgentStatus.COMPLETED if approved else AgentStatus.PARTIAL
        confidence = 0.95 if approved else max(0.3, 0.95 - len(critical) * 0.2)

        # Build reasoning summary
        summary = (
            f"Plan {'approved' if approved else 'has issues'}. "
            f"Checked {result.get('outputs_checked', 0)} agent outputs. "
            f"Issues: {len(issues)}, Critical: {len(critical)}."
        )
        if llm_reasoning:
            summary += f" AI analysis: {llm_reasoning[:120]}"

        return AgentOutput(
            agent=self.NAME,
            status=status,
            confidence=round(confidence, 2),
            reasoning_summary=summary,
            recommendation=validation_data,
            result=validation_data,
            warnings=critical,
        )

    # ------------------------------------------------------------------
    # Deterministic mode (existing logic — always runs as safety net)
    # ------------------------------------------------------------------

    def _deterministic_think(self, ctx: dict[str, Any],
                             state: SharedMissionState) -> dict[str, Any]:
        self.logger.info("Thinking: validating recovery plan consistency")
        return {"action": "validate_plan", "mode": "deterministic"}

    def _deterministic_act(self, plan: dict[str, Any],
                           state: SharedMissionState) -> dict[str, Any]:
        """Collect all agent outputs and check for conflicts."""
        issues: list[str] = []
        findings: list[dict[str, Any]] = []
        outputs = state.agent_outputs

        # A. Flight validity
        flight_output = outputs.get("FlightAgent")
        if not flight_output:
            issues.append("Missing flight recommendation")
            findings.append({
                "severity": "critical",
                "category": "flight_validity",
                "message": "EVIDENCE_MISSING: No flight recommendation found",
                "evidence": None,
            })
        elif flight_output.status != AgentStatus.COMPLETED:
            issues.append(f"Flight agent status: {flight_output.status.value}")
            findings.append({
                "severity": "critical",
                "category": "flight_validity",
                "message": f"Flight agent status: {flight_output.status.value}",
                "evidence": None,
            })

        # B. Mission constraints — check confidence threshold
        for agent_name, output in outputs.items():
            if output.confidence < 0.40:
                issues.append(f"{agent_name} has low confidence ({output.confidence})")
                findings.append({
                    "severity": "warning",
                    "category": "mission_constraints",
                    "message": f"{agent_name} has low confidence ({output.confidence})",
                    "evidence": None,
                })

        # C. Budget compliance
        flight_rec = state.flight
        if flight_rec and state.context:
            best_price = (flight_rec.get("best_option", {})
                          .get("candidate", {}).get("price", 0))
            budget = state.context.budget_limit
            if best_price > budget:
                issues.append(
                    f"Best flight (${best_price}) exceeds budget (${budget})")
                findings.append({
                    "severity": "critical",
                    "category": "budget_compliance",
                    "message": f"Best flight (${best_price}) exceeds budget (${budget})",
                    "evidence": f"price={best_price}, budget={budget}",
                })

        # D-F. Candidate evidence check
        if flight_output and not flight_output.evidence:
            issues.append("Flight recommendation has no evidence")
            findings.append({
                "severity": "critical",
                "category": "candidate_evidence",
                "message": "EVIDENCE_MISSING: Flight recommendation has no evidence",
                "evidence": None,
            })

        # G. Ranking consistency — check flight section
        if flight_rec:
            total = flight_rec.get("total_candidates_evaluated", 0)
            if total == 0 and flight_rec.get("best_option"):
                findings.append({
                    "severity": "warning",
                    "category": "ranking_consistency",
                    "message": "Best option present but total_candidates_evaluated is 0",
                    "evidence": None,
                })

        return {
            "issues": issues,
            "findings": findings,
            "outputs_checked": len(outputs),
        }

    # ------------------------------------------------------------------
    # LLM mode (semantic cross-validation on top of deterministic checks)
    # ------------------------------------------------------------------

    def _llm_think(self, ctx: dict[str, Any],
                   state: SharedMissionState) -> dict[str, Any]:
        """LLM plans what to focus on during validation."""
        self.logger.info("Thinking (LLM): planning validation focus")
        return {"action": "validate_plan", "mode": "llm"}

    def _llm_act(self, plan: dict[str, Any],
                 state: SharedMissionState) -> dict[str, Any]:
        """Run deterministic checks + LLM semantic validation."""
        # Always run deterministic checks first (safety net)
        deterministic_result = self._deterministic_act(plan, state)

        # Add LLM semantic analysis
        try:
            from tros.llm.prompts import CRITIC_SYSTEM_PROMPT, build_user_message
            from tros.llm.response_parser import parse_critic_response

            # Build state snapshot for LLM
            state_snapshot = self._build_state_snapshot(state)
            user_msg = build_user_message(
                mission_context=state.context.model_dump() if state.context else None,
                state_snapshot=state_snapshot,
                additional=(
                    "Review the agent outputs and flight recommendation above. "
                    "Identify any semantic conflicts, timing issues, or practical "
                    "problems that the deterministic checks might miss. "
                    f"Deterministic checks already found: {deterministic_result['issues']}"
                ),
            )

            raw_llm = self._llm.chat_json(CRITIC_SYSTEM_PROMPT, user_msg)
            llm_parsed = parse_critic_response(raw_llm)

            # Merge LLM issues with deterministic ones (deduplicate)
            all_issues = list(deterministic_result["issues"])
            for llm_issue in llm_parsed.get("issues", []):
                if llm_issue not in all_issues:
                    all_issues.append(llm_issue)

            deterministic_result["issues"] = all_issues
            deterministic_result["llm_reasoning"] = llm_parsed.get("llm_reasoning", "")
            deterministic_result["mode"] = "llm"

            self.logger.info("LLM added %d issue(s), reasoning: %s",
                             len(llm_parsed.get("issues", [])),
                             llm_parsed.get("llm_reasoning", "")[:80])

        except Exception as exc:
            self.logger.warning("LLM validation failed, using deterministic only: %s", exc)
            deterministic_result["llm_reasoning"] = f"LLM unavailable: {exc}"

        return deterministic_result

    def _build_state_snapshot(self, state: SharedMissionState) -> dict[str, Any]:
        """Build a serializable snapshot of mission state for the LLM."""
        snapshot: dict[str, Any] = {}

        # Flight recommendation
        if state.flight:
            flight = dict(state.flight)
            # Simplify for token budget
            best = flight.get("best_option", {})
            if best:
                snapshot["flight_recommendation"] = {
                    "flight_number": best.get("candidate", {}).get("flight_number"),
                    "carrier": best.get("candidate", {}).get("carrier"),
                    "price": best.get("candidate", {}).get("price"),
                    "arrival_time": best.get("candidate", {}).get("arrival_time"),
                    "departure_time": best.get("candidate", {}).get("departure_time"),
                    "duration_minutes": best.get("candidate", {}).get("duration_minutes"),
                    "stops": best.get("candidate", {}).get("stops"),
                    "score": best.get("score"),
                }
            snapshot["total_candidates"] = flight.get("total_candidates_evaluated", 0)

        # Budget
        if state.budget:
            snapshot["budget"] = dict(state.budget)

        # Agent outputs summary
        snapshot["agent_outputs"] = {
            name: {
                "status": out.status.value,
                "confidence": out.confidence,
                "summary": out.reasoning_summary[:100],
            }
            for name, out in state.agent_outputs.items()
        }

        return snapshot
