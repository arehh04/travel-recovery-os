"""Flight ranking — composite scoring strategy (Arch §7.3).

Weighting:
- Arrival Time: 35%
- Cost: 25%
- Delay (duration): 20%
- Stops: 10%
- Preference Match: 10%
"""

from __future__ import annotations

from tros.config import (
    RANKING_WEIGHT_ARRIVAL,
    RANKING_WEIGHT_COST,
    RANKING_WEIGHT_DELAY,
    RANKING_WEIGHT_PREFERENCE,
    RANKING_WEIGHT_STOPS,
)
from tros.schemas.flight import FlightCandidate, RankedFlight


def rank_candidates(
    candidates: list[FlightCandidate],
    preferred_airline: str | None = None,
) -> list[RankedFlight]:
    """Score and rank all flight candidates.

    Returns a sorted list (highest score first).
    """
    if not candidates:
        return []

    # Determine ranges for normalization
    prices = [c.price for c in candidates]
    durations = [c.duration_minutes for c in candidates]
    arrivals = [_parse_time_to_minutes(c.arrival_time) for c in candidates]

    min_price, max_price = min(prices), max(prices)
    min_dur, max_dur = min(durations), max(durations)
    min_arr, max_arr = min(arrivals), max(arrivals)

    ranked: list[RankedFlight] = []
    for candidate in candidates:
        arr_min = _parse_time_to_minutes(candidate.arrival_time)

        # Normalize each dimension to 0-100 (higher = better)
        arrival_score = _normalize_invert(arr_min, min_arr, max_arr)
        cost_score = _normalize_invert(candidate.price, min_price, max_price)
        delay_score = _normalize_invert(candidate.duration_minutes, min_dur, max_dur)
        stops_score = 100.0 if candidate.stops == 0 else max(0, 100.0 - candidate.stops * 40)

        pref_score = 0.0
        if preferred_airline:
            if candidate.carrier == preferred_airline:
                pref_score = 100.0
            elif candidate.operating_carrier == preferred_airline:
                pref_score = 70.0

        # Weighted composite
        composite = (
            arrival_score * RANKING_WEIGHT_ARRIVAL
            + cost_score * RANKING_WEIGHT_COST
            + delay_score * RANKING_WEIGHT_DELAY
            + stops_score * RANKING_WEIGHT_STOPS
            + pref_score * RANKING_WEIGHT_PREFERENCE
        )

        reasoning_parts = []
        if arrival_score >= 80:
            reasoning_parts.append("early arrival")
        if cost_score >= 80:
            reasoning_parts.append("low cost")
        if stops_score == 100:
            reasoning_parts.append("direct flight")
        if pref_score >= 70:
            reasoning_parts.append("preferred airline")

        ranked.append(RankedFlight(
            candidate=candidate,
            score=round(composite, 2),
            arrival_score=round(arrival_score, 2),
            cost_score=round(cost_score, 2),
            delay_score=round(delay_score, 2),
            stops_score=round(stops_score, 2),
            preference_score=round(pref_score, 2),
            reasoning=", ".join(reasoning_parts) or "balanced option",
        ))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def _parse_time_to_minutes(time_str: str) -> int:
    """Parse a time string to minutes for comparison.

    Supports two formats:
    - Full datetime: "YYYYMMDDHHMM" — returns total minutes from epoch
      (preserves cross-day ordering for multi-day itineraries)
    - Short time: "HHMM" — returns minutes since midnight
    """
    if not time_str or len(time_str) < 4:
        return 0
    try:
        if len(time_str) >= 12:
            # Full datetime format YYYYMMDDHHMM — include date for correct
            # cross-day ordering (e.g. arrival on Aug 21 > Aug 20)
            year = int(time_str[0:4])
            month = int(time_str[4:6])
            day = int(time_str[6:8])
            hours = int(time_str[8:10])
            minutes = int(time_str[10:12])
            # Total minutes from year 2000 — sufficient for relative comparison
            days_from_epoch = (year - 2000) * 365 + month * 30 + day
            return days_from_epoch * 1440 + hours * 60 + minutes
        # Short HHMM format
        hours = int(time_str[:2])
        minutes = int(time_str[2:])
        return hours * 60 + minutes
    except (ValueError, IndexError):
        return 0


def _normalize_invert(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value where lower is better → higher score.
    Returns 0-100 scale."""
    if max_val == min_val:
        return 100.0
    normalized = (value - min_val) / (max_val - min_val)
    return round((1.0 - normalized) * 100.0, 2)
