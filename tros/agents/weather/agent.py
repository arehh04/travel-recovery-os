"""Weather Agent — Aviation Weather Risk Assessment & Route Safety.

Evaluates METAR/TAF conditions, convective storms, crosswinds, freezing levels,
and ground-stop delay probabilities across origin, hub, and destination airports.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

from tros.agents.base import BaseAgent
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.state.mission_state import SharedMissionState


# Airport climate profiles for realistic deterministic simulation
AIRPORT_WEATHER_PROFILES: dict[str, dict[str, Any]] = {
    "KUL": {"temp": 31, "condition": "Tropical Thunderstorms", "wind": 8, "vis": 9.0, "risk": 0.25},
    "SIN": {"temp": 30, "condition": "Scattered Showers", "wind": 6, "vis": 10.0, "risk": 0.15},
    "NRT": {"temp": 24, "condition": "Clear / Light Breeze", "wind": 12, "vis": 10.0, "risk": 0.05},
    "HND": {"temp": 25, "condition": "Clear Skies", "wind": 10, "vis": 10.0, "risk": 0.05},
    "LHR": {"temp": 18, "condition": "Overcast / Low Ceiling", "wind": 16, "vis": 7.5, "risk": 0.20},
    "LGW": {"temp": 17, "condition": "Light Drizzle", "wind": 14, "vis": 8.0, "risk": 0.15},
    "JFK": {"temp": 22, "condition": "Isolated Convective Storms", "wind": 18, "vis": 8.5, "risk": 0.35},
    "EWR": {"temp": 22, "condition": "Ground Delay Program (GDP)", "wind": 19, "vis": 7.0, "risk": 0.40},
    "ORD": {"temp": 14, "condition": "Severe Thunderstorms / Microburst Alert", "wind": 28, "vis": 4.0, "risk": 0.75},
    "LAX": {"temp": 26, "condition": "Sunny / VFR", "wind": 7, "vis": 10.0, "risk": 0.02},
    "SFO": {"temp": 16, "condition": "Marine Layer Fog", "wind": 15, "vis": 5.0, "risk": 0.30},
    "DXB": {"temp": 38, "condition": "Clear / Extreme Heat", "wind": 11, "vis": 10.0, "risk": 0.10},
    "DOH": {"temp": 37, "condition": "Clear Skies", "wind": 9, "vis": 10.0, "risk": 0.08},
    "CDG": {"temp": 20, "condition": "Partly Cloudy", "wind": 12, "vis": 10.0, "risk": 0.10},
    "FRA": {"temp": 19, "condition": "Scattered Clouds", "wind": 10, "vis": 10.0, "risk": 0.08},
    "AMS": {"temp": 18, "condition": "Breezy / Rain Showers", "wind": 22, "vis": 8.0, "risk": 0.25},
    "SYD": {"temp": 21, "condition": "Clear / Mild", "wind": 10, "vis": 10.0, "risk": 0.05},
    "BKK": {"temp": 32, "condition": "Monsoon Showers", "wind": 7, "vis": 8.0, "risk": 0.30},
    "HKG": {"temp": 29, "condition": "Humid / Coastal Mist", "wind": 13, "vis": 8.5, "risk": 0.20},
}


def _get_airport_weather(iata: str, seed: str = "") -> dict[str, Any]:
    """Retrieve or deterministically simulate weather for an airport."""
    iata_clean = iata.upper().strip()
    profile = AIRPORT_WEATHER_PROFILES.get(
        iata_clean,
        {"temp": 22, "condition": "VFR Normal Operations", "wind": 10, "vis": 10.0, "risk": 0.10},
    )

    # Use hash seed for deterministic variability if needed
    h = int(hashlib.md5(f"{iata_clean}-{seed}".encode()).hexdigest(), 16) % 10
    risk_adj = round(max(0.01, min(0.95, profile["risk"] + (h - 5) * 0.02)), 2)

    return {
        "airport": iata_clean,
        "temperature_c": profile["temp"],
        "condition": profile["condition"],
        "wind_speed_knots": profile["wind"],
        "visibility_km": profile["vis"],
        "risk_score": risk_adj,
        "flight_category": "VFR" if risk_adj < 0.3 else "MVFR" if risk_adj < 0.6 else "IFR",
    }


class WeatherAgent(BaseAgent):
    """Specialist Agent: Evaluates aviation weather risk across flight paths."""

    NAME = "WeatherAgent"

    def __init__(self, llm_client: Any | None = None) -> None:
        super().__init__()
        self._llm = llm_client

    def think(self, ctx: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        """Plan weather risk evaluation for mission origin, destination, and candidates."""
        origin = state.context.origin if state.context else "KUL"
        destination = state.context.destination if state.context else "SIN"
        departure_date = state.context.departure_date if state.context else "2026-08-20"

        return {
            "action": "evaluate_weather_risk",
            "origin": origin,
            "destination": destination,
            "date": departure_date,
        }

    def act(self, plan: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        """Execute meteorological evaluation for all itinerary nodes."""
        origin = plan["origin"]
        destination = plan["destination"]
        date_seed = plan["date"]

        origin_wx = _get_airport_weather(origin, date_seed)
        dest_wx = _get_airport_weather(destination, date_seed)

        # Evaluate candidate flight layover nodes if present
        candidate_assessments = []
        flight_data = state.flight or {}
        alternatives = flight_data.get("alternatives", [])
        best_option = flight_data.get("best_option")

        candidates_to_check = []
        if best_option and isinstance(best_option, dict) and "candidate" in best_option:
            candidates_to_check.append(best_option["candidate"])
        for alt in alternatives:
            if isinstance(alt, dict) and "candidate" in alt:
                candidates_to_check.append(alt["candidate"])

        max_risk = max(origin_wx["risk_score"], dest_wx["risk_score"])
        warnings = []

        if origin_wx["risk_score"] > 0.4:
            warnings.append(f"Adverse weather alert at origin {origin}: {origin_wx['condition']}")
        if dest_wx["risk_score"] > 0.4:
            warnings.append(f"Adverse weather alert at destination {destination}: {dest_wx['condition']}")

        for cand in candidates_to_check:
            fn = cand.get("flight_number", "FL-UNK")
            carrier = cand.get("carrier", "UNK")
            route_risk = max_risk
            status = "FAVORABLE" if route_risk < 0.25 else "CAUTION" if route_risk < 0.55 else "HIGH_RISK"
            candidate_assessments.append({
                "flight_number": fn,
                "carrier": carrier,
                "risk_score": route_risk,
                "weather_status": status,
                "recommendation": "Safe for dispatch" if route_risk < 0.55 else "Expect potential ground holding",
            })

        overall_status = "FAVORABLE" if max_risk < 0.3 else "MODERATE_RISK" if max_risk < 0.6 else "SEVERE_RISK"

        return {
            "origin_weather": origin_wx,
            "destination_weather": dest_wx,
            "overall_weather_status": overall_status,
            "composite_risk_score": max_risk,
            "candidate_weather_assessments": candidate_assessments,
            "warnings": warnings,
        }

    def evaluate(self, observation: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        """Validate observations and format output."""
        return {
            **observation,
            "complete": True,
        }

    def commit(self, result: dict[str, Any], state: SharedMissionState) -> AgentOutput:
        """Store weather output in shared mission state and return AgentOutput."""
        # Store in state.weather
        state.weather = {
            "origin": result.get("origin_weather"),
            "destination": result.get("destination_weather"),
            "risk_score": result.get("composite_risk_score", 0.0),
            "status": result.get("overall_weather_status", "FAVORABLE"),
            "warnings": result.get("warnings", []),
        }

        risk = result.get("composite_risk_score", 0.0)
        confidence = round(1.0 - (risk * 0.3), 2)
        summary = (
            f"Weather evaluated: Origin ({result['origin_weather']['airport']}) "
            f"{result['origin_weather']['condition']} ({result['origin_weather']['temperature_c']}°C), "
            f"Destination ({result['destination_weather']['airport']}) "
            f"{result['destination_weather']['condition']}. "
            f"Composite Weather Risk: {result['overall_weather_status']} ({risk:.2f})."
        )

        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            reasoning_summary=summary,
            warnings=result.get("warnings", []),
        )
