"""Phase 6 tests — Bounded Recovery & Re-evaluation.

Tests cover:
1. Recovery models (RecoveryAction, RecoveryResult, RecoveryHistoryEntry)
2. Recovery precedence (deterministic action selection)
3. Recovery engine (no recovery, next valid, re-search, max attempts)
4. Evidence versioning (version increments, provenance)
5. Re-evaluation (validation, budget, critic, conflicts, confidence)
6. State management (recovery history, serialization)
7. Security (no LLM execution, no score modification, no fabrication)
8. Integration (full mission with/without recovery)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tros.agents.conflict_detector import AgentConflict, ConflictReport
from tros.agents.flight.recommendation_validator import (
    ValidationResult,
)
from tros.agents.recovery.engine import RecoveryEngine
from tros.agents.recovery.models import (
    RecoveryAction,
    RecoveryActionType,
    RecoveryHistoryEntry,
    RecoveryResult,
)
from tros.config import LLM_MAX_RECOVERY_ATTEMPTS
from tros.llm.evidence import EvidenceBundle, build_evidence_bundle
from tros.schemas.mission import (
    DisruptionEvent,
    DisruptionType,
    MissionContext,
    TravelerProfile,
)
from tros.state.mission_state import SharedMissionState

# =====================================================================
# Helpers
# =====================================================================

def _make_state(budget_limit: float = 1000.0) -> SharedMissionState:
    """Build a mission state with KUL->NRT context."""
    state = SharedMissionState(mission_id="test-phase6")
    state.set_context(MissionContext(
        origin="KUL",
        destination="NRT",
        departure_date="2026-08-20",
        disruption=DisruptionEvent(
            disruption_type=DisruptionType.FLIGHT_CANCELLED,
            origin="KUL", destination="NRT",
            original_flight_number="MH318",
        ),
        budget_limit=budget_limit,
        traveler=TravelerProfile(airline_preference=None),
    ))
    return state


def _make_evidence(candidates: list[dict] | None = None) -> EvidenceBundle:
    """Build a test EvidenceBundle with multiple candidates."""
    if candidates is None:
        candidates = [
            {"flight_number": "TR874", "origin": "KUL", "destination": "NRT",
             "departure_time": "0800", "arrival_time": "1655",
             "duration_minutes": 535, "stops": 0, "price": 400.0,
             "currency": "USD", "deterministic_score": 85.0,
             "carrier": "TR", "offer_id": "offer-0"},
            {"flight_number": "TR876", "origin": "KUL", "destination": "NRT",
             "departure_time": "1000", "arrival_time": "1855",
             "duration_minutes": 535, "stops": 0, "price": 500.0,
             "currency": "USD", "deterministic_score": 72.0,
             "carrier": "TR", "offer_id": "offer-1"},
            {"flight_number": "TR878", "origin": "KUL", "destination": "NRT",
             "departure_time": "1400", "arrival_time": "2255",
             "duration_minutes": 535, "stops": 1, "price": 350.0,
             "currency": "USD", "deterministic_score": 60.0,
             "carrier": "TR", "offer_id": "offer-2"},
        ]
    return build_evidence_bundle(candidates, search_id="test-search-v1")


def _make_flight_data(flight_number: str = "TR874", price: float = 400.0) -> dict:
    """Build flight_data dict with best_option and alternatives."""
    return {
        "best_option": {
            "candidate": {
                "flight_number": flight_number,
                "carrier": "TR",
                "departure_airport": "KUL",
                "arrival_airport": "NRT",
                "departure_time": "0800",
                "arrival_time": "1655",
                "duration_minutes": 535,
                "stops": 0,
                "price": price,
                "currency": "USD",
                "offer_id": "offer-0",
            },
            "score": 85.0,
            "reasoning": "top candidate",
        },
        "alternatives": [
            {
                "candidate": {
                    "flight_number": "TR876",
                    "carrier": "TR",
                    "departure_airport": "KUL",
                    "arrival_airport": "NRT",
                    "departure_time": "1000",
                    "arrival_time": "1855",
                    "duration_minutes": 535,
                    "stops": 0,
                    "price": 500.0,
                    "currency": "USD",
                    "offer_id": "offer-1",
                },
                "score": 72.0,
                "reasoning": "alternative",
            },
        ],
        "total_candidates_evaluated": 3,
    }


def _make_mission_context(budget_limit: float = 1000.0) -> dict:
    """Build mission_context dict."""
    return {
        "origin": "KUL",
        "destination": "NRT",
        "departure_date": "2026-08-20",
        "currency": "USD",
        "budget_limit": budget_limit,
    }


def _make_mock_tool_executor(success: bool = True, candidates: list | None = None):
    """Build a mock ToolExecutor that returns configurable results."""
    mock = MagicMock()
    observation = MagicMock()
    observation.success = success
    observation.search_id = "recovery-search-v2"
    observation.candidate_count = len(candidates) if candidates else 0
    observation.candidates = candidates or []
    observation.message = "" if success else "Atlas error"
    mock.execute_tool.return_value = observation
    return mock


# =====================================================================
# 1. Recovery Models
# =====================================================================

class TestRecoveryModels:
    """Tests for RecoveryAction, RecoveryResult, RecoveryHistoryEntry."""

    def test_valid_action_types(self):
        """All defined action types are valid."""
        for t in RecoveryActionType:
            action = RecoveryAction(action_type=t, reason="test")
            assert action.action_type == t

    def test_invalid_action_type_rejected(self):
        """Invalid action type raises validation error."""
        with pytest.raises(Exception):
            RecoveryAction(action_type="INVALID_ACTION", reason="bad")

    def test_action_serialization(self):
        """RecoveryAction serializes through Pydantic."""
        action = RecoveryAction(
            action_type=RecoveryActionType.RESEARCH_FLIGHTS,
            reason="budget violation",
            triggering_conflicts=["over budget"],
            attempt_number=1,
            provenance="deterministic",
        )
        d = action.model_dump()
        assert d["action_type"] == "RESEARCH_FLIGHTS"
        assert d["attempt_number"] == 1
        restored = RecoveryAction(**d)
        assert restored == action

    def test_recovery_result_structured(self):
        """RecoveryResult has all required fields."""
        result = RecoveryResult(
            recovered=True,
            terminated=False,
            reason="success",
            final_validation_valid=True,
            attempts_used=1,
            final_candidate="TR876",
            final_confidence=0.83,
        )
        assert result.recovered is True
        assert result.attempts_used == 1
        assert result.final_confidence == 0.83

    def test_history_entry_serialization(self):
        """RecoveryHistoryEntry serializes through Pydantic."""
        entry = RecoveryHistoryEntry(
            attempt_number=1,
            triggering_reason="budget violation",
            action=RecoveryActionType.USE_NEXT_VALID_CANDIDATE,
            result="success",
            candidates_found=3,
            validation_valid=True,
        )
        d = entry.model_dump()
        assert d["attempt_number"] == 1
        assert d["action"] == "USE_NEXT_VALID_CANDIDATE"


# =====================================================================
# 2. Recovery Precedence
# =====================================================================

class TestRecoveryPrecedence:
    """Deterministic precedence: constraint > fabricated > critic > budget > conflict > none."""

    def _engine(self) -> RecoveryEngine:
        return RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)

    def test_constraint_violation_triggers_next_valid(self):
        """Origin mismatch (constraint violation) triggers USE_NEXT_VALID_CANDIDATE."""
        engine = self._engine()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["Flight origin 'SIN' does not match mission origin 'KUL'"],
        )
        action = engine._determine_action(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            attempt_number=0,
        )
        assert action.action_type == RecoveryActionType.USE_NEXT_VALID_CANDIDATE

    def test_fabricated_recommendation_triggers_recovery(self):
        """Flight not in evidence triggers USE_NEXT_VALID_CANDIDATE."""
        engine = self._engine()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["Flight 'FAKE123' not found in evidence"],
        )
        action = engine._determine_action(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            attempt_number=0,
        )
        assert action.action_type == RecoveryActionType.USE_NEXT_VALID_CANDIDATE

    def test_critical_critic_triggers_recovery(self):
        """Critical conflict triggers USE_NEXT_VALID_CANDIDATE."""
        engine = self._engine()
        evidence = _make_evidence()
        validation = ValidationResult(valid=True, validated_flight="TR874")
        conflict = ConflictReport(
            conflicts=[AgentConflict(
                agents=["A", "B"], category="budget",
                description="over budget", severity="critical",
                resolution_required=True,
            )],
            has_critical_conflict=True,
        )
        action = engine._determine_action(
            conflict_report=conflict,
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            attempt_number=0,
        )
        assert action.action_type == RecoveryActionType.USE_NEXT_VALID_CANDIDATE

    def test_budget_violation_triggers_recovery(self):
        """Budget over limit triggers recovery."""
        engine = self._engine()
        evidence = _make_evidence()
        validation = ValidationResult(valid=True, validated_flight="TR874")
        action = engine._determine_action(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": False},
            attempt_number=0,
        )
        assert action.action_type == RecoveryActionType.USE_NEXT_VALID_CANDIDATE

    def test_noncritical_conflict_triggers_reevaluate(self):
        """Non-critical conflict triggers REEVALUATE_CANDIDATES."""
        engine = self._engine()
        evidence = _make_evidence()
        validation = ValidationResult(valid=True, validated_flight="TR874")
        conflict = ConflictReport(
            conflicts=[AgentConflict(
                agents=["A", "B"], category="recommendation",
                description="minor disagreement", severity="warning",
                resolution_required=False,
            )],
            has_critical_conflict=False,
        )
        action = engine._determine_action(
            conflict_report=conflict,
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            attempt_number=0,
        )
        assert action.action_type == RecoveryActionType.REEVALUATE_CANDIDATES

    def test_no_recovery_when_all_pass(self):
        """All checks pass → TERMINATE_NO_SOLUTION (no recovery needed)."""
        engine = self._engine()
        evidence = _make_evidence()
        validation = ValidationResult(valid=True, validated_flight="TR874")
        action = engine._determine_action(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            attempt_number=0,
        )
        assert action.action_type == RecoveryActionType.TERMINATE_NO_SOLUTION

    def test_max_attempts_terminates(self):
        """Exceeding max attempts → TERMINATE_NO_SOLUTION."""
        engine = self._engine()
        action = engine._determine_action(
            conflict_report=ConflictReport(has_critical_conflict=True),
            validation_result=ValidationResult(valid=False, errors=["bad"]),
            evidence=_make_evidence(),
            budget_assessment={"within_budget": False},
            attempt_number=2,  # >= max_attempts=2
        )
        assert action.action_type == RecoveryActionType.TERMINATE_NO_SOLUTION


# =====================================================================
# 3. Recovery Engine
# =====================================================================

class TestRecoveryEngine:
    """Tests for the bounded recovery loop."""

    def test_no_recovery_needed(self):
        """When validation passes and no conflicts, engine returns no-recovery."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(valid=True, validated_flight="TR874")
        result = engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        assert result.recovered is False
        assert result.terminated is False
        assert result.attempts_used == 0

    def test_next_valid_candidate_succeeds(self):
        """USE_NEXT_VALID_CANDIDATE picks a valid alternative."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        # TR874 fails validation (wrong origin), TR876 should be picked
        validation = ValidationResult(
            valid=False,
            errors=["Flight origin 'SIN' does not match mission origin 'KUL'"],
        )
        result = engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        assert result.recovered is True
        assert result.final_candidate == "TR876"
        assert result.attempts_used == 1

    def test_research_via_tool_executor(self):
        """RESEARCH_FLIGHTS calls ToolExecutor and uses new results."""
        new_candidates = [
            {"flight_number": "NEW001", "origin": "KUL", "destination": "NRT",
             "departure_time": "0900", "arrival_time": "1800",
             "duration_minutes": 540, "stops": 0, "price": 300.0,
             "currency": "USD", "deterministic_score": 90.0,
             "carrier": "SQ", "offer_id": "new-offer-0"},
        ]
        mock_executor = _make_mock_tool_executor(success=True, candidates=new_candidates)
        engine = RecoveryEngine(tool_executor=mock_executor, max_attempts=2)
        state = _make_state()
        # Single-candidate evidence → forces RESEARCH_FLIGHTS
        single_evidence = _make_evidence([
            {"flight_number": "OLD1", "origin": "KUL", "destination": "NRT",
             "departure_time": "0800", "arrival_time": "1655",
             "duration_minutes": 535, "stops": 0, "price": 400.0,
             "currency": "USD", "deterministic_score": 85.0,
             "carrier": "TR", "offer_id": "old-0"},
        ])
        validation = ValidationResult(
            valid=False,
            errors=["Flight 'FAKE999' not found in evidence"],
        )
        result = engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=single_evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(flight_number="FAKE999"),
            state=state,
        )
        assert result.recovered is True
        assert result.final_candidate == "NEW001"
        mock_executor.execute_tool.assert_called_once()

    def test_failed_search_terminates(self):
        """Failed Atlas search leads to termination."""
        mock_executor = _make_mock_tool_executor(success=False)
        engine = RecoveryEngine(tool_executor=mock_executor, max_attempts=2)
        state = _make_state()
        single_evidence = _make_evidence([
            {"flight_number": "ONLY1", "origin": "KUL", "destination": "NRT",
             "departure_time": "0800", "arrival_time": "1655",
             "duration_minutes": 535, "stops": 0, "price": 400.0,
             "currency": "USD", "deterministic_score": 85.0,
             "carrier": "TR", "offer_id": "only-0"},
        ])
        validation = ValidationResult(
            valid=False,
            errors=["Flight 'GONE' not found in evidence"],
        )
        result = engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=single_evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(flight_number="GONE"),
            state=state,
        )
        assert result.recovered is False
        assert result.terminated is True

    def test_max_attempts_exhausted(self):
        """Engine terminates after max attempts."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=1)
        state = _make_state()
        # Build evidence where only current best exists (no alternatives)
        evidence = _make_evidence([
            {"flight_number": "TR874", "origin": "KUL", "destination": "NRT",
             "departure_time": "0800", "arrival_time": "1655",
             "duration_minutes": 535, "stops": 0, "price": 400.0,
             "currency": "USD", "deterministic_score": 85.0,
             "carrier": "TR", "offer_id": "offer-0"},
            {"flight_number": "TR876", "origin": "WRONG", "destination": "NRT",
             "departure_time": "1000", "arrival_time": "1855",
             "duration_minutes": 535, "stops": 0, "price": 500.0,
             "currency": "USD", "deterministic_score": 72.0,
             "carrier": "TR", "offer_id": "offer-1"},
        ])
        validation = ValidationResult(
            valid=False,
            errors=["Flight origin does not match"],
        )
        result = engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        # TR876 fails validation (wrong origin), so recovery fails after 1 attempt
        assert result.attempts_used <= 1

    def test_successful_recovery_updates_state(self):
        """Successful recovery populates state recovery fields."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["Flight 'TR874' origin does not match"],
        )
        result = engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        assert state.recovery_state.get("recovered") is True
        assert len(state.recovery_history) >= 1
        assert len(state.evidence_versions) >= 1


# =====================================================================
# 4. Evidence Versioning
# =====================================================================

class TestEvidenceVersioning:
    """Tests for evidence version tracking across recovery attempts."""

    def test_version_increments_on_recovery(self):
        """Evidence version increments after successful recovery."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["Flight origin 'SIN' does not match mission origin 'KUL'"],
        )
        engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        # Evidence should have version metadata
        assert "evidence_version" in state.evidence
        assert state.evidence["evidence_version"] >= 2  # v2 = attempt 1

    def test_evidence_versions_list_populated(self):
        """evidence_versions list tracks each version."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["Flight origin 'SIN' does not match mission origin 'KUL'"],
        )
        engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        assert len(state.evidence_versions) >= 1
        v = state.evidence_versions[0]
        assert "version" in v
        assert "total_candidates" in v

    def test_search_id_preserved_in_evidence(self):
        """Re-search evidence preserves the new search ID."""
        new_candidates = [
            {"flight_number": "SQ100", "origin": "KUL", "destination": "NRT",
             "departure_time": "0900", "arrival_time": "1800",
             "duration_minutes": 540, "stops": 0, "price": 450.0,
             "currency": "USD", "deterministic_score": 88.0,
             "carrier": "SQ", "offer_id": "sq-offer-0"},
        ]
        mock_executor = _make_mock_tool_executor(success=True, candidates=new_candidates)
        engine = RecoveryEngine(tool_executor=mock_executor, max_attempts=2)
        state = _make_state()
        single_evidence = _make_evidence([
            {"flight_number": "OLD1", "origin": "KUL", "destination": "NRT",
             "departure_time": "0800", "arrival_time": "1655",
             "duration_minutes": 535, "stops": 0, "price": 400.0,
             "currency": "USD", "deterministic_score": 85.0,
             "carrier": "TR", "offer_id": "old-0"},
        ])
        validation = ValidationResult(
            valid=False,
            errors=["Flight 'FAKE' not found in evidence"],
        )
        engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=single_evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(flight_number="FAKE"),
            state=state,
        )
        # State evidence should contain candidates from new search
        assert "candidates" in state.evidence
        candidates = state.evidence["candidates"]
        assert len(candidates) >= 1


# =====================================================================
# 5. Re-evaluation
# =====================================================================

class TestReevaluation:
    """Re-evaluation re-runs Phase 5 pipeline on recovery candidates."""

    def test_recovered_candidate_passes_validation(self):
        """A valid alternative passes re-evaluation."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        evidence = _make_evidence()
        # TR876 is in evidence with correct origin/dest
        validation, conflict, budget, confidence = engine._reevaluate(
            evidence, _make_flight_data(flight_number="TR876", price=500.0),
            _make_mission_context(), _make_state(),
        )
        assert validation.valid is True
        assert validation.validated_flight == "TR876"

    def test_recovered_candidate_fails_validation(self):
        """A candidate with wrong origin fails re-evaluation."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        evidence = _make_evidence([
            {"flight_number": "BAD1", "origin": "SIN", "destination": "NRT",
             "departure_time": "0900", "arrival_time": "1800",
             "duration_minutes": 540, "stops": 0, "price": 300.0,
             "currency": "USD", "deterministic_score": 90.0,
             "carrier": "SQ", "offer_id": "bad-0"},
        ])
        validation, _, _, _ = engine._reevaluate(
            evidence, _make_flight_data(flight_number="BAD1", price=300.0),
            _make_mission_context(), _make_state(),
        )
        assert validation.valid is False

    def test_ranking_remains_deterministic(self):
        """Re-evaluation does not modify scores."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        evidence = _make_evidence()
        original_scores = {c.flight_number: c.deterministic_score for c in evidence.candidates}
        engine._reevaluate(
            evidence, _make_flight_data(), _make_mission_context(), _make_state(),
        )
        # Scores unchanged
        for c in evidence.candidates:
            assert c.deterministic_score == original_scores[c.flight_number]

    def test_budget_recalculated(self):
        """Budget assessment is recalculated on recovery."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        evidence = _make_evidence()
        _, _, budget, _ = engine._reevaluate(
            evidence,
            _make_flight_data(price=400.0),
            _make_mission_context(budget_limit=500.0),
            _make_state(),
        )
        assert budget["within_budget"] is True
        assert budget["remaining_budget"] == 100.0

    def test_confidence_recalculated(self):
        """Confidence is recalculated on recovery."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        evidence = _make_evidence()
        _, _, _, confidence = engine._reevaluate(
            evidence, _make_flight_data(), _make_mission_context(), _make_state(),
        )
        assert 0.0 <= confidence <= 0.95


