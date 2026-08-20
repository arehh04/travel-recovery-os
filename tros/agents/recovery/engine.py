"""Recovery Engine — bounded recovery + re-evaluation (Phase 6).

Inspects Phase 5 outputs (ConflictReport, ValidationResult, EvidenceBundle,
BudgetAssessment) and determines whether recovery is necessary.

Recovery actions are bounded by LLM_MAX_RECOVERY_ATTEMPTS.
The engine reuses the existing ToolExecutor → AtlasFlightAdapter path.
It never calls subprocess or Atlas CLI directly.

Re-evaluation re-runs the full Phase 5 deterministic pipeline on new evidence.
"""

from __future__ import annotations

from typing import Any

from tros.agents.conflict_detector import ConflictReport
from tros.agents.flight.comparator import compare_candidates
from tros.agents.flight.confidence import ConfidenceFactors, calculate_confidence
from tros.agents.flight.recommendation_validator import validate_recommendation
from tros.agents.recovery.models import (
    RecoveryAction,
    RecoveryActionType,
    RecoveryHistoryEntry,
    RecoveryResult,
)
from tros.config import DEFAULT_CURRENCY, LLM_MAX_RECOVERY_ATTEMPTS
from tros.llm.evidence import EvidenceBundle, build_evidence_bundle
from tros.utils.logging import get_logger

logger = get_logger("RecoveryEngine")


