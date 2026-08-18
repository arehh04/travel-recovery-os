"""Deterministic confidence calculation — evidence-based (Phase 5).

Confidence is NEVER decided by the LLM. It is computed deterministically
from evidence factors. The formula is documented and reproducible.

Formula:
  base = 0.50
  + 0.10  evidence validation passed
  + 0.08  budget validation passed
  + 0.07  constraint validation passed
  + 0.08  critic approved
  + 0.07  ranking margin (score #1 - score #2 > 5)
  - 0.10  per unresolved conflict (max 2 conflicts)
  - 0.05  missing evidence
  Clamp: [0.0, 0.95]
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConfidenceFactors(BaseModel):
    """Input factors for the deterministic confidence calculation."""
    evidence_validated: bool = False
    budget_validated: bool = False
    constraint_validated: bool = False
    critic_approved: bool = False
    ranking_margin_bonus: bool = False
    unresolved_conflicts: int = 0
    missing_evidence: bool = False


class ConfidenceResult(BaseModel):
    """Result of the deterministic confidence calculation."""
    confidence: float = Field(default=0.5, ge=0.0, le=0.95)
    factors: ConfidenceFactors
    breakdown: dict[str, float] = Field(default_factory=dict)


def calculate_confidence(factors: ConfidenceFactors) -> ConfidenceResult:
    """Calculate confidence deterministically from evidence factors.

    The formula is:
      base = 0.50
      + 0.10 if evidence validation passed
      + 0.08 if budget validation passed
      + 0.07 if constraint validation passed
      + 0.08 if critic approved
      + 0.07 if ranking margin is significant
      - 0.10 per unresolved conflict (max deduction 0.20)
      - 0.05 if evidence is missing
      Clamped to [0.0, 0.95]
    """
    base = 0.50
    breakdown: dict[str, float] = {"base": base}

    if factors.evidence_validated:
        base += 0.10
        breakdown["evidence_validated"] = 0.10

    if factors.budget_validated:
        base += 0.08
        breakdown["budget_validated"] = 0.08

    if factors.constraint_validated:
        base += 0.07
        breakdown["constraint_validated"] = 0.07

    if factors.critic_approved:
        base += 0.08
        breakdown["critic_approved"] = 0.08

    if factors.ranking_margin_bonus:
        base += 0.07
        breakdown["ranking_margin_bonus"] = 0.07

    conflict_penalty = min(factors.unresolved_conflicts * 0.10, 0.20)
    if conflict_penalty > 0:
        base -= conflict_penalty
        breakdown["conflict_penalty"] = -conflict_penalty

    if factors.missing_evidence:
        base -= 0.05
        breakdown["missing_evidence"] = -0.05

    # Clamp
    clamped = max(0.0, min(0.95, base))
    breakdown["final"] = round(clamped, 2)

    return ConfidenceResult(
        confidence=round(clamped, 2),
        factors=factors,
        breakdown=breakdown,
    )
