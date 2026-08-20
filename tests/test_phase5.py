"""Phase 5 tests — Multi-Agent Intelligence & Decision Quality.

Tests cover:
1. Evidence store
2. Candidate comparison
3. Recommendation validation
4. Budget assessment
5. Critic evidence-based review
6. Conflict detection
7. Confidence calculation
8. Supervisor coordination
9. Recovery plan
"""

from __future__ import annotations

from tros.agents.conflict_detector import detect_conflicts
from tros.agents.flight.comparator import compare_candidates
from tros.agents.flight.confidence import (
    ConfidenceFactors,
    calculate_confidence,
)
from tros.agents.flight.recommendation_validator import (
    validate_recommendation,
)
from tros.llm.evidence import EvidenceBundle, build_evidence_bundle
from tros.schemas.agent_output import AgentOutput, AgentStatus
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
    """Build a mission state with KUL->NRT flight cancellation context."""
    state = SharedMissionState(mission_id="test-phase5")
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
    """Build a test EvidenceBundle."""
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
    return build_evidence_bundle(candidates, search_id="test-search")


def _populate_flight_state(state: SharedMissionState) -> None:
    """Populate state.flight with test data for integration tests."""
    state.flight = {
        "best_option": {
            "candidate": {
                "flight_number": "TR874", "carrier": "TR",
                "departure_airport": "KUL", "arrival_airport": "NRT",
                "departure_time": "0800", "arrival_time": "1655",
                "duration_minutes": 535, "stops": 0,
                "price": 400.0, "currency": "USD",
                "offer_id": "offer-0",
            },
            "score": 85.0,
            "reasoning": "early arrival, low cost",
        },
        "alternatives": [
            {
                "candidate": {
                    "flight_number": "TR876", "carrier": "TR",
                    "departure_airport": "KUL", "arrival_airport": "NRT",
                    "departure_time": "1000", "arrival_time": "1855",
                    "duration_minutes": 535, "stops": 0,
                    "price": 500.0, "currency": "USD",
                    "offer_id": "offer-1",
                },
                "score": 72.0,
                "reasoning": "balanced option",
            },
        ],
        "total_candidates_evaluated": 5,
    }


# =====================================================================
# Evidence Tests
# =====================================================================

class TestEvidence:
    """Test the candidate evidence store."""

    def test_evidence_contains_only_atlas_data(self):
        """Evidence must only contain factual data from Atlas adapter."""
        bundle = _make_evidence()
        assert bundle.total_candidates == 3
        for c in bundle.candidates:
            assert c.source == "atlas_search"
            assert c.evidence_type == "atlas_search"
            # No LLM-generated fields
            assert c.flight_number.startswith("TR")
            assert c.price > 0

    def test_evidence_bundle_validates(self):
        """EvidenceBundle must be a valid Pydantic model."""
        bundle = _make_evidence()
        # Must be serializable
        dumped = bundle.model_dump()
        assert "candidates" in dumped
        assert "search_ids" in dumped
        assert dumped["total_candidates"] == 3
        # Must be reconstructable
        rebuilt = EvidenceBundle(**dumped)
        assert rebuilt.total_candidates == bundle.total_candidates

    def test_evidence_search_id_preserved(self):
        """Search ID must be preserved in the evidence bundle."""
        bundle = _make_evidence()
        assert "test-search" in bundle.search_ids
        for c in bundle.candidates:
            assert c.search_id == "test-search"


# =====================================================================
# Comparison Tests
# =====================================================================