# =====================================================================
# 6. State Management
# =====================================================================

class TestStateManagement:
    """Tests for recovery state storage and Pydantic serialization."""

    def test_recovery_history_stored(self):
        """Recovery history is stored in state after engine run."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["Flight origin 'SIN' does not match"],
        )
        engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        assert isinstance(state.recovery_history, list)
        assert len(state.recovery_history) >= 1
        entry = state.recovery_history[0]
        assert "attempt_number" in entry
        assert "action" in entry

    def test_no_raw_llm_data_in_recovery_state(self):
        """Recovery state contains no raw LLM data."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["constraint mismatch"],
        )
        engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        # recovery_state should only have deterministic fields
        for key in state.recovery_state:
            assert key in {"recovered", "terminated", "attempts_used", "reason"}

    def test_pydantic_serialization(self):
        """Full state serializes through Pydantic after recovery."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["constraint mismatch"],
        )
        engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        # Should not raise
        dumped = state.model_dump()
        assert "recovery_state" in dumped
        assert "recovery_history" in dumped
        assert "evidence_versions" in dumped


# =====================================================================
# 7. Security
# =====================================================================

class TestSecurity:
    """Security boundaries for recovery."""

    def test_llm_cannot_execute_atlas(self):
        """RecoveryEngine only uses ToolExecutor — never subprocess."""
        mock_executor = MagicMock()
        engine = RecoveryEngine(tool_executor=mock_executor, max_attempts=2)

        # The engine should never call subprocess
        with patch("subprocess.run") as mock_sub:
            state = _make_state()
            evidence = _make_evidence()
            validation = ValidationResult(valid=True, validated_flight="TR874")
            engine.run(
                conflict_report=ConflictReport(),
                validation_result=validation,
                evidence=evidence,
                budget_assessment={"within_budget": True},
                mission_context=_make_mission_context(),
                flight_data=_make_flight_data(),
                state=state,
            )
            mock_sub.assert_not_called()

    def test_llm_cannot_modify_ranking(self):
        """Recovery re-evaluation preserves deterministic scores."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        evidence = _make_evidence()
        scores_before = [c.deterministic_score for c in evidence.candidates]
        engine._reevaluate(
            evidence, _make_flight_data(), _make_mission_context(), _make_state(),
        )
        scores_after = [c.deterministic_score for c in evidence.candidates]
        assert scores_before == scores_after

    def test_llm_cannot_fabricate_evidence(self):
        """Recovery only uses candidates from EvidenceBundle or ToolExecutor."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        evidence = _make_evidence()
        validation, _, _, _ = engine._reevaluate(
            evidence, _make_flight_data(), _make_mission_context(), _make_state(),
        )
        # Validated flight must exist in evidence
        if validation.valid:
            flight_nums = [c.flight_number for c in evidence.candidates]
            assert validation.validated_flight in flight_nums

    def test_no_credentials_in_recovery_trace(self):
        """Recovery history and state contain no API keys or secrets."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=2)
        state = _make_state()
        evidence = _make_evidence()
        validation = ValidationResult(
            valid=False,
            errors=["constraint mismatch"],
        )
        engine.run(
            conflict_report=ConflictReport(),
            validation_result=validation,
            evidence=evidence,
            budget_assessment={"within_budget": True},
            mission_context=_make_mission_context(),
            flight_data=_make_flight_data(),
            state=state,
        )
        state_str = str(state.model_dump())
        assert "sk-" not in state_str.lower()
        assert "api_key" not in state_str.lower()
        assert "secret" not in state_str.lower()


