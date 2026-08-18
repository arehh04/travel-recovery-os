"""Agent conflict detection — detects disagreements between agents (Phase 5).

Do not automatically let the LLM decide which agent is correct.
Use deterministic precedence rules:
  1. Safety / constraint validation
  2. Atlas evidence
  3. Deterministic ranking
  4. Budget rules
  5. Critic findings
  6. LLM reasoning
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentConflict(BaseModel):
    """A detected conflict between agent outputs."""
    agents: list[str] = Field(default_factory=list)
    category: str = ""  # budget | recommendation | validation | confidence
    description: str = ""
    severity: str = "warning"  # warning | critical
    resolution_required: bool = False


class ConflictReport(BaseModel):
    """Report of all detected conflicts."""
    conflicts: list[AgentConflict] = Field(default_factory=list)
    has_critical_conflict: bool = False


def detect_conflicts(
    flight_recommendation: dict[str, Any] | None = None,
    budget_assessment: dict[str, Any] | None = None,
    critic_report: dict[str, Any] | None = None,
    reflection_insights: list[dict[str, Any]] | None = None,
    evidence_validated: bool = False,
    recommended_flight: str = "",
) -> ConflictReport:
    """Detect disagreements between agents using deterministic precedence.

    Checks:
    - Budget vs Critic: budget says within_budget but critic says not approved
    - Flight vs Evidence: recommended flight doesn't exist in evidence
    - Critic vs Reflection: critic approved but reflection recommends different flight
    - Budget vs Flight: recommended flight exceeds budget
    """
    conflicts: list[AgentConflict] = []

    # Check 1: Budget vs Critic disagreement
    if budget_assessment and critic_report:
        budget_ok = budget_assessment.get("within_budget", False)
        critic_ok = critic_report.get("approved", False)
        if budget_ok and not critic_ok:
            conflicts.append(AgentConflict(
                agents=["BudgetAgent", "CriticAgent"],
                category="validation",
                description=(
                    "BudgetAgent reports within budget but CriticAgent "
                    "did not approve the plan"
                ),
                severity="warning",
                resolution_required=True,
            ))
        elif not budget_ok and critic_ok:
            conflicts.append(AgentConflict(
                agents=["BudgetAgent", "CriticAgent"],
                category="budget",
                description=(
                    "BudgetAgent reports over budget but CriticAgent "
                    "approved the plan"
                ),
                severity="critical",
                resolution_required=True,
            ))

    # Check 2: Evidence validation failure
    if recommended_flight and not evidence_validated:
        conflicts.append(AgentConflict(
            agents=["FlightAgent", "RecommendationValidator"],
            category="recommendation",
            description=(
                f"Recommended flight '{recommended_flight}' failed "
                f"evidence validation"
            ),
            severity="critical",
            resolution_required=True,
        ))

    # Check 3: Reflection recommends different flight than FlightAgent
    if reflection_insights and recommended_flight:
        for insight in reflection_insights:
            alt_flight = insight.get("alternative_flight", "")
            if alt_flight and alt_flight.upper() != recommended_flight.upper():
                conflicts.append(AgentConflict(
                    agents=["FlightAgent", "ReflectionAgent"],
                    category="recommendation",
                    description=(
                        f"FlightAgent recommends {recommended_flight} but "
                        f"ReflectionAgent suggests {alt_flight}"
                    ),
                    severity="warning",
                    resolution_required=False,
                ))

    # Check 4: Budget over limit with recommendation
    if budget_assessment and flight_recommendation:
        if not budget_assessment.get("within_budget", True):
            conflicts.append(AgentConflict(
                agents=["FlightAgent", "BudgetAgent"],
                category="budget",
                description=(
                    "Recommended flight exceeds mission budget limit"
                ),
                severity="critical",
                resolution_required=True,
            ))

    has_critical = any(c.severity == "critical" for c in conflicts)

    return ConflictReport(
        conflicts=conflicts,
        has_critical_conflict=has_critical,
    )