class RecoveryEngine:
    """Bounded recovery engine for flight recovery missions.

    Reuses the existing ToolExecutor for Atlas search.
    Never creates a second Atlas execution mechanism.
    """

    def __init__(
        self,
        tool_executor: Any,
        max_attempts: int | None = None,
    ) -> None:
        self._tool_executor = tool_executor
        self._max_attempts = (
            max_attempts if max_attempts is not None
            else LLM_MAX_RECOVERY_ATTEMPTS
        )

    def run(
        self,
        *,
        conflict_report: ConflictReport,
        validation_result: Any,
        evidence: EvidenceBundle,
        budget_assessment: dict[str, Any],
        mission_context: dict[str, Any],
        flight_data: dict[str, Any],
        state: Any,
    ) -> RecoveryResult:
        """Execute bounded recovery if needed.

        Returns a RecoveryResult with recovery outcome and updated state.
        """
        # Determine if recovery is needed
        action = self._determine_action(
            conflict_report=conflict_report,
            validation_result=validation_result,
            evidence=evidence,
            budget_assessment=budget_assessment,
            attempt_number=0,
        )

        if action.action_type == RecoveryActionType.TERMINATE_NO_SOLUTION:
            # No recovery needed or no valid action possible
            if not conflict_report.has_critical_conflict and validation_result.valid:
                return RecoveryResult(
                    recovered=False,
                    terminated=False,
                    reason="No recovery needed — recommendation is valid",
                    final_validation_valid=True,
                    attempts_used=0,
                    final_candidate=validation_result.validated_flight,
                )
            # Critical issue but no recovery possible
            return RecoveryResult(
                recovered=False,
                terminated=True,
                reason=action.reason or "Unrecoverable — no valid action available",
                final_validation_valid=False,
                attempts_used=0,
            )

        # Execute recovery loop
        result = RecoveryResult()
        current_evidence = evidence
        history: list[dict[str, Any]] = []

        for attempt in range(1, self._max_attempts + 1):
            logger.info("Recovery attempt %d/%d: %s", attempt, self._max_attempts,
                        action.action_type.value)

            # Record attempt
            entry = RecoveryHistoryEntry(
                attempt_number=attempt,
                triggering_reason=action.reason,
                detected_conflicts=[c.description for c in conflict_report.conflicts],
                action=action.action_type,
            )

            # Execute the recovery action
            if action.action_type == RecoveryActionType.USE_NEXT_VALID_CANDIDATE:
                new_flight_data, new_evidence = self._try_next_valid_candidate(
                    current_evidence, flight_data, mission_context,
                )
            elif action.action_type == RecoveryActionType.RESEARCH_FLIGHTS:
                new_flight_data, new_evidence = self._try_research(
                    mission_context, state, attempt,
                )
            elif action.action_type == RecoveryActionType.REEVALUATE_CANDIDATES:
                new_flight_data, new_evidence = self._try_reevaluate(
                    current_evidence, flight_data, mission_context,
                )
            else:
                entry.result = "terminated"
                history.append(entry.model_dump())
                break

            if new_flight_data is None:
                # Recovery action failed
                entry.result = "failed"
                entry.candidates_found = 0
                history.append(entry.model_dump())

                # Determine next action
                action = self._determine_action(
                    conflict_report=conflict_report,
                    validation_result=validation_result,
                    evidence=current_evidence,
                    budget_assessment=budget_assessment,
                    attempt_number=attempt,
                )
                if action.action_type == RecoveryActionType.TERMINATE_NO_SOLUTION:
                    break
                continue

            # Re-evaluate: run full Phase 5 pipeline on new data
            new_validation, new_conflict, new_budget, new_confidence = (
                self._reevaluate(
                    new_evidence, new_flight_data, mission_context, state,
                )
            )

            entry.result = "success" if new_validation.valid else "failed"
            entry.candidates_found = new_evidence.total_candidates
            entry.validation_valid = new_validation.valid
            entry.search_parameters = action.search_modifications
            history.append(entry.model_dump())

            result.actions_taken.append(action)
            result.attempts_used = attempt
            result.final_validation_valid = new_validation.valid
            result.final_candidate = new_validation.validated_flight
            result.final_confidence = new_confidence

            # Store updated evidence (versioned)
            evidence_version = attempt + 1  # v1 = initial, v2 = attempt 1, etc.
            state.evidence = {
                **new_evidence.model_dump(),
                "evidence_version": evidence_version,
                "recovery_attempt": attempt,
            }

            # Update flight data for downstream
            state.flight = new_flight_data

            if new_validation.valid and not new_conflict.has_critical_conflict:
                result.recovered = True
                result.terminated = False
                result.reason = (
                    f"Recovery successful on attempt {attempt}: "
                    f"{new_validation.validated_flight}"
                )
                break

            # Update for next iteration
            current_evidence = new_evidence
            flight_data = new_flight_data
            conflict_report = new_conflict
            validation_result = new_validation
            budget_assessment = new_budget

            # Determine next action
            action = self._determine_action(
                conflict_report=conflict_report,
                validation_result=validation_result,
                evidence=current_evidence,
                budget_assessment=budget_assessment,
                attempt_number=attempt,
            )
            if action.action_type == RecoveryActionType.TERMINATE_NO_SOLUTION:
                result.terminated = True
                result.reason = "Max recovery attempts reached or no valid action"
                break

        if not result.recovered and not result.terminated:
            result.terminated = True
            result.reason = result.reason or "Recovery loop completed without success"

        # Store recovery history in state
        state.recovery_history = history
        state.recovery_state = {
            "recovered": result.recovered,
            "terminated": result.terminated,
            "attempts_used": result.attempts_used,
            "reason": result.reason,
        }

        # Store evidence versions
        existing_versions = state.evidence_versions or []
        existing_versions.append({
            "version": result.attempts_used + 1,
            "attempt": result.attempts_used,
            "total_candidates": current_evidence.total_candidates,
            "recovered": result.recovered,
        })
        state.evidence_versions = existing_versions

        return result

    # ------------------------------------------------------------------
    # Recovery action determination (deterministic precedence)
    # ------------------------------------------------------------------

    def _determine_action(
        self,
        *,
        conflict_report: ConflictReport,
        validation_result: Any,
        evidence: EvidenceBundle,
        budget_assessment: dict[str, Any],
        attempt_number: int,
    ) -> RecoveryAction:
        """Determine the next recovery action using deterministic precedence.

        Precedence (highest to lowest):
        1. invalid/mismatched mission constraints
        2. fabricated/non-evidence recommendation
        3. critical critic rejection
        4. budget violation
        5. unresolved critical conflict
        6. non-critical conflict
        7. no recovery needed
        """
        # Max attempts exhausted
        if attempt_number >= self._max_attempts:
            return RecoveryAction(
                action_type=RecoveryActionType.TERMINATE_NO_SOLUTION,
                reason=f"Max recovery attempts ({self._max_attempts}) exhausted",
                attempt_number=attempt_number,
            )

        # Check if recommendation validation failed
        if hasattr(validation_result, 'valid') and not validation_result.valid:
            errors = getattr(validation_result, 'errors', [])

            # Priority 1-2: constraint mismatch or fabricated recommendation
            is_fabricated = any("not found" in e.lower() for e in errors)
            is_constraint = any(
                kw in " ".join(errors).lower()
                for kw in ["origin", "destination", "currency", "does not match"]
            )

            if is_fabricated or is_constraint:
                # Try next valid candidate from existing evidence
                if evidence.total_candidates > 1:
                    return RecoveryAction(
                        action_type=RecoveryActionType.USE_NEXT_VALID_CANDIDATE,
                        reason=f"Recommendation invalid: {'; '.join(errors[:2])}",
                        triggering_conflicts=errors[:3],
                        attempt_number=attempt_number + 1,
                    )
                # Need fresh search
                return RecoveryAction(
                    action_type=RecoveryActionType.RESEARCH_FLIGHTS,
                    reason=f"Recommendation invalid and no alternatives: {'; '.join(errors[:2])}",
                    triggering_conflicts=errors[:3],
                    attempt_number=attempt_number + 1,
                )

        # Priority 3-4: critic rejection or budget violation
        budget_within = budget_assessment.get("within_budget", True)
        critic_conflicts = [
            c for c in conflict_report.conflicts if c.severity == "critical"
        ]

        if critic_conflicts or not budget_within:
            reason_parts = []
            if not budget_within:
                reason_parts.append("Budget violation")
            if critic_conflicts:
                reason_parts.append(
                    f"{len(critic_conflicts)} critical conflict(s)"
                )
            reason = "; ".join(reason_parts)

            if evidence.total_candidates > 1:
                return RecoveryAction(
                    action_type=RecoveryActionType.USE_NEXT_VALID_CANDIDATE,
                    reason=reason,
                    triggering_conflicts=[c.description for c in critic_conflicts[:3]],
                    attempt_number=attempt_number + 1,
                )
            return RecoveryAction(
                action_type=RecoveryActionType.RESEARCH_FLIGHTS,
                reason=reason,
                triggering_conflicts=[c.description for c in critic_conflicts[:3]],
                attempt_number=attempt_number + 1,
            )

        # Priority 5-6: non-critical conflicts
        if conflict_report.conflicts:
            return RecoveryAction(
                action_type=RecoveryActionType.REEVALUATE_CANDIDATES,
                reason=f"{len(conflict_report.conflicts)} non-critical conflict(s)",
                triggering_conflicts=[
                    c.description for c in conflict_report.conflicts[:3]
                ],
                attempt_number=attempt_number + 1,
            )

        # Priority 7: no recovery needed
        return RecoveryAction(
            action_type=RecoveryActionType.TERMINATE_NO_SOLUTION,
            reason="No recovery needed — all checks passed",
            attempt_number=attempt_number,
        )

    # ------------------------------------------------------------------
    # Recovery action execution
    # ------------------------------------------------------------------

    def _try_next_valid_candidate(
        self,
        evidence: EvidenceBundle,
        flight_data: dict[str, Any],
        mission_context: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, EvidenceBundle]:
        """Try the next valid candidate from existing evidence.

        Deterministically selects the next-highest-scored candidate
        that satisfies mission constraints.
        """
        mission_origin = mission_context.get("origin", "")
        mission_dest = mission_context.get("destination", "")
        mission_currency = mission_context.get("currency") or DEFAULT_CURRENCY

        # Get current best flight number to skip it
        current_best = (
            flight_data.get("best_option", {})
            .get("candidate", {}).get("flight_number", "")
        )

        # Sort by score descending, skip current best
        sorted_candidates = sorted(
            [c for c in evidence.candidates
             if c.flight_number != current_best],
            key=lambda c: c.deterministic_score,
            reverse=True,
        )

        for candidate in sorted_candidates:
            # Validate this candidate
            result = validate_recommendation(
                selected_flight_number=candidate.flight_number,
                evidence=evidence,
                mission_origin=mission_origin,
                mission_destination=mission_dest,
                mission_currency=mission_currency,
            )
            if result.valid:
                # Build new flight data with this candidate
                new_flight = self._build_flight_data_from_candidate(
                    candidate, evidence, flight_data,
                )
                return new_flight, evidence

        return None, evidence

    def _try_research(
        self,
        mission_context: dict[str, Any],
        state: Any,
        attempt: int,
    ) -> tuple[dict[str, Any] | None, EvidenceBundle]:
        """Re-search via ToolExecutor — the only Atlas execution path."""
        origin = mission_context.get("origin", "")
        destination = mission_context.get("destination", "")
        departure_date = mission_context.get("departure_date", "")

        if not origin or not destination or not departure_date:
            return None, EvidenceBundle()

        search_args = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": mission_context.get("traveler_count", 1),
            "currency": mission_context.get("currency") or DEFAULT_CURRENCY,
        }

        try:
            observation = self._tool_executor.execute_tool(
                "search_flights", search_args, mission_context,
            )
        except Exception as exc:
            logger.warning("Recovery re-search failed: %s", exc)
            return None, EvidenceBundle()

        if not observation.success:
            logger.warning("Recovery re-search returned error: %s", observation.message)
            return None, EvidenceBundle()

        # Build evidence from new search
        new_evidence = build_evidence_bundle(
            observation.candidates,
            search_id=observation.search_id or "",
        )

        # Build flight data from new candidates
        if not observation.candidates:
            return None, new_evidence

        best = observation.candidates[0]
        alternatives = observation.candidates[1:5]

        new_flight = {
            "best_option": {
                "candidate": {
                    "flight_number": best.get("flight_number", ""),
                    "carrier": best.get("carrier", ""),
                    "departure_airport": best.get("origin", ""),
                    "arrival_airport": best.get("destination", ""),
                    "departure_time": best.get("departure_time", ""),
                    "arrival_time": best.get("arrival_time", ""),
                    "duration_minutes": best.get("duration_minutes", 0),
                    "stops": best.get("stops", 0),
                    "price": best.get("price", 0.0),
                    "currency": best.get("currency", DEFAULT_CURRENCY),
                    "offer_id": best.get("offer_id", ""),
                },
                "score": best.get("deterministic_score", 0.0),
                "reasoning": best.get("reasoning", "recovery candidate"),
            },
            "alternatives": [
                {
                    "candidate": {
                        "flight_number": a.get("flight_number", ""),
                        "carrier": a.get("carrier", ""),
                        "departure_airport": a.get("origin", ""),
                        "arrival_airport": a.get("destination", ""),
                        "departure_time": a.get("departure_time", ""),
                        "arrival_time": a.get("arrival_time", ""),
                        "duration_minutes": a.get("duration_minutes", 0),
                        "stops": a.get("stops", 0),
                        "price": a.get("price", 0.0),
                        "currency": a.get("currency", DEFAULT_CURRENCY),
                        "offer_id": a.get("offer_id", ""),
                    },
                    "score": a.get("deterministic_score", 0.0),
                    "reasoning": a.get("reasoning", "recovery alternative"),
                }
                for a in alternatives
            ],
            "total_candidates_evaluated": observation.candidate_count,
        }

        logger.info(
            "Recovery re-search: %d candidates, best=%s",
            observation.candidate_count,
            best.get("flight_number"),
        )

        return new_flight, new_evidence

    def _try_reevaluate(
        self,
        evidence: EvidenceBundle,
        flight_data: dict[str, Any],
        mission_context: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, EvidenceBundle]:
        """Re-evaluate existing candidates with different selection criteria.

        Picks the candidate with best budget compliance rather than
        pure score.
        """
        budget_limit = float(mission_context.get("budget_limit", 1000.0))
        mission_origin = mission_context.get("origin", "")
        mission_dest = mission_context.get("destination", "")
        mission_currency = mission_context.get("currency") or DEFAULT_CURRENCY
        current_best = (
            flight_data.get("best_option", {})
            .get("candidate", {}).get("flight_number", "")
        )

        # Find candidates within budget, sorted by score
        within_budget = sorted(
            [c for c in evidence.candidates
             if c.price <= budget_limit and c.flight_number != current_best],
            key=lambda c: c.deterministic_score,
            reverse=True,
        )

        if within_budget:
            candidate = within_budget[0]
            result = validate_recommendation(
                candidate.flight_number, evidence,
                mission_origin=mission_origin,
                mission_destination=mission_dest,
                mission_currency=mission_currency,
            )
            if result.valid:
                new_flight = self._build_flight_data_from_candidate(
                    candidate, evidence, flight_data,
                )
                return new_flight, evidence

        return None, evidence

    # ------------------------------------------------------------------
    # Re-evaluation pipeline (re-runs Phase 5)
    # ------------------------------------------------------------------

    def _reevaluate(
        self,
        evidence: EvidenceBundle,
        flight_data: dict[str, Any],
        mission_context: dict[str, Any],
        state: Any,
    ) -> tuple:
        """Re-run the full Phase 5 deterministic pipeline on new evidence.

        Returns: (validation_result, conflict_report, budget_assessment, confidence)
        """
        from tros.agents.conflict_detector import detect_conflicts

        mission_origin = mission_context.get("origin", "")
        mission_dest = mission_context.get("destination", "")
        mission_currency = mission_context.get("currency") or DEFAULT_CURRENCY
        budget_limit = float(mission_context.get("budget_limit", 1000.0))

        # Comparison
        comparison = compare_candidates(
            evidence, budget_limit=budget_limit,
            mission_origin=mission_origin,
            mission_destination=mission_dest,
        )

        # Budget assessment
        best_price = (
            flight_data.get("best_option", {})
            .get("candidate", {}).get("price", 0)
        )
        budget_assessment = {
            "within_budget": best_price <= budget_limit,
            "price": best_price,
            "budget_limit": budget_limit,
            "remaining_budget": budget_limit - best_price,
        }

        # Recommendation validation
        best_flight = (
            flight_data.get("best_option", {})
            .get("candidate", {}).get("flight_number", "")
        )
        validation = validate_recommendation(
            best_flight, evidence,
            mission_origin=mission_origin,
            mission_destination=mission_dest,
            mission_currency=mission_currency,
        )

        # Conflict detection (simplified — no critic/reflection for recovery)
        conflict = detect_conflicts(
            flight_recommendation=flight_data,
            budget_assessment=budget_assessment,
            critic_report={"approved": True},  # Assume critic passes in recovery
            evidence_validated=validation.valid,
            recommended_flight=best_flight,
        )

        # Confidence
        ranking_margin = False
        if comparison.recommended and comparison.alternatives:
            top = comparison.recommended.score
            second = comparison.alternatives[0].score if comparison.alternatives else 0
            ranking_margin = (top - second) > 5

        factors = ConfidenceFactors(
            evidence_validated=validation.valid,
            budget_validated=budget_assessment.get("within_budget", False),
            constraint_validated=validation.valid,
            critic_approved=True,
            ranking_margin_bonus=ranking_margin,
            unresolved_conflicts=sum(
                1 for c in conflict.conflicts if c.resolution_required
            ),
            missing_evidence=evidence.total_candidates == 0,
        )
        confidence = calculate_confidence(factors)

        return validation, conflict, budget_assessment, confidence.confidence

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_flight_data_from_candidate(
        candidate,
        evidence: EvidenceBundle,
        old_flight_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Build flight_data dict from a CandidateEvidence object."""
        alternatives = [
            {
                "candidate": {
                    "flight_number": c.flight_number,
                    "carrier": c.carrier,
                    "departure_airport": c.origin,
                    "arrival_airport": c.destination,
                    "departure_time": c.departure_time,
                    "arrival_time": c.arrival_time,
                    "duration_minutes": c.duration_minutes,
                    "stops": c.stops,
                    "price": c.price,
                    "currency": c.currency,
                    "offer_id": c.offer_id,
                },
                "score": c.deterministic_score,
                "reasoning": "recovery alternative",
            }
            for c in evidence.candidates
            if c.flight_number != candidate.flight_number
        ][:4]

        return {
            "best_option": {
                "candidate": {
                    "flight_number": candidate.flight_number,
                    "carrier": candidate.carrier,
                    "departure_airport": candidate.origin,
                    "arrival_airport": candidate.destination,
                    "departure_time": candidate.departure_time,
                    "arrival_time": candidate.arrival_time,
                    "duration_minutes": candidate.duration_minutes,
                    "stops": candidate.stops,
                    "price": candidate.price,
                    "currency": candidate.currency,
                    "offer_id": candidate.offer_id,
                },
                "score": candidate.deterministic_score,
                "reasoning": "recovery candidate",
            },
            "alternatives": alternatives,
            "total_candidates_evaluated": evidence.total_candidates,
        }
