"""Flight Agent — True ReAct tool-calling workflow (Phase 4, Arch §7.3).

Responsibilities:
- Search alternative flights via Atlas adapter
- Filter invalid routes
- Rank candidates using composite scoring
- Publish flight recommendations

Two execution modes:
- LLM mode: True ReAct loop with search_flights tool calling
  (Thought -> Action -> Observation -> Thought -> Final)
- Deterministic mode: existing think -> act -> evaluate -> commit lifecycle

The ReAct loop is bounded by TR_OS_LLM_MAX_TOOL_CALLS (default 3).
Ranking algorithm and Atlas adapter remain deterministic in both modes.
"""

from __future__ import annotations

import json
import time
from typing import Any

from tros.adapters.flight import AtlasFlightAdapter, AtlasAdapterError, normalize_search_response
from tros.agents.base import BaseAgent
from tros.agents.flight.ranking import rank_candidates
from tros.config import LLM_MAX_TOOL_CALLS
from tros.llm.react_models import ReActFinalDecision, ReActTraceStep, ToolObservation
from tros.llm.tool_executor import ToolExecutor
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.schemas.flight import FlightRecommendation
from tros.state.mission_state import SharedMissionState


class FlightAgent(BaseAgent):
    NAME = "FlightAgent"

    def __init__(
        self,
        adapter: AtlasFlightAdapter | None = None,
        llm_client: Any | None = None,
    ) -> None:
        super().__init__()
        self._adapter = adapter or AtlasFlightAdapter()
        self._llm = llm_client
        self._tool_executor = ToolExecutor(adapter=self._adapter)

    # ------------------------------------------------------------------
    # Execution entry point — routes to ReAct or deterministic lifecycle
    # ------------------------------------------------------------------

    def execute(self, state: SharedMissionState) -> AgentOutput:
        """Run the agent. LLM mode uses ReAct loop; otherwise deterministic."""
        if self._llm and self._llm.is_available:
            return self._react_execute(state)
        return super().execute(state)

    # ------------------------------------------------------------------
    # ReAct lifecycle (LLM mode)
    # ------------------------------------------------------------------

    def _react_execute(self, state: SharedMissionState) -> AgentOutput:
        """Full ReAct execution: loop + commit."""
        start = time.time()
        self.logger.info("Starting ReAct execution for mission %s", state.mission_id)

        try:
            # Phase 1 — Context Loading
            ctx = self.load_context(state)

            # Run the bounded ReAct loop
            result = self._react_loop(ctx, state)

            # Phase 6 — Commit
            output = self.commit(result, state)
            elapsed = time.time() - start
            self.logger.info("ReAct completed in %.2fs (confidence=%.2f)",
                             elapsed, output.confidence)
            return output

        except Exception as exc:
            self.logger.error("ReAct FlightAgent failed: %s, falling back to deterministic", exc)
            # Fallback to deterministic mode
            return super().execute(state)

    def _react_loop(
        self,
        ctx: dict[str, Any],
        state: SharedMissionState,
    ) -> dict[str, Any]:
        """Bounded ReAct loop: Thought -> Action -> Observation -> Final.

        Returns a result dict compatible with commit():
        - "ranked": list of RankedFlight
        - "total_evaluated": int
        - "error": str or None
        - "llm_reasoning": str
        - "react_trace": list of ReActTraceStep dicts
        """
        from tros.llm.prompts import FLIGHT_SYSTEM_PROMPT, build_user_message
        from tros.llm.response_parser import (
            parse_react_flight_response,
            parse_tool_call_response,
        )
        from tros.llm.tools import get_tools_for_agent

        tools = get_tools_for_agent("FlightAgent")
        mission_ctx = ctx.get("mission_context", {})
        trace: list[ReActTraceStep] = []
        step_num = 0
        tool_calls_used = 0

        # Accumulated ranked candidates from all searches
        all_ranked: list = []
        total_evaluated = 0

        # Build initial user message with mission context
        user_msg = build_user_message(
            mission_context=mission_ctx,
            additional=(
                f"Search for replacement flights from "
                f"{mission_ctx.get('origin', '')} to "
                f"{mission_ctx.get('destination', '')} on "
                f"{mission_ctx.get('departure_date', '')}. "
                f"Budget limit: ${mission_ctx.get('budget_limit', 1000.0)}. "
                f"Use the search_flights tool to find live alternatives."
            ),
        )

        # Conversation history for tool_results parameter
        tool_results: list[dict[str, Any]] = []
        final_decision: dict[str, Any] | None = None

        for iteration in range(LLM_MAX_TOOL_CALLS + 1):
            step_start = time.time()

            # Determine whether tools should be offered
            use_tools = tools if tool_calls_used < LLM_MAX_TOOL_CALLS else None

            # Call LLM
            try:
                llm_result = self._llm.chat(
                    system_prompt=FLIGHT_SYSTEM_PROMPT,
                    user_message=user_msg,
                    tools=use_tools,
                    tool_results=tool_results if tool_results else None,
                )
            except Exception as exc:
                self.logger.warning("LLM call failed at iteration %d: %s", iteration, exc)
                # If we have candidates from prior searches, use them
                if all_ranked:
                    break
                # Otherwise fall back
                raise

            step_num += 1
            step_ms = int((time.time() - step_start) * 1000)

            # Extract explicit content from LLM response for THOUGHT recording.
            # Only record reasoning explicitly returned by the model — never fabricate.
            llm_content = llm_result.get("content", "")

            # Check for tool calls
            tc = parse_tool_call_response(llm_result)
            if tc:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                call_id = tc["call_id"]

                # Record THOUGHT — LLM's explicit reasoning before requesting tool
                trace.append(ReActTraceStep(
                    step_number=step_num,
                    phase="THOUGHT",
                    thought=llm_content if llm_content else "",
                    duration_ms=step_ms,
                ))

                # Record ACTION
                step_num += 1
                trace.append(ReActTraceStep(
                    step_number=step_num,
                    phase="ACTION",
                    thought="",
                    tool_name=tool_name,
                    tool_arguments=tool_args,
                    duration_ms=0,
                ))

                # Execute tool deterministically
                tool_start = time.time()
                observation = self._tool_executor.execute_tool(
                    tool_name, tool_args, mission_ctx,
                )
                tool_ms = int((time.time() - tool_start) * 1000)

                # Record OBSERVATION
                step_num += 1
                obs_dict = observation.model_dump()
                trace.append(ReActTraceStep(
                    step_number=step_num,
                    phase="OBSERVATION",
                    tool_name=tool_name,
                    observation=obs_dict,
                    duration_ms=tool_ms,
                    success=observation.success,
                ))

                # Accumulate ranked candidates from successful search
                if observation.success and observation.candidates:
                    total_evaluated += observation.candidate_count
                    for c_dict in observation.candidates:
                        all_ranked.append(c_dict)

                # Build tool_results entry for next LLM call
                tool_results.append({
                    "call_id": call_id,
                    "name": tool_name,
                    "arguments": tool_args,
                    "result": obs_dict,
                })

                tool_calls_used += 1
                continue

            # No tool calls — LLM returned content (final decision)
            content = llm_result.get("content", "")
            if content:
                try:
                    raw_final = json.loads(content)
                except json.JSONDecodeError:
                    raw_final = {"type": "final", "reasoning_summary": content}

                final_decision = parse_react_flight_response(raw_final)

                # Record THOUGHT — LLM's explicit reasoning before final decision
                thought_text = final_decision.get("thought", "")
                trace.append(ReActTraceStep(
                    step_number=step_num,
                    phase="THOUGHT",
                    thought=thought_text,
                    duration_ms=step_ms,
                ))

                # Record FINAL — step_num already accounts for this iteration
                step_num += 1
                trace.append(ReActTraceStep(
                    step_number=step_num,
                    phase="FINAL",
                    thought=final_decision.get("thought", ""),
                    observation={
                        "decision": final_decision.get("decision", ""),
                        "confidence": final_decision.get("confidence", 0.5),
                    },
                    duration_ms=0,
                ))
                break

            # No tool calls and no content — unusual, break
            self.logger.warning("LLM returned neither tool calls nor content at iteration %d", iteration)
            break

        # If no final decision was reached (max tool calls exhausted), force one
        if final_decision is None and all_ranked:
            step_num += 1
            final_decision = self._force_final_decision(
                FLIGHT_SYSTEM_PROMPT, user_msg, tool_results,
                all_ranked, total_evaluated, trace, step_num,
            )
        elif final_decision is None:
            # No candidates at all
            final_decision = {
                "type": "final",
                "thought": "No viable flight options found.",
                "decision": "no_viable_option",
                "reasoning_summary": "No flight candidates were available.",
                "confidence": 0.0,
                "selected_flight_number": None,
            }

        # Build the result dict for commit()
        # Convert dict-based candidates to RankedFlight objects if needed
        ranked_objects = self._ensure_ranked_objects(all_ranked, state)

        result = {
            "ranked": ranked_objects,
            "error": None if ranked_objects else "No flight candidates found",
            "total_evaluated": total_evaluated or len(ranked_objects),
            "llm_reasoning": final_decision.get("reasoning_summary", ""),
        }

        # Store ReAct trace in state
        state.llm_metadata["react_trace"] = [s.model_dump() for s in trace]
        state.llm_metadata["react_final"] = final_decision
        state.llm_metadata["react_tool_calls"] = tool_calls_used

        return result

    # ------------------------------------------------------------------
    # Deterministic lifecycle (fallback — Phase 3 compatible)
    # ------------------------------------------------------------------

    def think(self, ctx: dict[str, Any],
              state: SharedMissionState) -> dict[str, Any]:
        """Plan the flight search parameters from mission context."""
        return self._deterministic_think(ctx, state)

    def act(self, plan: dict[str, Any],
            state: SharedMissionState) -> dict[str, Any]:
        """Execute Atlas flight search and normalize results."""
        try:
            raw_response = self._adapter.search_flights(
                origin=plan["origin"],
                destination=plan["destination"],
                departure_date=plan["departure_date"],
                adults=1,
            )
            candidates = normalize_search_response(raw_response)
            offer_count = raw_response.get("data", {}).get("offer_count", len(candidates))
            search_id = raw_response.get("data", {}).get("search_id", "")

            return {
                "candidates": candidates,
                "offer_count": offer_count,
                "search_id": search_id,
                "error": None,
            }
        except AtlasAdapterError as exc:
            self.logger.error("Atlas search failed: %s", exc)
            return {"candidates": [], "offer_count": 0,
                    "search_id": "", "error": str(exc)}

    def evaluate(self, observation: dict[str, Any],
                 state: SharedMissionState) -> dict[str, Any]:
        """Evaluate search results: filter, rank, select best."""
        return self._deterministic_evaluate(observation, state)

    # ------------------------------------------------------------------
    # commit() — shared by both modes
    # ------------------------------------------------------------------

    def commit(self, result: dict[str, Any],
               state: SharedMissionState) -> AgentOutput:
        """Publish flight recommendation to blackboard."""
        ranked = result.get("ranked", [])
        error = result.get("error")
        llm_reasoning = result.get("llm_reasoning", "")

        if not ranked:
            return AgentOutput(
                agent=self.NAME,
                status=AgentStatus.FAILED,
                confidence=0.0,
                reasoning_summary=f"Flight search failed: {error}",
                warnings=[error or "No candidates"],
            )

        best = ranked[0]
        alternatives = ranked[1:5]  # Top 5 alternatives

        recommendation = FlightRecommendation(
            best_option=best,
            alternatives=alternatives,
            total_candidates_evaluated=result["total_evaluated"],
            search_origin=state.context.origin if state.context else "",
            search_destination=state.context.destination if state.context else "",
            search_date=state.context.departure_date if state.context else "",
        )

        # Write to blackboard
        state.update_section("flight", recommendation.model_dump(), self.NAME)

        # Compute confidence based on data quality
        confidence = min(0.95, 0.70 + (len(ranked) * 0.01))

        # Build reasoning summary — enriched with LLM if available
        base_summary = (
            f"Selected {best.candidate.flight_number} "
            f"({best.candidate.carrier}) departing "
            f"{_fmt_time(best.candidate.departure_time)} — "
            f"${best.candidate.price} — score {best.score}. "
            f"{best.reasoning}. "
            f"Evaluated {result['total_evaluated']} candidates."
        )
        if llm_reasoning:
            base_summary += f" AI assessment: {llm_reasoning[:120]}"

        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.COMPLETED,
            confidence=round(confidence, 2),
            reasoning_summary=base_summary,
            recommendation=recommendation.model_dump(),
            evidence=[{
                "type": "flight_search",
                "total_candidates": result["total_evaluated"],
                "best_flight": best.candidate.flight_number,
                "best_price": best.candidate.price,
                "best_score": best.score,
            }],
        )

    # ------------------------------------------------------------------
    # Deterministic helpers
    # ------------------------------------------------------------------

    def _deterministic_think(self, ctx: dict[str, Any],
                             state: SharedMissionState) -> dict[str, Any]:
        """Extract search parameters from mission context."""
        mission_ctx = ctx.get("mission_context", {})
        origin = mission_ctx.get("origin", "")
        destination = mission_ctx.get("destination", "")
        departure_date = mission_ctx.get("departure_date", "")
        traveler = mission_ctx.get("traveler", {})
        preferred_airline = traveler.get("airline_preference")

        self.logger.info(
            "Thinking: search %s -> %s on %s", origin, destination, departure_date)

        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "preferred_airline": preferred_airline,
            "budget_limit": mission_ctx.get("budget_limit", 1000.0),
        }

    def _deterministic_evaluate(self, observation: dict[str, Any],
                                state: SharedMissionState) -> dict[str, Any]:
        """Filter, rank, and select using deterministic scoring."""
        error = observation.get("error")
        candidates = observation.get("candidates", [])

        if error or not candidates:
            return {
                "ranked": [],
                "error": error or "No flight candidates found",
                "total_evaluated": 0,
            }

        # Filter: only same-route candidates (origin matches context)
        ctx = state.context
        valid = []
        for c in candidates:
            if c.departure_airport == ctx.origin:
                valid.append(c)

        # If filtering removed everything, keep all
        if not valid:
            valid = candidates

        # Rank
        preferred = None
        if ctx:
            preferred = ctx.traveler.airline_preference

        ranked = rank_candidates(valid, preferred_airline=preferred)

        return {
            "ranked": ranked,
            "error": None,
            "total_evaluated": len(ranked),
            "filtered_out": len(candidates) - len(valid),
        }

    # ------------------------------------------------------------------
    # ReAct helpers
    # ------------------------------------------------------------------

    def _force_final_decision(
        self,
        system_prompt: str,
        user_msg: str,
        tool_results: list[dict[str, Any]],
        all_ranked: list[dict[str, Any]],
        total_evaluated: int,
        trace: list[ReActTraceStep],
        step_num: int,
    ) -> dict[str, Any]:
        """Force a final decision when tool-call budget is exhausted."""
        from tros.llm.response_parser import parse_react_flight_response

        self.logger.info("Max tool calls reached — forcing final decision")

        # Add instruction to produce final decision
        force_msg = user_msg + (
            "\n\nYou have completed your searches. "
            "Now provide your FINAL decision based on the evidence gathered. "
            "Do NOT call any tools. Return a final decision JSON."
        )

        try:
            start = time.time()
            llm_result = self._llm.chat(
                system_prompt=system_prompt,
                user_message=force_msg,
                tools=None,  # No tools — force final decision
                tool_results=tool_results if tool_results else None,
            )
            ms = int((time.time() - start) * 1000)

            content = llm_result.get("content", "")
            if content:
                try:
                    raw_final = json.loads(content)
                except json.JSONDecodeError:
                    raw_final = {"type": "final", "reasoning_summary": content}
                final = parse_react_flight_response(raw_final)
            else:
                final = self._synthesize_final_from_evidence(all_ranked, total_evaluated)
        except Exception as exc:
            self.logger.warning("Forced final decision LLM call failed: %s", exc)
            final = self._synthesize_final_from_evidence(all_ranked, total_evaluated)
            ms = 0

        step_num  # Use caller's step_num — caller already incremented
        trace.append(ReActTraceStep(
            step_number=step_num,
            phase="FINAL",
            thought=final.get("thought", "Forced final decision"),
            observation={
                "decision": final.get("decision", ""),
                "confidence": final.get("confidence", 0.5),
            },
            duration_ms=ms,
        ))

        return final

    def _synthesize_final_from_evidence(
        self,
        all_ranked: list[dict[str, Any]],
        total_evaluated: int,
    ) -> dict[str, Any]:
        """Produce a deterministic final decision from accumulated evidence."""
        if not all_ranked:
            return {
                "type": "final",
                "thought": "No evidence available.",
                "decision": "no_viable_option",
                "reasoning_summary": "No flight candidates found.",
                "confidence": 0.0,
                "selected_flight_number": None,
            }

        # Pick the best by deterministic score
        best = max(all_ranked, key=lambda c: c.get("deterministic_score", 0))
        return {
            "type": "final",
            "thought": f"Selecting highest-scored candidate from {len(all_ranked)} options.",
            "decision": "recommend",
            "reasoning_summary": (
                f"Selected {best.get('flight_number', 'unknown')} "
                f"with score {best.get('deterministic_score', 0)} "
                f"from {total_evaluated} candidates evaluated."
            ),
            "confidence": 0.75,
            "selected_flight_number": best.get("flight_number"),
        }

    def _ensure_ranked_objects(
        self,
        all_ranked: list[dict[str, Any]],
        state: SharedMissionState,
    ) -> list:
        """Convert dict-based candidate data to RankedFlight objects for commit().

        The ReAct loop stores candidates as dicts from ToolObservation.
        commit() expects RankedFlight objects. This method converts them.
        """
        from tros.schemas.flight import FlightCandidate, RankedFlight

        objects = []
        for item in all_ranked:
            if isinstance(item, RankedFlight):
                objects.append(item)
            elif isinstance(item, dict):
                try:
                    candidate = FlightCandidate(
                        offer_id=item.get("offer_id", item.get("flight_number", "")),
                        flight_number=item.get("flight_number", ""),
                        carrier=item.get("carrier", ""),
                        departure_airport=item.get("origin", item.get("departure_airport", "")),
                        arrival_airport=item.get("destination", item.get("arrival_airport", "")),
                        departure_time=item.get("departure_time", ""),
                        arrival_time=item.get("arrival_time", ""),
                        duration_minutes=item.get("duration_minutes", 0),
                        stops=item.get("stops", 0),
                        price=item.get("price", 0.0),
                        currency=item.get("currency", "USD"),
                    )
                    ranked = RankedFlight(
                        candidate=candidate,
                        score=item.get("deterministic_score", item.get("score", 0.0)),
                        reasoning=item.get("reasoning", "balanced option"),
                    )
                    objects.append(ranked)
                except Exception as exc:
                    self.logger.warning("Failed to convert candidate dict: %s", exc)

        # De-duplicate by flight_number, keeping highest score
        seen: dict[str, RankedFlight] = {}
        for r in objects:
            fn = r.candidate.flight_number
            if fn not in seen or r.score > seen[fn].score:
                seen[fn] = r

        # Sort by score descending
        result = sorted(seen.values(), key=lambda r: r.score, reverse=True)
        return result


def _fmt_time(t: str) -> str:
    """Format HHMM or datetime string to HH:MM."""
    if len(t) >= 4:
        t = t[-4:]
        return f"{t[:2]}:{t[2:]}"
    return t
