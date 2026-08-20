"""Regression tests for multi-segment itinerary normalization.

These tests verify that the normalizer correctly handles multi-segment
(connection) flights — a bug was found where only the first segment's
data was used, producing incorrect arrival_airport, arrival_time, and
duration_minutes for all connecting flights.

Bug report (TR467 KUL->NRT):
- Raw: KUL->SIN (TR467, 80min) + SIN->NRT (TR884, 420min)
- Before fix: arrival_airport=SIN, duration=80min  (WRONG)
- After fix:  arrival_airport=NRT, duration=1940min (CORRECT)
"""

from tros.adapters.flight.normalizer import (
    _compute_itinerary_duration,
    _normalize_offer,
    _parse_segment_datetime,
    normalize_search_response,
)


def _make_multi_segment_offer():
    """TR467 KUL->SIN->NRT — the real offer that exposed the bug."""
    return {
        "offer_id": "off_b1f3ce4dac83155396603d69",
        "currency": "USD",
        "total_price": 459.13,
        "passenger_prices": [{
            "passenger_type": "adult",
            "count": 1,
            "base_fare_per_passenger": 429.85,
            "tax_per_passenger": 29.28,
            "subtotal": 459.13,
        }],
        "segments": [
            {
                "departure_airport": "KUL",
                "arrival_airport": "SIN",
                "departure_time": "202608202245",
                "arrival_time": "202608210005",
                "carrier": "TR",
                "operating_carrier": None,
                "flight_number": "TR467",
                "duration_minutes": 80,
                "cabin_class": 1,
                "direction": "outbound",
            },
            {
                "departure_airport": "SIN",
                "arrival_airport": "NRT",
                "departure_time": "202608212305",
                "arrival_time": "202608220705",
                "carrier": "TR",
                "operating_carrier": None,
                "flight_number": "TR884",
                "duration_minutes": 420,
                "cabin_class": 1,
                "direction": "outbound",
            },
        ],
        "bookable": False,
        "price_status": "reference",
    }


def _make_single_segment_offer():
    """Direct flight KUL->NRT."""
    return {
        "offer_id": "off_direct_001",
        "currency": "USD",
        "total_price": 800.0,
        "passenger_prices": [{
            "passenger_type": "adult",
            "count": 1,
            "base_fare_per_passenger": 650.0,
            "tax_per_passenger": 150.0,
            "subtotal": 800.0,
        }],
        "segments": [
            {
                "departure_airport": "KUL",
                "arrival_airport": "NRT",
                "departure_time": "202608200930",
                "arrival_time": "202608201830",
                "carrier": "MH",
                "operating_carrier": None,
                "flight_number": "MH318",
                "duration_minutes": 420,
                "cabin_class": 1,
                "direction": "outbound",
            },
        ],
        "bookable": False,
        "price_status": "reference",
    }


class TestMultiSegmentNormalization:
    """Regression tests for the multi-segment itinerary bug."""

    def test_arrival_airport_is_final_destination(self):
        """arrival_airport must be the LAST segment's arrival_airport."""
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.arrival_airport == "NRT", (
            f"Expected NRT, got {candidate.arrival_airport}. "
            "Normalizer must use last segment's arrival_airport."
        )

    def test_departure_airport_is_first_origin(self):
        """departure_airport must be the FIRST segment's departure_airport."""
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.departure_airport == "KUL"

    def test_arrival_time_is_final_arrival(self):
        """arrival_time must be the LAST segment's arrival_time."""
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.arrival_time == "202608220705", (
            f"Expected 202608220705, got {candidate.arrival_time}. "
            "Normalizer must use last segment's arrival_time."
        )

    def test_departure_time_is_first_departure(self):
        """departure_time must be the FIRST segment's departure_time."""
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.departure_time == "202608202245"

    def test_duration_is_total_itinerary_time(self):
        """duration_minutes must cover first departure to last arrival
        (including layover)."""
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        # KUL depart Aug 20 22:45 -> NRT arrive Aug 22 07:05
        # = 32 hours 20 minutes = 1940 minutes
        assert candidate.duration_minutes == 1940, (
            f"Expected 1940 min, got {candidate.duration_minutes}. "
            "Duration must be total itinerary time, not first segment only."
        )

    def test_stops_count_for_connection(self):
        """A 2-segment itinerary has 1 stop."""
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.stops == 1

    def test_flight_number_is_primary_segment(self):
        """flight_number should be the longest (primary) segment."""
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        # TR884 (420 min) is longer than TR467 (80 min)
        assert candidate.flight_number == "TR884"

    def test_price_is_total_price(self):
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.price == 459.13

    def test_carrier_is_first_segment(self):
        offer = _make_multi_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.carrier == "TR"


class TestSingleSegmentNormalization:
    """Verify single-segment flights still work correctly after the fix."""

    def test_single_segment_unchanged(self):
        offer = _make_single_segment_offer()
        candidate = _normalize_offer(offer)
        assert candidate.departure_airport == "KUL"
        assert candidate.arrival_airport == "NRT"
        assert candidate.departure_time == "202608200930"
        assert candidate.arrival_time == "202608201830"
        assert candidate.duration_minutes == 540  # 9h00m
        assert candidate.stops == 0
        assert candidate.flight_number == "MH318"


class TestParseSegmentDatetime:
    def test_valid_datetime(self):
        dt = _parse_segment_datetime("202608202245")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 8
        assert dt.day == 20
        assert dt.hour == 22
        assert dt.minute == 45

    def test_short_string_returns_none(self):
        assert _parse_segment_datetime("1835") is None

    def test_empty_string_returns_none(self):
        assert _parse_segment_datetime("") is None


class TestComputeItineraryDuration:
    def test_multi_segment_duration(self):
        first = {"departure_time": "202608202245"}
        last = {"arrival_time": "202608220705"}
        assert _compute_itinerary_duration(first, last) == 1940

    def test_same_day_duration(self):
        first = {"departure_time": "202608200930"}
        last = {"arrival_time": "202608201830"}
        assert _compute_itinerary_duration(first, last) == 540

    def test_fallback_to_segment_durations(self):
        """When timestamps can't be parsed, fall back to sum of durations."""
        first = {"departure_time": "bad", "duration_minutes": 80}
        last = {"arrival_time": "bad", "duration_minutes": 420}
        result = _compute_itinerary_duration(first, last)
        assert result == 500

    def test_fallback_single_segment(self):
        """Single segment falls back to its own duration."""
        seg = {"departure_time": "bad", "arrival_time": "bad",
               "duration_minutes": 420}
        result = _compute_itinerary_duration(seg, seg)
        assert result == 420


class TestNormalizeSearchResponse:
    def test_full_response_normalization(self):
        """Normalize a complete search response with mixed itineraries."""
        raw = {
            "status": "success",
            "code": "FLIGHT_SEARCHED",
            "data": {
                "search_id": "srch_test",
                "offer_count": 2,
                "offers": [
                    _make_multi_segment_offer(),
                    _make_single_segment_offer(),
                ],
            },
        }
        candidates = normalize_search_response(raw)
        assert len(candidates) == 2

        # Multi-segment: arrival_airport must be NRT (last segment)
        multi = candidates[0]
        assert multi.arrival_airport == "NRT"
        assert multi.duration_minutes == 1940
        assert multi.stops == 1

        # Single-segment: unchanged
        single = candidates[1]
        assert single.arrival_airport == "NRT"
        assert single.stops == 0
