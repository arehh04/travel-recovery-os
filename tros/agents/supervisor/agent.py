"""Supervisor Agent — mission orchestration (Arch §7.1, ADR-006).

The Supervisor NEVER performs domain reasoning.
Its responsibility is orchestration only:
- Receive mission
- Plan execution graph
- Dispatch agents
- Monitor completion
- Trigger Critic → Reflection → Summary

LLM-optional: When an LLMClient is provided, uses LLM reasoning for
dynamic execution graph planning and failure impact assessment.
Without LLM, uses the fixed sequential pipeline.
"""

from __future__ import annotations

import time
from typing import Any

from tros.agents.budget import BudgetAgent
from tros.agents.context import ContextAgent
from tros.agents.critic import CriticAgent
from tros.agents.flight import FlightAgent
from tros.agents.hotel import HotelAgent
from tros.agents.policy import PolicyAgent
from tros.agents.reflection import ReflectionAgent
from tros.agents.summary import SummaryAgent
from tros.agents.transport import TransportAgent
from tros.agents.weather import WeatherAgent
from tros.llm.tool_executor import ToolExecutor
from tros.schemas.agent_output import AgentStatus
from tros.schemas.mission import MissionStatus
from tros.state.mission_state import SharedMissionState
from tros.utils.logging import get_logger


