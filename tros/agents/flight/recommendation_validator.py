"""Recommendation integrity check — verifies LLM recommendation against evidence (Phase 5).

The LLM recommendation must NEVER be trusted simply because it says
a flight is recommended. Python verifies it against evidence.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from tros.llm.evidence import EvidenceBundle


class ValidationResult(BaseModel):
    """Result of recommendation validation against evidence."""
    valid: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validated_flight: Optional[str] = None


def validate_recommendation(
    selected_flight_number: str,
    evidence: EvidenceBundle,
    mission_origin: str = "",
    mission_destination: str = "",
    mission_currency: str = "USD",
    departure_date: str = "",
    expected_score: float | None = None,
    traveler_count: int = 1,
) -> ValidationResult:
    """Validate that the recommended flight exists in evidence and matches constraints.

    Checks:
    - selected flight exists in Atlas evidence
    - selected flight origin matches mission
    - selected flight destination matches mission
    - selected flight currency matches mission currency
    - selected flight price is real Atlas data (not fabricated)
    - deterministic score matches ranking output
    - selected flight is not fabricated by the LLM
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not selected_flight_number:
        errors.append("No flight number provided for validation")
        return ValidationResult(valid=False, errors=errors)

    # Check flight exists in evidence
    matching = [
        c for c in evidence.candidates
        if c.flight_number.upper() == selected_flight_number.upper()
    ]
    if not matching:
        errors.append(
            f"Flight '{selected_flight_number}' not found in evidence. "
            f"Available: {[c.flight_number for c in evidence.candidates]}"
        )
        return ValidationResult(
            valid=False,
            errors=errors,
            validated_flight=selected_flight_number,
        )

    flight = matching[0]

    # Origin match
    if mission_origin and flight.origin.upper() != mission_origin.upper():
        errors.append(
            f"Flight origin '{flight.origin}' does not match "
            f"mission origin '{mission_origin}'"
        )

    # Destination match
    if mission_destination and flight.destination.upper() != mission_destination.upper():
        errors.append(
            f"Flight destination '{flight.destination}' does not match "
            f"mission destination '{mission_destination}'"
        )

    # Currency match
    if mission_currency and flight.currency.upper() != mission_currency.upper():
        errors.append(
            f"Flight currency '{flight.currency}' does not match "
            f"mission currency '{mission_currency}'"
        )

    # Price is real (positive, from Atlas)
    if flight.price <= 0:
        errors.append(f"Flight price {flight.price} is not valid Atlas data")

    # Score match (if expected_score provided)
    if expected_score is not None:
        if abs(flight.deterministic_score - expected_score) > 0.5:
            errors.append(
                f"Deterministic score mismatch: evidence has "
                f"{flight.deterministic_score}, expected {expected_score}"
            )

    is_valid = len(errors) == 0
    return ValidationResult(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        validated_flight=selected_flight_number,
    )
