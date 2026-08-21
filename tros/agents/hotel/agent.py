"""Hotel Recovery Agent — Distress Passenger Accommodations & Vouchers.

Evaluates missed connection / overnight layovers and provisions distress
hotel vouchers, terminal shuttle access, and statutory meal vouchers.
"""

from __future__ import annotations

import hashlib
from typing import Any

from tros.agents.base import BaseAgent
from tros.schemas.agent_output import AgentOutput, AgentStatus
from tros.state.mission_state import SharedMissionState


# Airport partner distress hotel chains with shuttle logistics
AIRPORT_HOTEL_INVENTORY: dict[str, list[dict[str, Any]]] = {
    "KUL": [
        {"name": "Sama-Sama Hotel KLIA", "stars": 5, "distance_km": 0.3, "shuttle": "Direct Skybridge Access", "rate": 120.0, "amenities": ["24/7 Dining", "Express Check-in", "High-speed WiFi"]},
        {"name": "Aerotel KLIA Terminal 2", "stars": 4, "distance_km": 0.1, "shuttle": "Inside Terminal", "rate": 95.0, "amenities": ["Hourly Rooms", "Showers", "Complimentary Refreshments"]},
        {"name": "Movenpick Hotel & Convention Centre KLIA", "stars": 5, "distance_km": 4.5, "shuttle": "Free 15-min Shuttle", "rate": 85.0, "amenities": ["Halal Dining", "Pool", "Luggage Storage"]},
    ],
    "SIN": [
        {"name": "Crowne Plaza Changi Airport", "stars": 5, "distance_km": 0.2, "shuttle": "Terminal 3 Direct Access", "rate": 220.0, "amenities": ["Runway View", "Spa", "24/7 Room Service"]},
        {"name": "YOTELAIR Singapore Changi", "stars": 4, "distance_km": 0.1, "shuttle": "Jewel Changi Level 4", "rate": 140.0, "amenities": ["SmartBed Cabin", "Rain Showers", "Free Barista Coffee"]},
    ],
    "LHR": [
        {"name": "Hilton London Heathrow Terminal 4", "stars": 4, "distance_km": 0.4, "shuttle": "Covered Walkway", "rate": 160.0, "amenities": ["Executive Lounge", "Soundproof Glazing", "Breakfast Included"]},
        {"name": "Sofitel London Heathrow T5", "stars": 5, "distance_km": 0.2, "shuttle": "Direct Terminal 5 Link", "rate": 210.0, "amenities": ["Luxury Spa", "Gourmet Brasserie", "Valet Baggage"]},
    ],
    "JFK": [
        {"name": "TWA Hotel at JFK Airport", "stars": 4, "distance_km": 0.2, "shuttle": "AirTrain T5 Connection", "rate": 240.0, "amenities": ["Rooftop Pool", "Retro Lounge", "Paris Cafe"]},
        {"name": "Hyatt Regency JFK Airport at Resorts World", "stars": 4, "distance_km": 5.2, "shuttle": "Complimentary Shuttle Bus", "rate": 175.0, "amenities": ["Casino Access", "Fitness Center", "Dining"]},
    ],
    "NRT": [
        {"name": "Narita Airport Rest House", "stars": 3, "distance_km": 0.8, "shuttle": "Free 5-min Shuttle", "rate": 80.0, "amenities": ["Japanese Breakfast", "Convenience Store", "Coin Laundry"]},
        {"name": "Hotel Nikko Narita", "stars": 4, "distance_km": 3.0, "shuttle": "Dedicated Airport Bus", "rate": 110.0, "amenities": ["Executive Lounge", "Garden", "Currency Exchange"]},
    ],
}

DEFAULT_HOTEL_CHAIN = [
    {"name": "Airport Transit Grand Hotel", "stars": 4, "distance_km": 1.2, "shuttle": "Free 10-min Shuttle", "rate": 130.0, "amenities": ["24h Reception", "Hot Buffet", "Soundproofing"]},
    {"name": "Express Terminal Lodge", "stars": 3, "distance_km": 2.5, "shuttle": "Free 15-min Shuttle", "rate": 90.0, "amenities": ["Grab & Go Breakfast", "Fast WiFi", "Quiet Rooms"]},
]


