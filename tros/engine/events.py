"""Domain events for travel disruptions (Arch §3.6)."""

from __future__ import annotations

from tros.schemas.mission import DisruptionEvent, DisruptionType


def flight_cancelled(
    origin: str,
    destination: str,
    flight_number: str | None = None,
    airline: str | None = None,
    departure: str | None = None,
    arrival: str | None = None,
    booking_ref: str | None = None,
    description: str = "Flight has been cancelled by the airline.",
) -> DisruptionEvent:
    """Create a FlightCancelled event."""
    return DisruptionEvent(
        disruption_type=DisruptionType.FLIGHT_CANCELLED,
        origin=origin,
        destination=destination,
        original_flight_number=flight_number,
        original_departure=departure,
        original_arrival=arrival,
        booking_reference=booking_ref,
        airline=airline,
        description=description,
    )


def flight_delayed(
    origin: str,
    destination: str,
    flight_number: str | None = None,
    airline: str | None = None,
    departure: str | None = None,
    arrival: str | None = None,
    description: str = "Flight has been significantly delayed.",
) -> DisruptionEvent:
    """Create a FlightDelayed event."""
    return DisruptionEvent(
        disruption_type=DisruptionType.FLIGHT_DELAYED,
        origin=origin,
        destination=destination,
        original_flight_number=flight_number,
        original_departure=departure,
        original_arrival=arrival,
        airline=airline,
        description=description,
    )


def missed_connection(
    origin: str,
    destination: str,
    flight_number: str | None = None,
    airline: str | None = None,
    description: str = "Missed connecting flight due to upstream delay.",
) -> DisruptionEvent:
    """Create a MissedConnection event."""
    return DisruptionEvent(
        disruption_type=DisruptionType.MISSED_CONNECTION,
        origin=origin,
        destination=destination,
        original_flight_number=flight_number,
        airline=airline,
        description=description,
    )