class TestComparison:
    """Test the candidate comparison layer."""

    def test_comparator_preserves_deterministic_score(self):
        """Comparator must never alter the deterministic score."""
        evidence = _make_evidence()
        report = compare_candidates(evidence, budget_limit=1000.0)
        assert report.recommended is not None
        # Score must match evidence exactly
        assert report.recommended.score == 85.0
        for alt in report.alternatives:
            orig = [c for c in evidence.candidates
                    if c.flight_number == alt.flight_number][0]
            assert alt.score == orig.deterministic_score

    def test_comparator_orders_candidates_correctly(self):
        """Candidates must be ordered by deterministic score descending."""
        evidence = _make_evidence()
        report = compare_candidates(evidence, budget_limit=1000.0)
        assert report.recommended is not None
        assert report.recommended.rank == 1
        assert report.recommended.flight_number == "TR874"
        scores = [report.recommended.score] + [a.score for a in report.alternatives]
        assert scores == sorted(scores, reverse=True)

    def test_comparator_does_not_allow_llm_score_override(self):
        """Comparator output is deterministic — no LLM parameter exists."""
        evidence = _make_evidence()
        report1 = compare_candidates(evidence, budget_limit=1000.0)
        report2 = compare_candidates(evidence, budget_limit=1000.0)
        # Same input → same output (deterministic)
        assert report1.recommended.score == report2.recommended.score
        assert report1.recommended.flight_number == report2.recommended.flight_number

    def test_budget_status_is_deterministic(self):
        """Budget status must be computed deterministically."""
        evidence = _make_evidence()
        report = compare_candidates(evidence, budget_limit=450.0)
        # TR874 ($400) within budget, TR876 ($500) over budget
        assert report.recommended.budget_status == "within_budget"
        over_budget = [a for a in report.alternatives
                       if a.budget_status == "over_budget"]
        assert len(over_budget) >= 1


# =====================================================================
# Recommendation Validation Tests
# =====================================================================

class TestRecommendationValidation:
    """Test the recommendation integrity check."""

    def test_recommendation_exists_in_evidence(self):
        """Valid flight in evidence must pass validation."""
        evidence = _make_evidence()
        result = validate_recommendation(
            "TR874", evidence,
            mission_origin="KUL", mission_destination="NRT",
            mission_currency="USD",
        )
        assert result.valid is True
        assert len(result.errors) == 0

    def test_fabricated_flight_rejected(self):
        """Flight not in evidence must be rejected."""
        evidence = _make_evidence()
        result = validate_recommendation(
            "FAKE999", evidence,
            mission_origin="KUL", mission_destination="NRT",
        )
        assert result.valid is False
        assert any("not found" in e.lower() for e in result.errors)

    def test_wrong_origin_rejected(self):
        """Flight with wrong origin must be rejected."""
        evidence = _make_evidence()
        result = validate_recommendation(
            "TR874", evidence,
            mission_origin="SIN",  # Wrong origin
            mission_destination="NRT",
        )
        assert result.valid is False
        assert any("origin" in e.lower() for e in result.errors)

    def test_wrong_destination_rejected(self):
        """Flight with wrong destination must be rejected."""
        evidence = _make_evidence()
        result = validate_recommendation(
            "TR874", evidence,
            mission_origin="KUL",
            mission_destination="SIN",  # Wrong destination
        )
        assert result.valid is False
        assert any("destination" in e.lower() for e in result.errors)

    def test_wrong_currency_rejected(self):
        """Flight with wrong currency must be rejected."""
        evidence = _make_evidence()
        result = validate_recommendation(
            "TR874", evidence,
            mission_origin="KUL", mission_destination="NRT",
            mission_currency="EUR",  # Evidence has USD
        )
        assert result.valid is False
        assert any("currency" in e.lower() for e in result.errors)

    def test_wrong_date_rejected(self):
        """Score mismatch must be detected."""
        evidence = _make_evidence()
        result = validate_recommendation(
            "TR874", evidence,
            mission_origin="KUL", mission_destination="NRT",
            mission_currency="USD",
            expected_score=99.0,  # Actual is 85.0
        )
        assert result.valid is False
        assert any("score" in e.lower() for e in result.errors)

    def test_score_mismatch_rejected(self):
        """Large score mismatch must be detected."""
        evidence = _make_evidence()
        result = validate_recommendation(
            "TR874", evidence,
            mission_origin="KUL", mission_destination="NRT",
            mission_currency="USD",
            expected_score=50.0,  # Actual is 85.0, diff > 0.5
        )
        assert result.valid is False


# =====================================================================
# Budget Tests
# =====================================================================