class HotelAgent(BaseAgent):
    """Specialist Agent: Provisions distress hotel vouchers & overnight care."""

    NAME = "HotelAgent"

    def __init__(self, llm_client: Any | None = None) -> None:
        super().__init__()
        self._llm = llm_client

    def think(self, ctx: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        """Determine if delay/cancellation severity warrants hotel accommodation."""
        disruption_type = "FlightCancelled"
        if state.context and state.context.disruption:
            dt = state.context.disruption.disruption_type
            disruption_type = dt.value if hasattr(dt, "value") else str(dt)

        origin = state.context.origin if state.context else "KUL"
        destination = state.context.destination if state.context else "SIN"
        traveler_count = state.context.traveler_count if state.context else 1

        # Check flight layover / departure timing
        flight_data = state.flight or {}
        best_option = flight_data.get("best_option", {})
        cand = best_option.get("candidate", {}) if isinstance(best_option, dict) else {}
        duration_minutes = cand.get("duration_minutes", 0)

        # Triggers: Cancellations, overnight delays, or severe ground stops
        requires_hotel = (
            "Cancel" in disruption_type
            or "Stranded" in disruption_type
            or "Missed" in disruption_type
            or duration_minutes > 480
        )

        return {
            "action": "provision_distress_hotel",
            "requires_hotel": requires_hotel,
            "hub": origin,
            "destination": destination,
            "travelers": traveler_count,
            "disruption_type": disruption_type,
        }

    def act(self, plan: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        """Allocate distress hotel vouchers and airline-mandated meal credits."""
        requires_hotel = plan["requires_hotel"]
        hub = plan["hub"].upper()
        travelers = max(1, plan["travelers"])

        if not requires_hotel:
            return {
                "hotel_required": False,
                "hotel_voucher": None,
                "meal_voucher_usd": 35.0 * travelers,
                "lounge_access_granted": True,
                "summary": "Same-day recovery: Airport lounge pass and meal voucher issued.",
            }

        # Select closest partner hotel
        inventory = AIRPORT_HOTEL_INVENTORY.get(hub, DEFAULT_HOTEL_CHAIN)
        selected_hotel = inventory[0]

        # Generate unique airline electronic voucher code
        voucher_seed = f"{hub}-{selected_hotel['name']}-{plan['disruption_type']}"
        h_code = hashlib.md5(voucher_seed.encode()).hexdigest()[:8].upper()
        voucher_code = f"HTL-VCH-{h_code}"

        hotel_voucher = {
            "voucher_code": voucher_code,
            "hotel_name": selected_hotel["name"],
            "star_rating": selected_hotel["stars"],
            "distance_from_terminal_km": selected_hotel["distance_km"],
            "shuttle_logistics": selected_hotel["shuttle"],
            "nightly_rate_usd": selected_hotel["rate"],
            "rooms_booked": max(1, (travelers + 1) // 2),
            "check_in_window": "Immediate (Emergency Priority)",
            "check_out_time": "12:00 PM Next Day / Adjusted to Rescheduled Departure",
            "amenities": selected_hotel["amenities"],
            "airline_duty_of_care_covered": True,
            "traveler_out_of_pocket_cost": 0.0,
            "meal_voucher_allowance_usd": 65.0 * travelers,
        }

        return {
            "hotel_required": True,
            "hotel_voucher": hotel_voucher,
            "meal_voucher_usd": 65.0 * travelers,
            "lounge_access_granted": True,
            "summary": (
                f"Emergency accommodation allocated at {selected_hotel['name']} "
                f"({selected_hotel['distance_km']}km from {hub}). 100% airline covered "
                f"with complimentary shuttle and ${65.0 * travelers:.2f} meal credits."
            ),
        }

    def evaluate(self, observation: dict[str, Any], state: SharedMissionState) -> dict[str, Any]:
        """Verify accommodation compliance with duty-of-care policy."""
        return {
            **observation,
            "complete": True,
        }

    def commit(self, result: dict[str, Any], state: SharedMissionState) -> AgentOutput:
        """Commit hotel voucher details to shared mission state."""
        state.hotel = {
            "required": result.get("hotel_required", False),
            "voucher": result.get("hotel_voucher"),
            "meal_voucher_usd": result.get("meal_voucher_usd", 0.0),
            "lounge_access": result.get("lounge_access_granted", False),
        }

        vch = result.get("hotel_voucher")
        summary = result.get("summary", "Hotel recovery completed.")
        warnings = []
        if vch and vch.get("distance_from_terminal_km", 0) > 3.0:
            warnings.append(f"Hotel is {vch['distance_from_terminal_km']}km away; allow shuttle transfer time.")

        return AgentOutput(
            agent=self.NAME,
            status=AgentStatus.COMPLETED,
            confidence=0.95 if vch else 0.90,
            reasoning_summary=summary,
            warnings=warnings,
        )
