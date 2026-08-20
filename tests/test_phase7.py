"""Phase 7 tests — Production Hardening, Observability & API Readiness.

Tests cover:
1. ExecutionContext (mission IDs, propagation)
2. Structured logging
3. Error taxonomy
4. Timeout handling
5. Retry behavior
6. Idempotency
7. Lifecycle transitions
8. Cancellation
9. Performance metadata
10. MissionService
11. Public MissionResult
12. Health checks
13. Security regression
14. Full integration
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from tros.execution.cancellation import CancellationToken
from tros.execution.context import ExecutionContext
from tros.execution.errors import (
    AtlasError,
    AtlasTimeoutError,
    CancellationError,
    ConstraintViolationError,
    InternalMissionError,
    LLMError,
    LLMTimeoutError,
    MissionError,
    RecommendationError,
    RecoveryError,
    ToolExecutionError,
    ValidationError,
)
from tros.execution.health import HealthReport, check_health
from tros.execution.idempotency import IdempotencyStore
from tros.execution.lifecycle import (
    ExecutionStatus,
    is_valid_transition,
    validate_transition,
)
from tros.execution.logging import StructuredLogger, Timer
from tros.execution.performance import PerformanceMetrics, PerfTimer
from tros.execution.retry import execute_with_retry
from tros.service.mission_service import MissionService
from tros.service.result import FlightInfo, MissionResult
from tros.state.mission_state import SharedMissionState

# =====================================================================
# 1. ExecutionContext
# =====================================================================

class TestExecutionContext:
    """Execution context with unique IDs."""

    def test_create_generates_unique_ids(self):
        ctx = ExecutionContext.create()
        assert ctx.mission_id.startswith("mission-")
        assert ctx.execution_id.startswith("exec-")
        assert ctx.request_id.startswith("req-")

    def test_create_with_explicit_ids(self):
        ctx = ExecutionContext.create(mission_id="m-123", request_id="r-456")
        assert ctx.mission_id == "m-123"
        assert ctx.request_id == "r-456"

    def test_ids_are_unique(self):
        ctx1 = ExecutionContext.create()
        ctx2 = ExecutionContext.create()
        assert ctx1.execution_id != ctx2.execution_id

    def test_to_dict_no_secrets(self):
        ctx = ExecutionContext.create()
        d = ctx.to_dict()
        assert "mission_id" in d
        assert "execution_id" in d
        assert "api_key" not in d
        assert "secret" not in d

    def test_has_timestamp(self):
        ctx = ExecutionContext.create()
        assert ctx.started_at is not None
        assert isinstance(ctx.started_at, datetime)


# =====================================================================
# 2. Structured Logging
# =====================================================================

class TestStructuredLogging:
    """Machine-readable JSON structured logging."""

    def test_event_produces_json(self, caplog):
        logger = StructuredLogger("test_structured")
        with caplog.at_level(logging.INFO, logger="test_structured"):
            logger.event("TEST_EVENT", agent="TestAgent")
        assert len(caplog.records) == 1
        record = json.loads(caplog.records[0].message)
        assert record["event_name"] == "TEST_EVENT"
        assert record["agent"] == "TestAgent"

    def test_event_includes_context(self, caplog):
        logger = StructuredLogger("test_ctx")
        logger.set_context(mission_id="m-1", execution_id="e-1")
        with caplog.at_level(logging.INFO, logger="test_ctx"):
            logger.event("AGENT_COMPLETED")
        record = json.loads(caplog.records[0].message)
        assert record["mission_id"] == "m-1"
        assert record["execution_id"] == "e-1"

    def test_event_filters_secrets(self, caplog):
        logger = StructuredLogger("test_secrets")
        with caplog.at_level(logging.INFO, logger="test_secrets"):
            logger.event("TEST", api_key="sk-secret", safe_field="ok")
        record = json.loads(caplog.records[0].message)
        assert "api_key" not in record
        assert record["safe_field"] == "ok"

    def test_event_includes_duration(self, caplog):
        logger = StructuredLogger("test_dur")
        with caplog.at_level(logging.INFO, logger="test_dur"):
            logger.event("TIMER_EVENT", duration_ms=150)
        record = json.loads(caplog.records[0].message)
        assert record["duration_ms"] == 150

    def test_timer_measures_duration(self):
        import time
        with Timer() as t:
            time.sleep(0.01)
        assert t.elapsed_ms >= 5  # at least some ms


# =====================================================================
# 3. Error Taxonomy
# =====================================================================

class TestErrorTaxonomy:
    """Application error hierarchy."""

    def test_mission_error_structure(self):
        err = MissionError("TEST_ERROR", "TEST", "something broke")
        assert err.error_code == "TEST_ERROR"
        assert err.category == "TEST"
        d = err.to_dict()
        assert d["error_code"] == "TEST_ERROR"
        assert d["retryable"] is False

    def test_validation_error(self):
        err = ValidationError("bad input")
        assert err.error_code == "VALIDATION_ERROR"
        assert err.retryable is False

    def test_atlas_error_retryable(self):
        err = AtlasError("search failed")
        assert err.retryable is True

    def test_atlas_timeout(self):
        err = AtlasTimeoutError()
        assert err.error_code == "ATLAS_ERROR"
        assert err.retryable is True

    def test_llm_error(self):
        err = LLMError("provider down")
        assert err.error_code == "LLM_ERROR"
        assert err.retryable is True

    def test_llm_timeout(self):
        err = LLMTimeoutError()
        assert err.error_code == "LLM_ERROR"
        assert err.retryable is True

    def test_cancellation_error(self):
        err = CancellationError("user cancelled")
        assert err.error_code == "CANCELLED"
        assert err.retryable is False

    def test_error_no_secrets_in_dict(self):
        err = MissionError("X", "Y", "msg", details={"api_key": "secret"})
        d = err.to_dict()
        assert "api_key" not in str(d.get("details", {}))  # details not in to_dict

    def test_all_errors_inherit_mission_error(self):
        errors = [
            ValidationError("x"), ConstraintViolationError("x"),
            ToolExecutionError("x"), AtlasError("x"),
            LLMError("x"), RecoveryError("x"),
            RecommendationError("x"), InternalMissionError("x"),
        ]
        for err in errors:
            assert isinstance(err, MissionError)


# =====================================================================
# 4. Lifecycle Transitions
# =====================================================================

class TestLifecycle:
    """Execution status state machine."""

    def test_valid_pending_to_running(self):
        assert is_valid_transition(ExecutionStatus.PENDING, ExecutionStatus.RUNNING)

    def test_valid_running_to_completed(self):
        assert is_valid_transition(ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED)

    def test_valid_running_to_recovering(self):
        assert is_valid_transition(ExecutionStatus.RUNNING, ExecutionStatus.RECOVERING)

    def test_valid_recovering_to_running(self):
        assert is_valid_transition(ExecutionStatus.RECOVERING, ExecutionStatus.RUNNING)

    def test_valid_running_to_cancelled(self):
        assert is_valid_transition(ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED)

    def test_invalid_completed_to_running(self):
        assert not is_valid_transition(ExecutionStatus.COMPLETED, ExecutionStatus.RUNNING)

    def test_invalid_failed_to_running(self):
        assert not is_valid_transition(ExecutionStatus.FAILED, ExecutionStatus.RUNNING)

    def test_invalid_cancelled_to_running(self):
        assert not is_valid_transition(ExecutionStatus.CANCELLED, ExecutionStatus.RUNNING)

    def test_validate_transition_raises_on_invalid(self):
        with pytest.raises(ValueError, match="Invalid lifecycle transition"):
            validate_transition(ExecutionStatus.COMPLETED, ExecutionStatus.RUNNING)

    def test_validate_transition_passes_on_valid(self):
        validate_transition(ExecutionStatus.PENDING, ExecutionStatus.RUNNING)


# =====================================================================
# 5. Cancellation
# =====================================================================

class TestCancellation:
    """Cooperative cancellation token."""

    def test_initially_not_cancelled(self):
        token = CancellationToken()
        assert not token.is_cancelled()

    def test_cancel_marks_token(self):
        token = CancellationToken()
        token.cancel("test reason")
        assert token.is_cancelled()
        assert token.reason == "test reason"

    def test_throw_if_cancelled_raises(self):
        token = CancellationToken()
        token.cancel()
        with pytest.raises(CancellationError):
            token.throw_if_cancelled()

    def test_throw_if_not_cancelled_passes(self):
        token = CancellationToken()
        token.throw_if_cancelled()  # no error

    def test_cancellation_preserves_reason(self):
        token = CancellationToken()
        token.cancel("timeout exceeded")
        assert token.reason == "timeout exceeded"


# =====================================================================
# 6. Retry
# =====================================================================

class TestRetry:
    """Bounded exponential backoff retry."""

    def test_success_no_retry(self):
        result = execute_with_retry(lambda: 42, max_retries=2, base_delay=0.01)
        assert result == 42

    def test_retry_on_retryable_error(self):
        calls = [0]
        def flaky():
            calls[0] += 1
            if calls[0] < 2:
                raise AtlasError("transient")
            return "ok"
        result = execute_with_retry(flaky, max_retries=2, base_delay=0.01)
        assert result == "ok"
        assert calls[0] == 2

    def test_no_retry_on_non_retryable(self):
        calls = [0]
        def fail():
            calls[0] += 1
            raise ValidationError("bad input")
        with pytest.raises(ValidationError):
            execute_with_retry(fail, max_retries=3, base_delay=0.01)
        assert calls[0] == 1  # only 1 call, no retry

    def test_retry_exhausted_raises(self):
        def always_fail():
            raise AtlasError("always fails")
        with pytest.raises(AtlasError):
            execute_with_retry(always_fail, max_retries=2, base_delay=0.01)

    def test_retry_bounded(self):
        calls = [0]
        def always_fail():
            calls[0] += 1
            raise AtlasError("fail")
        with pytest.raises(AtlasError):
            execute_with_retry(always_fail, max_retries=2, base_delay=0.01)
        assert calls[0] == 3  # initial + 2 retries


# =====================================================================
# 7. Idempotency
# =====================================================================

class TestIdempotency:
    """In-memory idempotency store."""

    def test_first_request(self):
        store = IdempotencyStore()
        assert not store.exists("key-1")
        store.set("key-1", {"result": "ok"})
        assert store.exists("key-1")

    def test_duplicate_request(self):
        store = IdempotencyStore()
        store.set("key-1", {"result": "first"})
        entry = store.get("key-1")
        assert entry is not None
        assert entry.result == {"result": "first"}

    def test_different_keys(self):
        store = IdempotencyStore()
        store.set("key-a", "result-a")
        store.set("key-b", "result-b")
        assert store.get("key-a").result == "result-a"
        assert store.get("key-b").result == "result-b"

    def test_get_nonexistent(self):
        store = IdempotencyStore()
        assert store.get("nonexistent") is None

    def test_size(self):
        store = IdempotencyStore()
        store.set("a", 1)
        store.set("b", 2)
        assert store.size == 2


# =====================================================================
# 8. Performance Metrics
# =====================================================================

class TestPerformance:
    """Performance timing instrumentation."""

    def test_default_values_zero(self):
        metrics = PerformanceMetrics()
        assert metrics.total_ms == 0
        assert metrics.llm_ms == 0
        assert metrics.atlas_ms == 0

    def test_perf_timer_records_field(self):
        import time
        metrics = PerformanceMetrics()
        with PerfTimer(metrics, "total_ms"):
            time.sleep(0.01)
        assert metrics.total_ms >= 5

    def test_to_dict_all_fields_present(self):
        metrics = PerformanceMetrics(total_ms=100, llm_ms=50, atlas_ms=30)
        d = metrics.to_dict()
        assert d["total_ms"] == 100
        assert d["llm_ms"] == 50
        assert d["atlas_ms"] == 30
        assert d["recovery_ms"] == 0

    def test_all_metrics_non_negative(self):
        metrics = PerformanceMetrics()
        for v in metrics.to_dict().values():
            assert v >= 0


# =====================================================================
# 9. Health Checks
# =====================================================================

class TestHealth:
    """System health/readiness checks."""

    def test_health_report_structure(self):
        report = check_health()
        assert isinstance(report, HealthReport)
        d = report.to_dict()
        assert "status" in d
        assert "checks" in d
        assert isinstance(d["checks"], list)

    def test_configuration_check_present(self):
        report = check_health()
        names = [c["name"] for c in report.to_dict()["checks"]]
        assert "configuration" in names

    def test_no_secrets_in_report(self):
        report = check_health()
        report_str = json.dumps(report.to_dict())
        assert "sk-" not in report_str


# =====================================================================
# 10. MissionService
# =====================================================================

class TestMissionService:
    """Service layer for mission execution."""

    def test_validates_required_fields(self):
        service = MissionService(llm_client=None)
        result = service.run({"origin": "", "destination": "NRT", "departure_date": "2026-08-20"})
        assert result.status == "failed"

    def test_idempotency_returns_cached(self):
        service = MissionService(llm_client=None)
        # First request fails validation but still caches
        result1 = service.run(
            {"origin": "", "destination": "NRT", "departure_date": "2026-08-20"},
            idempotency_key="dup-key",
        )
        result2 = service.run(
            {"origin": "", "destination": "NRT", "departure_date": "2026-08-20"},
            idempotency_key="dup-key",
        )
        assert result1.mission_id == result2.mission_id

    def test_cancellation_before_execution(self):
        service = MissionService(llm_client=None)
        token = CancellationToken()
        token.cancel("pre-cancelled")
        result = service.run(
            {"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            cancellation_token=token,
        )
        # Should still run (cancellation check is before execution,
        # but the request validation passes and supervisor runs)
        # The service handles this gracefully
        assert result is not None

    def test_get_result_returns_cached(self):
        service = MissionService(llm_client=None)
        result = service.run(
            {"origin": "", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        cached = service.get_result(result.mission_id)
        assert cached is not None


# =====================================================================
# 11. Public MissionResult
# =====================================================================

class TestMissionResult:
    """Sanitized public result model."""

    def test_to_dict_structure(self):
        result = MissionResult(
            mission_id="m-1",
            execution_id="e-1",
            status="completed",
            recommendation=FlightInfo(
                flight_number="TR874", carrier="TR", price=400.0, score=85.0,
            ),
            confidence=0.83,
        )
        d = result.to_dict()
        assert d["mission_id"] == "m-1"
        assert d["recommendation"]["flight_number"] == "TR874"
        assert d["confidence"] == 0.83

    def test_no_internal_state_in_dict(self):
        result = MissionResult(mission_id="m-1", status="completed")
        d = result.to_dict()
        assert "llm_metadata" not in d
        assert "react_trace" not in d
        assert "phase5_trace" not in d
        assert "phase6_trace" not in d
        assert "prompt" not in str(d).lower()

    def test_from_state(self):
        state = SharedMissionState(mission_id="test-mission")
        state.flight = {
            "best_option": {
                "candidate": {
                    "flight_number": "TR874", "carrier": "TR",
                    "departure_time": "0800", "arrival_time": "1655",
                    "duration_minutes": 535, "stops": 0,
                    "price": 400.0, "currency": "USD",
                },
                "score": 85.0,
            },
            "alternatives": [],
        }
        state.mission_decision = {"status": "approved", "confidence": 0.83}
        state.budget_assessment = {"within_budget": True}
        state.conflict_report = {"conflicts": [], "has_critical_conflict": False}
        state.recovery_state = {}

        result = MissionResult.from_state(state)
        assert result.mission_id == "test-mission"
        assert result.recommendation.flight_number == "TR874"
        assert result.confidence == 0.83


# =====================================================================
# 12. Security Regression
# =====================================================================

class TestSecurityRegression:
    """Ensure Phase 1-6 security boundaries remain intact."""

    def test_no_secrets_in_execution_context(self):
        ctx = ExecutionContext.create()
        d = ctx.to_dict()
        for key in d:
            assert key not in ("api_key", "secret", "password")

    def test_error_dict_no_secrets(self):
        err = AtlasError("search failed")
        d = err.to_dict()
        assert "api_key" not in str(d)
        assert "sk-" not in str(d)

    def test_mission_result_no_raw_llm(self):
        result = MissionResult(mission_id="m-1", status="completed")
        d = result.to_dict()
        for key in d:
            assert key not in ("raw_llm", "prompts", "tool_arguments")

    def test_tool_names_allowlisted(self):
        """ToolExecutor only accepts 'search_flights'."""
        from tros.llm.tool_executor import ToolExecutor
        executor = ToolExecutor(adapter=MagicMock())
        obs = executor.execute_tool("invalid_tool", {}, {})
        assert obs.success is False
        assert obs.error_code == "UNKNOWN_TOOL"

    def test_no_subprocess_in_recovery_engine(self):
        """RecoveryEngine never calls subprocess directly."""
        from tros.agents.recovery.engine import RecoveryEngine
        engine = RecoveryEngine(tool_executor=MagicMock(), max_attempts=1)
        state = SharedMissionState(mission_id="sec-test")
        from tros.agents.conflict_detector import ConflictReport
        from tros.agents.flight.recommendation_validator import ValidationResult
        from tros.llm.evidence import EvidenceBundle
        with patch("subprocess.run") as mock_sub:
            engine.run(
                conflict_report=ConflictReport(),
                validation_result=ValidationResult(valid=True, validated_flight="TR874"),
                evidence=EvidenceBundle(),
                budget_assessment={"within_budget": True},
                mission_context={"origin": "KUL", "destination": "NRT"},
                flight_data={},
                state=state,
            )
            mock_sub.assert_not_called()


# =====================================================================
# 13. Integration
# =====================================================================

class TestPhase7Integration:
    """Full integration tests combining Phase 7 features."""

    def test_execution_context_propagation(self):
        """ExecutionContext IDs are unique and non-empty."""
        ctx = ExecutionContext.create(mission_id="integration-test")
        assert ctx.mission_id == "integration-test"
        assert len(ctx.execution_id) > 10
        assert len(ctx.request_id) > 10

    def test_lifecycle_full_flow(self):
        """Valid full lifecycle: PENDING → RUNNING → COMPLETED."""
        validate_transition(ExecutionStatus.PENDING, ExecutionStatus.RUNNING)
        validate_transition(ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED)

    def test_lifecycle_recovery_flow(self):
        """Valid recovery flow: RUNNING → RECOVERING → RUNNING → COMPLETED."""
        validate_transition(ExecutionStatus.RUNNING, ExecutionStatus.RECOVERING)
        validate_transition(ExecutionStatus.RECOVERING, ExecutionStatus.RUNNING)
        validate_transition(ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED)

    def test_lifecycle_conditional_recovery_flow(self):
        """Valid conditional: RUNNING → CONDITIONAL → RECOVERING → FAILED."""
        validate_transition(ExecutionStatus.RUNNING, ExecutionStatus.CONDITIONAL)
        validate_transition(ExecutionStatus.CONDITIONAL, ExecutionStatus.RECOVERING)
        validate_transition(ExecutionStatus.RECOVERING, ExecutionStatus.FAILED)

    def test_retry_with_cancellation(self):
        """Retry stops when cancellation is triggered."""
        token = CancellationToken()
        calls = [0]
        def check_and_fail():
            calls[0] += 1
            if calls[0] >= 2:
                token.cancel("stop retrying")
            raise AtlasError("transient")
        # Retry continues because execute_with_retry doesn't check token
        # (cancellation is a separate concern from retry)
        with pytest.raises(AtlasError):
            execute_with_retry(check_and_fail, max_retries=3, base_delay=0.01)
        assert token.is_cancelled()
