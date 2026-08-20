"""Candidate evidence store — factual data from deterministic tools only (Phase 5).

The evidence layer contains ONLY factual information returned by
deterministic tools (Atlas adapter). LLM-generated claims are never
stored as factual flight evidence.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CandidateEvidence(BaseModel):
    """A single flight candidate's factual evidence from Atlas."""
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    stops: int
    price: float
    currency: str
    deterministic_score: float
    source: str = "atlas_search"
    search_id: str | None = None
    evidence_type: str = "atlas_search"
    carrier: str = ""
    offer_id: str = ""


class EvidenceBundle(BaseModel):
    """Collection of candidate evidence from one or more searches."""
    candidates: list[CandidateEvidence] = Field(default_factory=list)
    search_ids: list[str] = Field(default_factory=list)
    total_candidates: int = 0
    source_count: int = 0


def build_evidence_bundle(
    ranked_candidates: list[dict[str, Any]],
    search_id: str = "",
) -> EvidenceBundle:
    """Build an EvidenceBundle from ranked candidate dicts.

    Only factual data from the Atlas adapter / deterministic ranking
    is included. No LLM-generated content enters the evidence store.
    """
    evidence_list: list[CandidateEvidence] = []
    for c in ranked_candidates:
        evidence_list.append(CandidateEvidence(
            flight_number=c.get("flight_number", ""),
            origin=c.get("origin", c.get("departure_airport", "")),
            destination=c.get("destination", c.get("arrival_airport", "")),
            departure_time=c.get("departure_time", ""),
            arrival_time=c.get("arrival_time", ""),
            duration_minutes=c.get("duration_minutes", 0),
            stops=c.get("stops", 0),
            price=c.get("price", 0.0),
            currency=c.get("currency", "USD"),
            deterministic_score=c.get("deterministic_score", c.get("score", 0.0)),
            source="atlas_search",
            search_id=search_id or c.get("search_id"),
            carrier=c.get("carrier", ""),
            offer_id=c.get("offer_id", ""),
        ))

    search_ids = [search_id] if search_id else []
    return EvidenceBundle(
        candidates=evidence_list,
        search_ids=search_ids,
        total_candidates=len(evidence_list),
        source_count=len(search_ids),
    )