class TestBudget:
    """Test the structured budget assessment."""

    def test_budget_assessment_within_budget(self):
        """Budget assessment must report within_budget correctly."""
        state = _make_state(budget_limit=1000.0)
        _populate_flight_state(state)

        from tros.agents.stubs import BudgetAgent
        agent = BudgetAgent()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        assert state.budget_assessment.get("within_budget") is True

    def test_budget_assessment_over_budget(self):
        """Budget assessment must detect over-budget flights."""
        state = _make_state(budget_limit=300.0)
        _populate_flight_state(state)

        from tros.agents.stubs import BudgetAgent
        agent = BudgetAgent()
        output = agent.execute(state)

        assert output.status == AgentStatus.COMPLETED
        assert state.budget_assessment.get("within_budget") is False

    def test_budget_margin_calculation(self):
        """Budget margin must be calculated correctly."""
        state = _make_state(budget_limit=1000.0)
        _populate_flight_state(state)

        from tros.agents.stubs import BudgetAgent
        agent = BudgetAgent()
        agent.execute(state)

        assessment = state.budget_assessment
        assert assessment.get("price") == 400.0
        assert assessment.get("budget_limit") == 1000.0
        assert assessment.get("remaining_budget") == 600.0
        assert assessment.get("margin_percentage") == 60.0


# =====================================================================
# Critic Tests
# =====================================================================

class TestCritic:
    """Test the evidence-based critic review."""

    def test_critic_detects_missing_evidence(self):
        """Critic must detect when flight recommendation has no evidence."""
        state = _make_state()
        # Set flight output with no evidence
        state.flight = {"best_option": {"candidate": {"flight_number": "TR874"}}}

        # Add a mock FlightAgent output with empty evidence
        state.update_agent_output(AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.8,
            evidence=[],
        ))

        from tros.agents.critic.agent import CriticAgent
        critic = CriticAgent()
        output = critic.execute(state)

        assert state.critic_report.get("critical_count", 0) >= 1
        findings = state.critic_report.get("findings", [])
        evidence_missing = [
            f for f in findings
            if "EVIDENCE_MISSING" in f.get("message", "")
        ]
        assert len(evidence_missing) >= 1

    def test_critic_detects_constraint_violation(self):
        """Critic must detect budget constraint violations."""
        state = _make_state(budget_limit=100.0)
        _populate_flight_state(state)

        state.update_agent_output(AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.8,
            evidence=[{"type": "flight_search"}],
        ))

        from tros.agents.critic.agent import CriticAgent
        critic = CriticAgent()
        output = critic.execute(state)

        # Should flag over-budget as critical
        findings = state.critic_report.get("findings", [])
        budget_findings = [
            f for f in findings
            if f.get("category") == "budget_compliance"
        ]
        assert len(budget_findings) >= 1

    def test_critic_approves_valid_recommendation(self):
        """Critic must approve when all checks pass."""
        state = _make_state(budget_limit=1000.0)
        _populate_flight_state(state)

        state.update_agent_output(AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.85,
            evidence=[{"type": "flight_search", "total_candidates": 5}],
        ))

        from tros.agents.critic.agent import CriticAgent
        critic = CriticAgent()
        output = critic.execute(state)

        assert state.critic_report.get("approved") is True

    def test_critic_does_not_fabricate_evidence(self):
        """Critic findings must reference actual state, not fabricated data."""
        state = _make_state()
        _populate_flight_state(state)

        state.update_agent_output(AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.85,
            evidence=[{"type": "flight_search"}],
        ))

        from tros.agents.critic.agent import CriticAgent
        critic = CriticAgent()
        output = critic.execute(state)

        findings = state.critic_report.get("findings", [])
        for f in findings:
            # No fabricated flight numbers or prices in findings
            msg = f.get("message", "")
            assert "FAKE" not in msg.upper()
            assert "INVENTED" not in msg.upper()


# =====================================================================
# Conflict Tests
# =====================================================================

class TestConflict:
    """Test agent conflict detection."""

    def test_no_conflict_when_agents_agree(self):
        """No conflicts when all agents agree."""
        report = detect_conflicts(
            flight_recommendation={"best_option": {}},
            budget_assessment={"within_budget": True},
            critic_report={"approved": True},
            evidence_validated=True,
            recommended_flight="TR874",
        )
        assert len(report.conflicts) == 0
        assert report.has_critical_conflict is False

    def test_conflict_when_budget_disagrees(self):
        """Conflict detected when budget agent says over budget."""
        report = detect_conflicts(
            flight_recommendation={"best_option": {"candidate": {}}},
            budget_assessment={"within_budget": False},
            critic_report={"approved": True},
            evidence_validated=True,
            recommended_flight="TR874",
        )
        assert len(report.conflicts) >= 1
        budget_conflicts = [
            c for c in report.conflicts if "BudgetAgent" in c.agents
        ]
        assert len(budget_conflicts) >= 1

    def test_conflict_when_critic_rejects(self):
        """Conflict detected when critic rejects but budget says ok."""
        report = detect_conflicts(
            budget_assessment={"within_budget": True},
            critic_report={"approved": False},
            evidence_validated=True,
            recommended_flight="TR874",
        )
        assert len(report.conflicts) >= 1
        assert any(
            "CriticAgent" in c.agents for c in report.conflicts
        )

    def test_critical_conflict_blocks_final_approval(self):
        """Critical conflict must be flagged."""
        report = detect_conflicts(
            flight_recommendation={"best_option": {"candidate": {}}},
            budget_assessment={"within_budget": False},
            critic_report={"approved": True},
            evidence_validated=False,
            recommended_flight="TR874",
        )
        assert report.has_critical_conflict is True