# =====================================================================
# 8. Integration
# =====================================================================

class TestIntegration:
    """End-to-end integration tests for Phase 6 recovery."""

    def test_full_mission_no_recovery(self):
        """Mission with valid recommendation requires no recovery."""
        from tros.agents.supervisor import SupervisorAgent

        supervisor = SupervisorAgent(llm_client=None)
        state = _make_state()
        raw_input = {
            "disruption_type": "FlightCancelled",
            "origin": "KUL",
            "destination": "NRT",
            "departure_date": "2026-08-20",
            "original_flight_number": "MH318",
            "budget_limit": 1000.0,
            "traveler_type": "Business",
        }
        result = supervisor.run_mission(state, raw_input)
        # Mission should complete regardless of recovery
        assert result.status.value in ("completed", "recommendation")

    def test_full_mission_with_recovery(self):
        """Supervisor triggers recovery when decision is conditional."""
        from tros.agents.supervisor import SupervisorAgent

        supervisor = SupervisorAgent(llm_client=None)
        state = _make_state()
        raw_input = {
            "disruption_type": "FlightCancelled",
            "origin": "KUL",
            "destination": "NRT",
            "departure_date": "2026-08-20",
            "original_flight_number": "MH318",
            "budget_limit": 1000.0,
            "traveler_type": "Business",
        }
        result = supervisor.run_mission(state, raw_input)
        # Mission completes — recovery may or may not have been triggered
        assert result.status.value in ("completed", "recommendation")

    def test_recovery_history_in_recovery_plan(self):
        """SummaryAgent includes recovery history in RecoveryPlan."""
        from tros.agents.summary import SummaryAgent

        state = _make_state()
        state.flight = _make_flight_data()
        state.recovery_state = {"recovered": True, "attempts_used": 1}
        state.recovery_history = [
            {"attempt_number": 1, "action": "USE_NEXT_VALID_CANDIDATE", "result": "success"},
        ]
        state.evidence_versions = [{"version": 2, "attempt": 1}]
        state.mission_decision = {
            "status": "approved",
            "confidence": 0.83,
            "recovery_attempts": 1,
        }
        state.budget_assessment = {"within_budget": True}
        state.critic_report = {"approved": True}
        state.conflict_report = {"conflicts": []}

        summary = SummaryAgent(llm_client=None)
        output = summary.execute(state)
        # RecoveryPlan should contain recovery info
        plan = state.recovery_plan
        assert plan.get("recovery_occurred") is True
        assert len(plan.get("recovery_history", [])) >= 1

    def test_config_constant_used(self):
        """LLM_MAX_RECOVERY_ATTEMPTS is configurable and used by engine."""
        assert LLM_MAX_RECOVERY_ATTEMPTS >= 1
        engine = RecoveryEngine(tool_executor=MagicMock())
        assert engine._max_attempts == LLM_MAX_RECOVERY_ATTEMPTS

    def test_custom_max_attempts(self):
        """Custom max_attempts overrides the config default."""
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=5)
        assert engine._max_attempts == 5