class SupervisorAgent:
    """Central orchestrator for TR-OS recovery missions."""

    NAME = "SupervisorAgent"

    def __init__(self, llm_client: Any | None = None) -> None:
        self.logger = get_logger(self.NAME)
        self._llm = llm_client

        # ToolExecutor for recovery re-search (Phase 6)
        self._tool_executor = ToolExecutor()

        # Instantiate all agents — pass LLM client to LLM-capable agents
        self._context_agent = ContextAgent()
        self._flight_agent = FlightAgent(llm_client=llm_client)
        self._budget_agent = BudgetAgent()
        self._hotel_agent = HotelAgent()
        self._policy_agent = PolicyAgent()
        self._transport_agent = TransportAgent()
        self._weather_agent = WeatherAgent()
        self._critic_agent = CriticAgent(llm_client=llm_client)
        self._reflection_agent = ReflectionAgent(llm_client=llm_client)
        self._summary_agent = SummaryAgent(llm_client=llm_client)

    def run_mission(self, state: SharedMissionState,
                    raw_input: dict[str, Any]) -> SharedMissionState:
        """Execute the full recovery mission pipeline.

        This is the main entry point called by the Mission Engine / demo.
        """
        start = time.time()
        self.logger.info("=== MISSION %s STARTED ===", state.mission_id)

        # ---------------------------------------------------------------
        # Phase 1: Context Collection (sequential)
        # ---------------------------------------------------------------
        self.logger.info("Phase 1: Context Collection")
        state.transition(MissionStatus.PLANNING, self.NAME)

        # Seed raw input for the Context Agent
        state.update_section("flight", {"_raw_input": raw_input}, self.NAME)

        ctx_output = self._context_agent.execute(state)
        state.update_agent_output(ctx_output)

        if ctx_output.status == AgentStatus.FAILED:
            self.logger.error("Context Agent failed — aborting mission")
            state.transition(MissionStatus.FAILED, self.NAME)
            return state

        # ---------------------------------------------------------------
        # Phase 1.5: LLM Execution Planning (optional)
        # ---------------------------------------------------------------
        specialist_agents = self._plan_execution_graph(state, raw_input)

        # ---------------------------------------------------------------
        # Phase 2: Specialist agent execution
        # ---------------------------------------------------------------
        self.logger.info("Phase 2: Specialist Agent Execution")
        state.transition(MissionStatus.RUNNING, self.NAME)

        execution_graph = {
            "sequential": ["ContextAgent"],
            "parallel": [a.NAME for a in specialist_agents],
            "validation": ["CriticAgent"],
            "reflection": ["ReflectionAgent"],
            "summary": ["SummaryAgent"],
        }
        state.execution_graph = execution_graph

        # Execute specialists (in-process; sequential for prototype clarity)
        for agent in specialist_agents:
            self.logger.info("Dispatching %s", agent.NAME)
            try:
                output = agent.execute(state)
                state.update_agent_output(output)

                if output.status == AgentStatus.FAILED:
                    state.failed_agents.append(agent.NAME)
                    self.logger.warning("%s failed — continuing mission", agent.NAME)
                else:
                    self.logger.info("%s completed (confidence=%.2f)",
                                     agent.NAME, output.confidence)
            except Exception as exc:
                self.logger.error("%s threw exception: %s", agent.NAME, exc)
                state.failed_agents.append(agent.NAME)

        # Handle failures with LLM assessment if available
        if state.failed_agents:
            self._handle_failures(state)

        # ---------------------------------------------------------------
        # Phase 2.5: Evidence & Comparison (Phase 5 intelligence)
        # ---------------------------------------------------------------
        self._build_evidence_and_comparison(state)

        # ---------------------------------------------------------------
        # Phase 3: Critic Validation
        # ---------------------------------------------------------------
        self.logger.info("Phase 3: Critic Validation")
        state.transition(MissionStatus.VALIDATION, self.NAME)

        critic_output = self._critic_agent.execute(state)
        state.update_agent_output(critic_output)

        # ---------------------------------------------------------------
        # Phase 4: Reflection
        # ---------------------------------------------------------------
        self.logger.info("Phase 4: Reflection")
        state.transition(MissionStatus.REFLECTION, self.NAME)

        reflection_output = self._reflection_agent.execute(state)
        state.update_agent_output(reflection_output)

        # ---------------------------------------------------------------
        # Phase 4.5: Conflict Detection & Recommendation Validation
        # ---------------------------------------------------------------
        self._run_conflict_detection_and_validation(state)

        # ---------------------------------------------------------------
        # Phase 4.6: Recovery (Phase 6 — bounded recovery if needed)
        # ---------------------------------------------------------------
        mission_decision = state.mission_decision or {}
        if mission_decision.get("status") == "conditional":
            self._run_recovery(state)
            # After recovery, re-build evidence and re-run validation
            if state.recovery_state.get("recovered"):
                self._build_evidence_and_comparison(state)
                self._run_conflict_detection_and_validation(state)

        # ---------------------------------------------------------------
        # Phase 5: Summary
        # ---------------------------------------------------------------
        self.logger.info("Phase 5: Summary Generation")
        state.transition(MissionStatus.RECOMMENDATION, self.NAME)

        summary_output = self._summary_agent.execute(state)
        state.update_agent_output(summary_output)

        # ---------------------------------------------------------------
        # Mission Complete
        # ---------------------------------------------------------------
        state.transition(MissionStatus.COMPLETED, self.NAME)
        elapsed = time.time() - start
        self.logger.info(
            "=== MISSION %s COMPLETED in %.2fs ===",
            state.mission_id, elapsed,
        )

        return state

    # ------------------------------------------------------------------
    # Phase 5: Evidence, Comparison, Conflict, Validation, Confidence
    # ------------------------------------------------------------------

    def _build_evidence_and_comparison(self, state: SharedMissionState) -> None:
        """Build EvidenceBundle and ComparisonReport from flight data.

        Only factual Atlas data enters the evidence store.
        Comparison is fully deterministic.
        """
        from tros.agents.flight.comparator import compare_candidates
        from tros.config import DEFAULT_CURRENCY
        from tros.llm.evidence import build_evidence_bundle

        flight_data = state.flight
        if not flight_data:
            self.logger.info("No flight data — skipping evidence build")
            return

        # Collect candidate dicts from flight section
        best = flight_data.get("best_option", {})
        alternatives = flight_data.get("alternatives", [])

        candidate_dicts: list[dict] = []
        for item in [best] + alternatives:
            c = item.get("candidate", {})
            if c.get("flight_number"):
                candidate_dicts.append({
                    "flight_number": c.get("flight_number", ""),
                    "origin": c.get("departure_airport", ""),
                    "destination": c.get("arrival_airport", ""),
                    "departure_time": c.get("departure_time", ""),
                    "arrival_time": c.get("arrival_time", ""),
                    "duration_minutes": c.get("duration_minutes", 0),
                    "stops": c.get("stops", 0),
                    "price": c.get("price", 0.0),
                    "currency": c.get("currency", DEFAULT_CURRENCY),
                    "deterministic_score": item.get("score", 0.0),
                    "carrier": c.get("carrier", ""),
                    "offer_id": c.get("offer_id", ""),
                })

        search_id = flight_data.get("search_id", "")
        bundle = build_evidence_bundle(candidate_dicts, search_id=search_id)

        # Store evidence in state
        state.update_section("evidence", bundle.model_dump(), self.NAME)

        # Run deterministic comparison
        budget_limit = state.context.budget_limit if state.context else 0.0
        mission_origin = state.context.origin if state.context else ""
        mission_dest = state.context.destination if state.context else ""
        comparison = compare_candidates(
            bundle,
            budget_limit=budget_limit,
            mission_origin=mission_origin,
            mission_destination=mission_dest,
        )
        state.update_section("comparison", comparison.model_dump(), self.NAME)

        # Record Phase 5 trace
        self._record_phase5_trace(state, "evidence_and_comparison", {
            "evidence_count": bundle.total_candidates,
            "comparison_recommended": (
                comparison.recommended.flight_number if comparison.recommended else None
            ),
        })

        self.logger.info(
            "Phase 5: %d candidates in evidence, recommended=%s",
            bundle.total_candidates,
            comparison.recommended.flight_number if comparison.recommended else "none",
        )

    def _run_conflict_detection_and_validation(self, state: SharedMissionState) -> None:
        """Run recommendation validation, conflict detection, confidence calculation.

        All operations are deterministic. No LLM involvement.
        """
        from tros.agents.conflict_detector import detect_conflicts
        from tros.agents.flight.confidence import (
            ConfidenceFactors,
            calculate_confidence,
        )
        from tros.agents.flight.recommendation_validator import validate_recommendation
        from tros.config import DEFAULT_CURRENCY
        from tros.llm.evidence import EvidenceBundle

        flight_data = state.flight
        best = flight_data.get("best_option", {}) if flight_data else {}
        candidate = best.get("candidate", {})
        recommended_flight = candidate.get("flight_number", "")

        # Build evidence from state
        evidence_dict = state.evidence or {}
        evidence = EvidenceBundle(**evidence_dict) if evidence_dict.get("candidates") else EvidenceBundle()

        # --- Recommendation Validation ---
        mission_origin = state.context.origin if state.context else ""
        mission_dest = state.context.destination if state.context else ""
        mission_currency = DEFAULT_CURRENCY

        validation = validate_recommendation(
            selected_flight_number=recommended_flight,
            evidence=evidence,
            mission_origin=mission_origin,
            mission_destination=mission_dest,
            mission_currency=mission_currency,
            expected_score=best.get("score"),
        )

        # --- Budget assessment from state ---
        budget_assessment = state.budget_assessment or {}

        # --- Critic report from state ---
        critic_report = state.critic_report or {}

        # --- Reflection insights ---
        reflection_data = state.reflection or {}
        reflection_insights = reflection_data.get("insights", [])

        # --- Conflict Detection ---
        conflict_report = detect_conflicts(
            flight_recommendation=flight_data,
            budget_assessment=budget_assessment,
            critic_report=critic_report,
            reflection_insights=reflection_insights,
            evidence_validated=validation.valid,
            recommended_flight=recommended_flight,
        )
        state.update_section(
            "conflict_report", conflict_report.model_dump(), self.NAME
        )

        # --- Deterministic Confidence ---
        # Check ranking margin
        comparison_dict = state.comparison or {}
        ranking_margin = False
        alts = comparison_dict.get("alternatives", [])
        if comparison_dict.get("recommended") and alts:
            top_score = comparison_dict["recommended"].get("score", 0)
            second_score = alts[0].get("score", 0) if alts else 0
            ranking_margin = (top_score - second_score) > 5

        factors = ConfidenceFactors(
            evidence_validated=validation.valid,
            budget_validated=budget_assessment.get("within_budget", False),
            constraint_validated=validation.valid,
            critic_approved=critic_report.get("approved", False),
            ranking_margin_bonus=ranking_margin,
            unresolved_conflicts=sum(
                1 for c in conflict_report.conflicts
                if c.resolution_required
            ),
            missing_evidence=evidence.total_candidates == 0,
        )
        confidence_result = calculate_confidence(factors)

        # --- Build MissionDecision ---
        mission_decision = {
            "status": "approved" if (
                validation.valid
                and critic_report.get("approved", False)
                and not conflict_report.has_critical_conflict
            ) else "conditional",
            "recommended_flight": recommended_flight if validation.valid else None,
            "deterministic_score": best.get("score") if validation.valid else None,
            "budget_approved": budget_assessment.get("within_budget", False),
            "critic_approved": critic_report.get("approved", False),
            "conflicts_present": len(conflict_report.conflicts) > 0,
            "confidence": confidence_result.confidence,
            "rationale": self._build_mission_rationale(
                validation, critic_report, conflict_report, confidence_result
            ),
            "validation_result": validation.model_dump(),
            "confidence_breakdown": confidence_result.breakdown,
        }
        state.update_section("mission_decision", mission_decision, self.NAME)

        # Record Phase 5 trace
        self._record_phase5_trace(state, "conflict_and_confidence", {
            "confidence": confidence_result.confidence,
            "conflicts": len(conflict_report.conflicts),
            "evidence_validated": validation.valid,
        })

        self.logger.info(
            "Phase 5: confidence=%.2f, conflicts=%d, validated=%s",
            confidence_result.confidence,
            len(conflict_report.conflicts),
            validation.valid,
        )

    def _build_mission_rationale(
        self,
        validation,
        critic_report: dict,
        conflict_report,
        confidence_result,
    ) -> str:
        """Build a human-readable rationale for the mission decision."""
        parts: list[str] = []
        if validation.valid:
            parts.append("Recommendation validated against Atlas evidence.")
        else:
            parts.append(f"Validation failed: {'; '.join(validation.errors[:2])}")

        if critic_report.get("approved"):
            parts.append("Critic approved.")
        else:
            count = critic_report.get("critical_count", 0)
            parts.append(f"Critic flagged {count} critical issue(s).")

        if conflict_report.conflicts:
            parts.append(
                f"{len(conflict_report.conflicts)} conflict(s) detected."
            )

        parts.append(
            f"Deterministic confidence: {confidence_result.confidence:.0%}."
        )
        return " ".join(parts)

    def _record_phase5_trace(
        self, state: SharedMissionState, action: str, details: dict
    ) -> None:
        """Record Phase 5 trace in llm_metadata without exposing secrets."""
        existing = state.llm_metadata.get("phase5_trace", [])
        existing.append({
            "agent": self.NAME,
            "action": action,
            "details": details,
            "duration_ms": 0,
        })
        state.llm_metadata["phase5_trace"] = existing

    def _record_phase6_trace(
        self, state: SharedMissionState, action: str, details: dict
    ) -> None:
        """Record Phase 6 recovery trace without exposing secrets."""
        existing = state.llm_metadata.get("phase6_trace", [])
        existing.append({
            "agent": self.NAME,
            "action": action,
            "details": details,
            "duration_ms": 0,
        })
        state.llm_metadata["phase6_trace"] = existing

    # ------------------------------------------------------------------
    # Phase 6: Recovery
    # ------------------------------------------------------------------

    def _run_recovery(self, state: SharedMissionState) -> None:
        """Run bounded recovery when the mission decision is conditional.

        Uses the RecoveryEngine which reuses the existing ToolExecutor.
        Never creates a second Atlas execution path.
        """
        from tros.agents.conflict_detector import ConflictReport
        from tros.agents.flight.recommendation_validator import ValidationResult
        from tros.agents.recovery.engine import RecoveryEngine
        from tros.config import DEFAULT_CURRENCY
        from tros.llm.evidence import EvidenceBundle

        self.logger.info("Phase 6: Recovery triggered — decision is conditional")

        # Build inputs from current state
        evidence_dict = state.evidence or {}
        evidence = (
            EvidenceBundle(**evidence_dict)
            if evidence_dict.get("candidates")
            else EvidenceBundle()
        )

        conflict_dict = state.conflict_report or {}
        conflicts = conflict_dict.get("conflicts", [])
        has_critical = conflict_dict.get("has_critical_conflict", False)
        conflict_report = ConflictReport(
            conflicts=conflicts, has_critical_conflict=has_critical,
        )

        validation_dict = (state.mission_decision or {}).get("validation_result", {})
        validation = ValidationResult(
            valid=validation_dict.get("valid", False),
            errors=validation_dict.get("errors", []),
            warnings=validation_dict.get("warnings", []),
            validated_flight=validation_dict.get("validated_flight"),
        )

        budget_assessment = state.budget_assessment or {}

        # Build mission context dict
        ctx = state.context
        mission_context = {
            "origin": ctx.origin if ctx else "",
            "destination": ctx.destination if ctx else "",
            "departure_date": ctx.departure_date if ctx else "",
            "traveler_count": ctx.traveler_count if ctx else 1,
            "currency": DEFAULT_CURRENCY,
            "budget_limit": ctx.budget_limit if ctx else 0,
        }

        engine = RecoveryEngine(tool_executor=self._tool_executor)
        result = engine.run(
            conflict_report=conflict_report,
            validation_result=validation,
            evidence=evidence,
            budget_assessment=budget_assessment,
            mission_context=mission_context,
            flight_data=state.flight,
            state=state,
        )

        # Update mission decision with recovery info
        decision = state.mission_decision or {}
        decision["recovery_required"] = True
        decision["recovery_attempts"] = result.attempts_used
        decision["recovered"] = result.recovered
        decision["initial_decision"] = decision.get("status", "conditional")
        if result.recovered:
            decision["status"] = "approved"
            decision["recommended_flight"] = result.final_candidate
            decision["final_confidence"] = result.final_confidence
            decision["final_validation"] = True
        decision["recovery_reason"] = result.reason
        state.update_section("mission_decision", decision, self.NAME)

        # Record Phase 6 trace
        self._record_phase6_trace(state, "recovery_complete", {
            "recovered": result.recovered,
            "terminated": result.terminated,
            "attempts_used": result.attempts_used,
            "final_candidate": result.final_candidate,
        })

        self.logger.info(
            "Phase 6: Recovery %s — attempts=%d, candidate=%s",
            "succeeded" if result.recovered else "failed",
            result.attempts_used,
            result.final_candidate,
        )

    # ------------------------------------------------------------------
    # Execution graph planning (LLM-optional)
    # ------------------------------------------------------------------

    def _plan_execution_graph(
        self,
        state: SharedMissionState,
        raw_input: dict[str, Any],
    ) -> list[Any]:
        """Decide which specialist agents to activate.

        Without LLM: returns the fixed full list (deterministic default).
        With LLM: asks the LLM to plan the execution graph, then filters.
        """
        all_specialists: dict[str, Any] = {
            "FlightAgent": self._flight_agent,
            "HotelAgent": self._hotel_agent,
            "BudgetAgent": self._budget_agent,
            "PolicyAgent": self._policy_agent,
            "TransportAgent": self._transport_agent,
            "WeatherAgent": self._weather_agent,
        }

        # Default: all specialists in standard order
        default_order = [
            self._flight_agent,
            self._hotel_agent,
            self._budget_agent,
            self._policy_agent,
            self._transport_agent,
            self._weather_agent,
        ]

        if not (self._llm and self._llm.is_available):
            return default_order

        # LLM-assisted execution planning
        try:
            from tros.llm.prompts import SUPERVISOR_SYSTEM_PROMPT, build_user_message
            from tros.llm.response_parser import parse_supervisor_response

            ctx_dict = state.context.model_dump() if state.context else {}
            user_msg = build_user_message(
                mission_context=ctx_dict,
                additional=(
                    f"Disruption type: {raw_input.get('disruption_type', 'unknown')}. "
                    "Plan which specialist agents to activate from: "
                    "FlightAgent, HotelAgent, BudgetAgent, PolicyAgent, TransportAgent, WeatherAgent. "
                    "Activate all domain specialists relevant to solving the disruption."
                ),
            )

            raw_llm = self._llm.chat_json(SUPERVISOR_SYSTEM_PROMPT, user_msg)
            llm_parsed = parse_supervisor_response(raw_llm)

            # Build agent list from LLM execution plan
            skip_agents = set(llm_parsed.get("skip_agents", []))
            execution_plan = llm_parsed.get("execution_plan", [])

            if execution_plan:
                planned_agents = []
                for agent_name in execution_plan:
                    agent_name = agent_name.strip()
                    if agent_name in all_specialists and agent_name not in skip_agents:
                        planned_agents.append(all_specialists[agent_name])

                # If LLM produced a valid plan, use it; otherwise fall back
                if planned_agents:
                    self.logger.info(
                        "LLM execution plan: %s (skipped: %s)",
                        [a.NAME for a in planned_agents],
                        list(skip_agents),
                    )
                    # Store the LLM orchestration reasoning in state
                    state.update_section("llm_metadata", {
                        "execution_plan": [a.NAME for a in planned_agents],
                        "skip_agents": list(skip_agents),
                        "reasoning": llm_parsed.get("llm_reasoning", ""),
                        "failure_response": llm_parsed.get("failure_response", ""),
                    }, self.NAME)
                    return planned_agents

        except Exception as exc:
            self.logger.warning("LLM execution planning failed, using default: %s", exc)

        return default_order

    # ------------------------------------------------------------------
    # Failure handling (LLM-optional)
    # ------------------------------------------------------------------

    def _handle_failures(self, state: SharedMissionState) -> None:
        """Assess agent failures and decide on recovery action.

        Without LLM: logs failures and continues (existing behavior).
        With LLM: asks the LLM to assess impact and suggest recovery.
        """
        if not (self._llm and self._llm.is_available):
            self.logger.info(
                "Failed agents: %s — continuing (deterministic mode)",
                state.failed_agents,
            )
            return

        try:
            from tros.llm.prompts import SUPERVISOR_SYSTEM_PROMPT, build_user_message
            from tros.llm.response_parser import parse_supervisor_response

            agent_outputs = {
                name: {
                    "status": out.status.value,
                    "confidence": out.confidence,
                    "summary": out.reasoning_summary[:100],
                }
                for name, out in state.agent_outputs.items()
            }

            user_msg = build_user_message(
                state_snapshot={
                    "failed_agents": state.failed_agents,
                    "agent_outputs": agent_outputs,
                    "mission_context": state.context.model_dump() if state.context else {},
                },
                additional=(
                    f"The following agents failed: {state.failed_agents}. "
                    "Assess the impact on the mission. Should we retry, "
                    "abort, or continue with partial results?"
                ),
            )

            raw_llm = self._llm.chat_json(SUPERVISOR_SYSTEM_PROMPT, user_msg)
            llm_parsed = parse_supervisor_response(raw_llm)

            failure_response = llm_parsed.get("failure_response", "")
            self.logger.info("LLM failure assessment: %s", failure_response[:100])

            # Store the failure assessment
            existing = dict(state.llm_metadata)
            existing["failures"] = {
                "failed_agents": state.failed_agents,
                "failure_response": failure_response,
                "reasoning": llm_parsed.get("llm_reasoning", ""),
            }
            state.update_section("llm_metadata", existing, self.NAME)

        except Exception as exc:
            self.logger.warning("LLM failure handling failed: %s", exc)