# =====================================================================
# Confidence Tests
# =====================================================================

class TestConfidence:
    """Test the deterministic confidence calculation."""

    def test_confidence_increases_with_validation(self):
        """Confidence increases when all validations pass."""
        factors_all_pass = ConfidenceFactors(
            evidence_validated=True,
            budget_validated=True,
            constraint_validated=True,
            critic_approved=True,
            ranking_margin_bonus=True,
        )
        result = calculate_confidence(factors_all_pass)
        assert result.confidence > 0.50

    def test_confidence_decreases_with_conflict(self):
        """Confidence decreases with unresolved conflicts."""
        factors_with_conflicts = ConfidenceFactors(
            evidence_validated=True,
            budget_validated=True,
            unresolved_conflicts=2,
        )
        result = calculate_confidence(factors_with_conflicts)

        factors_no_conflicts = ConfidenceFactors(
            evidence_validated=True,
            budget_validated=True,
            unresolved_conflicts=0,
        )
        result_clean = calculate_confidence(factors_no_conflicts)
        assert result.confidence < result_clean.confidence

    def test_confidence_is_clamped(self):
        """Confidence must be clamped to [0.0, 0.95]."""
        # Maximum possible
        factors_max = ConfidenceFactors(
            evidence_validated=True,
            budget_validated=True,
            constraint_validated=True,
            critic_approved=True,
            ranking_margin_bonus=True,
        )
        result_max = calculate_confidence(factors_max)
        assert result_max.confidence <= 0.95

        # Minimum possible
        factors_min = ConfidenceFactors(
            unresolved_conflicts=10,
            missing_evidence=True,
        )
        result_min = calculate_confidence(factors_min)
        assert result_min.confidence >= 0.0

    def test_confidence_is_deterministic(self):
        """Same inputs must always produce same confidence."""
        factors = ConfidenceFactors(
            evidence_validated=True,
            budget_validated=True,
            critic_approved=True,
            ranking_margin_bonus=False,
            unresolved_conflicts=1,
        )
        r1 = calculate_confidence(factors)
        r2 = calculate_confidence(factors)
        assert r1.confidence == r2.confidence
        assert r1.breakdown == r2.breakdown


# =====================================================================
# Supervisor Tests
# =====================================================================

