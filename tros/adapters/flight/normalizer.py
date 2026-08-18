"""Response normalizer — converts Atlas CLI output to TR-OS schemas (Arch §8.9).

Provider-specific fields are mapped to standardized FlightCandidate objects.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tros.schemas.flight import FlightCandidate
from tros.utils.logging import get_logger

logger = get_logger("Normalizer")


def normalize_search_response(raw: dict[str, Any]) -> list[FlightCandidate]:
    """Convert atlas-flight search JSON to a list of FlightCandidate objects.

    The raw response has the structure:
      data.offers[] with fields like offer_id, flight_number, segments[], etc.
    """
    data = raw.get("data", {})
    raw_offers = data.get("offers", [])

    if not raw_offers:
        logger.warning("No offers found in Atlas response")
        return []

    candidates: list[FlightCandidate] = []
    for offer in raw_offers:
        try:
            candidate = _normalize_offer(offer)
            candidates.append(candidate)
        except Exception as exc:
            logger.warning("Skipping malformed offer: %s", exc)
            continue

    logger.info("Normalized %d flight candidates", len(candidates))
    return candidates


def _normalize_offer(offer: dict[str, Any]) -> FlightCandidate:
    """Normalize a single Atlas offer into a FlightCandidate.

    For multi-segment itineraries:
    - departure_airport/time from the first segment
    - arrival_airport/time from the last segment
    - duration_minutes = total itinerary elapsed time (including layovers)
    - flight_number from the longest (primary) segment
    """
    segments = offer.get("segments", [])
    if not segments:
        raise ValueError("Offer has no segments")

    first_seg = segments[0]
    last_seg = segments[-1]

    # For multi-segment itineraries, use the longest segment as primary
    primary_seg = max(segments, key=lambda s: s.get("duration_minutes", 0))

    # Compute total itinerary duration from timestamps
    duration = _compute_itinerary_duration(first_seg, last_seg)

    # Extract pricing
    passenger_prices = offer.get("passenger_prices", [])
    base_fare = 0.0
    tax = 0.0
    if passenger_prices:
        pp = passenger_prices[0]
        base_fare = pp.get("base_fare_per_passenger", 0.0)
        tax = pp.get("tax_per_passenger", 0.0)

    # Count stops (number of segments minus 1)
    stops = max(0, len(segments) - 1)

    return FlightCandidate(
        offer_id=offer.get("offer_id", ""),
        flight_number=primary_seg.get("flight_number", ""),
        carrier=first_seg.get("carrier", ""),
        departure_airport=first_seg.get("departure_airport", ""),
        arrival_airport=last_seg.get("arrival_airport", ""),
        departure_time=first_seg.get("departure_time", ""),
        arrival_time=last_seg.get("arrival_time", ""),
        duration_minutes=duration,
        stops=stops,
        cabin_class=first_seg.get("cabin_class", 1),
        price=offer.get("total_price", 0.0),
        currency=offer.get("currency", "USD"),
        base_fare=base_fare,
        tax=tax,
        operating_carrier=first_seg.get("operating_carrier"),
        bookable=offer.get("bookable", False),
        price_status=offer.get("price_status", "reference"),
    )


def _parse_segment_datetime(time_str: str) -> datetime | None:
    """Parse an Atlas datetime string (YYYYMMDDHHMM) into a datetime object."""
    try:
        if len(time_str) >= 12:
            return datetime.strptime(time_str[:12], "%Y%m%d%H%M")
    except (ValueError, IndexError):
        pass
    return None


def _compute_itinerary_duration(
    first_seg: dict[str, Any], last_seg: dict[str, Any]
) -> int:
    """Compute total itinerary duration in minutes from first departure
    to last arrival (includes layover time).

    Falls back to sum of segment durations if timestamps cannot be parsed.
    """
    dep_dt = _parse_segment_datetime(first_seg.get("departure_time", ""))
    arr_dt = _parse_segment_datetime(last_seg.get("arrival_time", ""))

    if dep_dt and arr_dt:
        delta = arr_dt - dep_dt
        total_minutes = int(delta.total_seconds() / 60)
        if total_minutes > 0:
            return total_minutes

    # Fallback: sum of individual segment durations
    return first_seg.get("duration_minutes", 0) + (
        last_seg.get("duration_minutes", 0)
        if last_seg is not first_seg else 0
    )
