"""Tests for flight ranking logic."""

from tros.agents.flight.ranking import _parse_time_to_minutes, rank_candidates
from tros.schemas.flight import FlightCandidate


def _make_candidate(
    flight_number: str = "SQ318",
    price: float = 420.0,
    departure_time: str = "0930",
    arrival_time: str = "1835",
    duration_minutes: int = 545,
    stops: int = 0,
    carrier: str = "SQ",
) -> FlightCandidate:
    return FlightCandidate(
        offer_id=f"off_{flight_number}",
        flight_number=flight_number,
        carrier=carrier,
        departure_airport="KUL",
        arrival_airport="NRT",
        departure_time=departure_time,
        arrival_time=arrival_time,
        duration_minutes=duration_minutes,
        stops=stops,
        price=price,
    )


class TestParseTime:
    def test_standard_time(self):
        assert _parse_time_to_minutes("1835") == 18 * 60 + 35

    def test_datetime_format(self):
        # Full datetime returns epoch-based minutes (preserves cross-day order)
        result = _parse_time_to_minutes("202608201835")
        assert result > 0
        # Later on the same day is still greater
        assert _parse_time_to_minutes("202608202000") > result

    def test_datetime_cross_day(self):
        # Aug 21 08:00 should rank later than Aug 20 22:00
        aug20_late = _parse_time_to_minutes("202608202200")
        aug21_early = _parse_time_to_minutes("202608210800")
        assert aug21_early > aug20_late

    def test_midnight(self):
        assert _parse_time_to_minutes("0000") == 0

    def test_empty(self):
        assert _parse_time_to_minutes("") == 0


class TestRanking:
    def test_empty_candidates(self):
        assert rank_candidates([]) == []

    def test_single_candidate(self):
        candidates = [_make_candidate()]
        ranked = rank_candidates(candidates)
        assert len(ranked) == 1
        # Without preferred airline, preference_score=0 → composite < 100
        assert ranked[0].arrival_score == 100.0
        assert ranked[0].cost_score == 100.0
        assert ranked[0].stops_score == 100.0

    def test_cheapest_scores_higher(self):
        cheap = _make_candidate(flight_number="AK1", price=100.0)
        expensive = _make_candidate(flight_number="SQ1", price=800.0)
        ranked = rank_candidates([cheap, expensive])
        # Cheapest should have higher cost_score
        cheap_ranked = next(r for r in ranked if r.candidate.flight_number == "AK1")
        exp_ranked = next(r for r in ranked if r.candidate.flight_number == "SQ1")
        assert cheap_ranked.cost_score > exp_ranked.cost_score

    def test_earlier_arrival_scores_higher(self):
        early = _make_candidate(flight_number="E1", arrival_time="0800")
        late = _make_candidate(flight_number="L1", arrival_time="2200")
        ranked = rank_candidates([early, late])
        early_ranked = next(r for r in ranked if r.candidate.flight_number == "E1")
        late_ranked = next(r for r in ranked if r.candidate.flight_number == "L1")
        assert early_ranked.arrival_score > late_ranked.arrival_score

    def test_direct_flight_scores_higher(self):
        direct = _make_candidate(flight_number="D1", stops=0)
        one_stop = _make_candidate(flight_number="S1", stops=1)
        ranked = rank_candidates([direct, one_stop])
        direct_ranked = next(r for r in ranked if r.candidate.flight_number == "D1")
        stop_ranked = next(r for r in ranked if r.candidate.flight_number == "S1")
        assert direct_ranked.stops_score > stop_ranked.stops_score

    def test_preferred_airline_bonus(self):
        preferred = _make_candidate(flight_number="MH1", carrier="MH")
        other = _make_candidate(flight_number="AK1", carrier="AK")
        ranked = rank_candidates([preferred, other], preferred_airline="MH")
        mh_ranked = next(r for r in ranked if r.candidate.flight_number == "MH1")
        assert mh_ranked.preference_score == 100.0

    def test_sorted_by_score(self):
        candidates = [
            _make_candidate(flight_number="A", price=500, arrival_time="2000", stops=1),
            _make_candidate(flight_number="B", price=100, arrival_time="0800", stops=0),
            _make_candidate(flight_number="C", price=300, arrival_time="1200", stops=0),
        ]
        ranked = rank_candidates(candidates)
        scores = [r.score for r in ranked]
        assert scores == sorted(scores, reverse=True)
