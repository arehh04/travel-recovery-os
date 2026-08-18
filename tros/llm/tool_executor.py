"""Deterministic tool executor — validates and runs tool calls (Phase 4).

The LLM proposes tool calls; this module validates arguments against
mission constraints, executes via the Atlas adapter, normalizes, ranks,
and returns a structured observation.

Safety boundaries:
- Arguments are validated deterministically before execution
- Mission constraints (origin, destination, date window) are enforced
- No credentials are exposed in observations
- Unknown tools return an error observation (never executed)
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from tros.config import DEFAULT_CURRENCY
from tros.adapters.flight import (
    AtlasAdapterError,
    AtlasFlightAdapter,
    normalize_search_response,
)
from tros.llm.react_models import ToolObservation
from tros.utils.logging import get_logger

logger = get_logger("ToolExecutor")

# IATA airport code: exactly 3 uppercase letters
_IATA_RE = re.compile(r"^[A-Z]{3}$")

# YYYY-MM-DD date format
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Permitted date flexibility: ±3 days from mission departure date
_RECOVERY_WINDOW_DAYS = 3


class ToolExecutor:
    """Deterministic tool execution layer for the ReAct FlightAgent.

    The LLM requests tool calls; this executor validates and runs them.
    """

    def __init__(self, adapter: AtlasFlightAdapter | None = None) -> None:
        self._adapter = adapter or AtlasFlightAdapter()

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        mission_context: dict[str, Any],
    ) -> ToolObservation:
        """Execute a tool call with deterministic validation.

        Args:
            tool_name: The name of the tool to execute.
            arguments: The tool call arguments proposed by the LLM.
            mission_context: Mission context dict for constraint validation.

        Returns:
            A ToolObservation with results or error information.
        """
        if tool_name == "search_flights":
            return self._execute_search_flights(arguments, mission_context)

        logger.warning("Unknown tool requested: %s", tool_name)
        return ToolObservation(
            tool=tool_name,
            success=False,
            error_code="UNKNOWN_TOOL",
            message=f"Tool '{tool_name}' is not available.",
        )

    # ------------------------------------------------------------------
    # search_flights implementation
    # ------------------------------------------------------------------

    def _execute_search_flights(
        self,
        arguments: dict[str, Any],
        mission_context: dict[str, Any],
    ) -> ToolObservation:
        """Validate, search, normalize, and rank flight candidates."""
        # 1. Validate argument types and formats
        validation_error = self._validate_arguments(arguments, mission_context)
        if validation_error:
            return validation_error

        origin = arguments["origin"].upper()
        destination = arguments["destination"].upper()
        departure_date = arguments["departure_date"]
        adults = arguments.get("adults", 1)
        currency = arguments.get("currency", "USD")

        # 2. Execute Atlas search
        try:
            raw_response = self._adapter.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                adults=int(adults),
                currency=currency,
            )
        except AtlasAdapterError as exc:
            logger.error("Atlas search failed: %s", exc)
            return ToolObservation(
                tool="search_flights",
                success=False,
                error_code="ATLAS_ERROR",
                message=str(exc),
            )

        # 3. Normalize
        candidates = normalize_search_response(raw_response)
        search_id = raw_response.get("data", {}).get("search_id", "")
        offer_count = raw_response.get("data", {}).get("offer_count", len(candidates))

        # 4. Filter by route (same-route only)
        valid = [c for c in candidates if c.departure_airport == origin]
        if not valid:
            valid = candidates  # keep all if filter removes everything

        # 5. Rank candidates deterministically
        from tros.agents.flight.ranking import rank_candidates
        preferred_airline = mission_context.get("traveler", {}).get("airline_preference")
        ranked = rank_candidates(valid, preferred_airline=preferred_airline)

        # 6. Build observation with top candidates
        top_candidates = self._build_top_candidates(ranked)

        logger.info(
            "search_flights: %d offers, %d candidates, %d ranked, top=%s",
            offer_count, len(candidates), len(ranked),
            top_candidates[0].get("flight_number") if top_candidates else "none",
        )

        return ToolObservation(
            tool="search_flights",
            success=True,
            search_id=search_id,
            candidate_count=len(ranked),
            candidates=top_candidates,
        )

    # ------------------------------------------------------------------
    # Argument validation
    # ------------------------------------------------------------------

    def _validate_arguments(
        self,
        arguments: dict[str, Any],
        mission_context: dict[str, Any],
    ) -> ToolObservation | None:
        """Validate tool arguments. Returns a ToolObservation on error, None on success."""
        origin = arguments.get("origin", "")
        destination = arguments.get("destination", "")
        departure_date = arguments.get("departure_date", "")
        adults = arguments.get("adults", 1)

        # Required fields
        if not origin:
            return self._constraint_violation("origin is required")
        if not destination:
            return self._constraint_violation("destination is required")
        if not departure_date:
            return self._constraint_violation("departure_date is required")

        # IATA format
        origin_upper = str(origin).upper()
        dest_upper = str(destination).upper()
        if not _IATA_RE.match(origin_upper):
            return self._constraint_violation(
                f"Invalid origin airport code: '{origin}'. Must be 3 uppercase letters."
            )
        if not _IATA_RE.match(dest_upper):
            return self._constraint_violation(
                f"Invalid destination airport code: '{destination}'. Must be 3 uppercase letters."
            )

        # Date format
        if not _DATE_RE.match(str(departure_date)):
            return self._constraint_violation(
                f"Invalid departure_date format: '{departure_date}'. Must be YYYY-MM-DD."
            )

        # Date must be parseable
        try:
            dep_date = datetime.strptime(str(departure_date), "%Y-%m-%d")
        except ValueError:
            return self._constraint_violation(
                f"Cannot parse departure_date: '{departure_date}'."
            )

        # Adults must be positive integer
        try:
            adults_int = int(adults)
            if adults_int < 1:
                raise ValueError()
        except (ValueError, TypeError):
            return self._constraint_violation(
                f"adults must be a positive integer, got: '{adults}'."
            )

        # Currency must be a non-empty string
        currency = arguments.get("currency", "USD")
        if not currency or not isinstance(currency, str) or len(currency.strip()) == 0:
            return self._constraint_violation(
                "currency must be a non-empty string."
            )

        # --- Mission constraint validation ---

        mission_origin = (mission_context.get("origin") or "").upper()
        mission_dest = (mission_context.get("destination") or "").upper()

        if mission_origin and origin_upper != mission_origin:
            return self._constraint_violation(
                f"Origin '{origin_upper}' does not match mission origin '{mission_origin}'. "
                f"Search parameters must respect the mission constraints."
            )
        if mission_dest and dest_upper != mission_dest:
            return self._constraint_violation(
                f"Destination '{dest_upper}' does not match mission destination '{mission_dest}'. "
                f"Search parameters must respect the mission constraints."
            )

        # Date within recovery window
        mission_date_str = mission_context.get("departure_date", "")
        if mission_date_str:
            try:
                mission_date = datetime.strptime(str(mission_date_str), "%Y-%m-%d")
                delta = abs((dep_date - mission_date).days)
                if delta > _RECOVERY_WINDOW_DAYS:
                    return self._constraint_violation(
                        f"Departure date {departure_date} is {delta} days from mission date "
                        f"{mission_date_str}. Permitted window is ±{_RECOVERY_WINDOW_DAYS} days."
                    )
            except ValueError:
                pass  # Can't validate window if mission date is unparseable

        # Adults must match mission traveler count
        # MissionContext uses TravelerProfile (single traveler); traveler_count
        # defaults to 1 unless explicitly provided in mission_context.
        mission_traveler_count = mission_context.get("traveler_count")
        if mission_traveler_count is None:
            mission_traveler_count = 1  # single TravelerProfile = 1 traveler
        if int(adults_int) != int(mission_traveler_count):
            return self._constraint_violation(
                f"adults ({adults_int}) does not match mission traveler count "
                f"({mission_traveler_count})."
            )

        # Currency must match mission currency
        mission_currency = mission_context.get("currency") or DEFAULT_CURRENCY
        if str(currency).upper() != str(mission_currency).upper():
            return self._constraint_violation(
                f"Currency '{currency}' does not match mission currency '{mission_currency}'."
            )

        return None  # Validation passed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _constraint_violation(message: str) -> ToolObservation:
        """Build a CONSTRAINT_VIOLATION error observation."""
        logger.warning("Constraint violation: %s", message)
        return ToolObservation(
            tool="search_flights",
            success=False,
            error_code="CONSTRAINT_VIOLATION",
            message=message,
        )

    @staticmethod
    def _build_top_candidates(ranked: list, max_count: int = 5) -> list[dict[str, Any]]:
        """Convert top ranked flights to serializable dicts for LLM observation."""
        top = []
        for r in ranked[:max_count]:
            c = r.candidate
            top.append({
                "flight_number": c.flight_number,
                "carrier": c.carrier,
                "origin": c.departure_airport,
                "destination": c.arrival_airport,
                "departure_time": c.departure_time,
                "arrival_time": c.arrival_time,
                "duration_minutes": c.duration_minutes,
                "stops": c.stops,
                "price": c.price,
                "currency": c.currency,
                "deterministic_score": r.score,
                "reasoning": r.reasoning,
            })
        return top
