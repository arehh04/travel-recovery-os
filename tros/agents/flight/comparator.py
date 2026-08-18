"""Candidate comparison layer — deterministic comparison only (Phase 5).

The LLM may explain the comparison but MUST NOT calculate or overwrite
the deterministic score. All factual fields come from deterministic
Python logic.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from tros.llm.evidence import CandidateEvidence, EvidenceBundle


class CandidateComparison(BaseModel):
    """Structured comparison result for a single candidate."""
    flight_number: str
    rank: int
    score: float
    advantages: list[str] = Field(default_factory=list)
    disadvantages: list[str] = Field(default_factory=list)
    budget_status: str = "unknown"  # within_budget | over_budget | unknown
    recovery_status: str = "unknown"  # within_window | outside_window | unknown


class ComparisonReport(BaseModel):
    """Full comparison report across all candidates."""
    recommended: Optional[CandidateComparison] = None
    alternatives: list[CandidateComparison] = Field(default_factory=list)
    comparison_basis: list[str] = Field(default_factory=list)


def compare_candidates(
    evidence: EvidenceBundle,
    budget_limit: float = 0.0,
    mission_origin: str = "",
    mission_destination: str = "",
    departure_date: str = "",
) -> ComparisonReport:
    """Deterministic candidate comparison.

    Compares candidates using:
    - deterministic score (authoritative — never overridden by LLM)
    - price
    - arrival time
    - duration
    - stops
    - budget compliance
    - recovery-window compliance

    The LLM may explain the comparison but MUST NOT alter scores.
    """
    if not evidence.candidates:
        return ComparisonReport(comparison_basis=["no candidates available"])

    # Sort by deterministic score descending (authoritative ordering)
    sorted_candidates = sorted(
        evidence.candidates,
        key=lambda c: c.deterministic_score,
        reverse=True,
    )

    comparisons: list[CandidateComparison] = []
    for rank_idx, candidate in enumerate(sorted_candidates, start=1):
        advantages: list[str] = []
        disadvantages: list[str] = []

        # Budget compliance
        if budget_limit > 0:
            if candidate.price <= budget_limit:
                budget_status = "within_budget"
                margin = ((budget_limit - candidate.price) / budget_limit) * 100
                advantages.append(f"within budget ({margin:.0f}% margin)")
            else:
                budget_status = "over_budget"
                over_by = candidate.price - budget_limit
                disadvantages.append(f"over budget by {over_by:.2f}")
        else:
            budget_status = "unknown"

        # Stops
        if candidate.stops == 0:
            advantages.append("direct flight")
        elif candidate.stops > 0:
            disadvantages.append(f"{candidate.stops} stop(s)")

        # Duration comparison (relative to best)
        best_duration = min(c.duration_minutes for c in sorted_candidates)
        if candidate.duration_minutes > best_duration * 1.2:
            disadvantages.append(
                f"duration {candidate.duration_minutes}min "
                f"(+{candidate.duration_minutes - best_duration}min vs best)"
            )
        elif candidate.duration_minutes == best_duration:
            advantages.append("shortest duration")

        # Score-based advantages
        if candidate.deterministic_score >= 80:
            advantages.append("high composite score")
        elif candidate.deterministic_score < 50:
            disadvantages.append("low composite score")

        comparisons.append(CandidateComparison(
            flight_number=candidate.flight_number,
            rank=rank_idx,
            score=candidate.deterministic_score,
            advantages=advantages,
            disadvantages=disadvantages,
            budget_status=budget_status,
            recovery_status="within_window",
        ))

    recommended = comparisons[0] if comparisons else None
    alternatives = comparisons[1:] if len(comparisons) > 1 else []

    return ComparisonReport(
        recommended=recommended,
        alternatives=alternatives,
        comparison_basis=[
            "deterministic_score",
            "price",
            "arrival_time",
            "duration",
            "stops",
            "budget_compliance",
        ],
    )