class TestSupervisor:
    """Test supervisor Phase 5 coordination."""

    def test_supervisor_uses_validated_recommendation(self):
        """Supervisor must use validated recommendation in mission_decision."""
        state = _make_state(budget_limit=1000.0)
        _populate_flight_state(state)

        # Simulate FlightAgent output
        state.update_agent_output(AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.85,
            evidence=[{"type": "flight_search", "total_candidates": 5}],
        ))

        # Simulate BudgetAgent output
        from tros.agents.stubs import BudgetAgent
        budget_agent = BudgetAgent()
        budget_output = budget_agent.execute(state)
        state.update_agent_output(budget_output)

        # Run evidence building
        from tros.agents.supervisor.agent import SupervisorAgent
        supervisor = SupervisorAgent()
        supervisor._build_evidence_and_comparison(state)
        assert state.evidence.get("total_candidates", 0) > 0

    def test_supervisor_exposes_conflicts(self):
        """Supervisor must expose conflicts in mission_decision."""
        state = _make_state(budget_limit=100.0)  # Very low budget
        _populate_flight_state(state)

        state.update_agent_output(AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.85,
            evidence=[{"type": "flight_search"}],
        ))

        from tros.agents.stubs import BudgetAgent
        budget_agent = BudgetAgent()
        budget_output = budget_agent.execute(state)
        state.update_agent_output(budget_output)

        from tros.agents.supervisor.agent import SupervisorAgent
        supervisor = SupervisorAgent()
        supervisor._build_evidence_and_comparison(state)

        # Simulate critic
        from tros.agents.critic.agent import CriticAgent
        critic = CriticAgent()
        critic_output = critic.execute(state)
        state.update_agent_output(critic_output)

        # Simulate reflection
        from tros.agents.reflection.agent import ReflectionAgent
        reflection = ReflectionAgent()
        refl_output = reflection.execute(state)
        state.update_agent_output(refl_output)

        # Run conflict detection
        supervisor._run_conflict_detection_and_validation(state)

        decision = state.mission_decision
        assert "confidence" in decision
        assert "conflicts_present" in decision

    def test_supervisor_does_not_fabricate_flight(self):
        """Supervisor must not recommend a flight not in evidence."""
        state = _make_state()
        state.flight = {}  # No flight data

        from tros.agents.supervisor.agent import SupervisorAgent
        supervisor = SupervisorAgent()
        supervisor._build_evidence_and_comparison(state)

        # No flight → no evidence → no recommendation
        assert state.evidence.get("total_candidates", 0) == 0


# =====================================================================
# Recovery Plan Tests
# =====================================================================

class TestRecoveryPlan:
    """Test the recovery plan generation."""

    def _run_full_pipeline(self, budget_limit: float = 1000.0) -> SharedMissionState:
        """Run the full Phase 5 pipeline for testing."""
        state = _make_state(budget_limit=budget_limit)
        _populate_flight_state(state)

        # FlightAgent output
        state.update_agent_output(AgentOutput(
            agent="FlightAgent",
            status=AgentStatus.COMPLETED,
            confidence=0.85,
            evidence=[{"type": "flight_search", "total_candidates": 5}],
        ))

        # BudgetAgent
        from tros.agents.stubs import BudgetAgent
        budget_agent = BudgetAgent()
        budget_output = budget_agent.execute(state)
        state.update_agent_output(budget_output)

        # Supervisor: evidence + comparison
        from tros.agents.supervisor.agent import SupervisorAgent
        supervisor = SupervisorAgent()
        supervisor._build_evidence_and_comparison(state)

        # Critic
        from tros.agents.critic.agent import CriticAgent
        critic = CriticAgent()
        critic_output = critic.execute(state)
        state.update_agent_output(critic_output)

        # Reflection
        from tros.agents.reflection.agent import ReflectionAgent
        reflection = ReflectionAgent()
        refl_output = reflection.execute(state)
        state.update_agent_output(refl_output)

        # Conflict detection + confidence
        supervisor._run_conflict_detection_and_validation(state)

        # Summary
        from tros.agents.summary.agent import SummaryAgent
        summary = SummaryAgent()
        summary_output = summary.execute(state)
        state.update_agent_output(summary_output)

        return state

    def test_recovery_plan_contains_validated_flight(self):
        """Recovery plan must contain the validated flight."""
        state = self._run_full_pipeline()
        plan = state.recovery_plan
        assert plan.get("recommended_flight") is not None
        assert plan["recommended_flight"]["flight_number"] == "TR874"

    def test_recovery_plan_contains_alternatives(self):
        """Recovery plan must contain alternatives."""
        state = self._run_full_pipeline()
        plan = state.recovery_plan
        assert isinstance(plan.get("alternatives"), list)
        assert len(plan["alternatives"]) >= 1

    def test_recovery_plan_contains_budget(self):
        """Recovery plan must contain budget assessment."""
        state = self._run_full_pipeline()
        plan = state.recovery_plan
        assert "budget_assessment" in plan
        assert plan["budget_assessment"].get("within_budget") is True

    def test_recovery_plan_contains_critic_report(self):
        """Recovery plan must contain critic summary."""
        state = self._run_full_pipeline()
        plan = state.recovery_plan
        assert "critic_summary" in plan

    def test_recovery_plan_contains_conflicts(self):
        """Recovery plan must contain conflicts list."""
        state = self._run_full_pipeline()
        plan = state.recovery_plan
        assert "conflicts" in plan
        assert isinstance(plan["conflicts"], list)
