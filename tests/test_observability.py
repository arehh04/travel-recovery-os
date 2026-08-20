"""Tests for enhanced observability (Phase 10)."""

from __future__ import annotations

import io
import json
import logging
import threading

import pytest

from tros.api.metrics import (
    MetricsCollector,
    reset_metrics_collector,
)
from tros.api.structured_logging import (
    RequestContextFilter,
    StructuredFormatter,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_metrics_collector()
    yield
    reset_metrics_collector()


class TestRequestMetrics:
    def test_request_count_tracked(self):
        """Request count is tracked per endpoint."""
        collector = MetricsCollector()
        collector.record_request("GET", "/api/v1/health", 200, 5.0)
        collector.record_request("GET", "/api/v1/health", 200, 8.0)
        collector.record_request("POST", "/api/v1/missions", 202, 12.0)

        stats = collector.get_request_stats()
        assert "GET:/api/v1/health" in stats
        assert stats["GET:/api/v1/health"]["count"] == 2
        assert "POST:/api/v1/missions" in stats
        assert stats["POST:/api/v1/missions"]["count"] == 1

    def test_latency_percentiles(self):
        """Latency percentiles are computed correctly."""
        collector = MetricsCollector()
        for i in range(20):
            collector.record_request("GET", "/test", 200, float(i * 10))

        stats = collector.get_request_stats()
        assert "GET:/test" in stats
        entry = stats["GET:/test"]
        assert entry["count"] == 20
        assert entry["p50_ms"] >= 0
        assert entry["p95_ms"] >= entry["p50_ms"]
        assert entry["avg_ms"] >= 0

    def test_rate_limit_counter(self):
        """Rate limit events are counted."""
        collector = MetricsCollector()
        collector.increment("rate_limit_events", 3)
        snapshot = collector.get_snapshot()
        assert snapshot["rate_limit_events"] == 3

    def test_auth_failure_counter(self):
        """Auth failures are counted."""
        collector = MetricsCollector()
        collector.increment("auth_failures", 1)
        collector.increment("auth_failures", 1)
        snapshot = collector.get_snapshot()
        assert snapshot["auth_failures"] == 2

    def test_repository_error_counter(self):
        """Repository errors are counted."""
        collector = MetricsCollector()
        collector.increment("repository_errors", 1)
        snapshot = collector.get_snapshot()
        assert snapshot["repository_errors"] == 1


class TestRequestContextFilter:
    def test_request_id_in_logs(self):
        """Request context filter injects request_id into log records."""
        test_logger = logging.getLogger("test_context")
        test_logger.setLevel(logging.DEBUG)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        ctx_filter = RequestContextFilter()
        handler.addFilter(ctx_filter)
        test_logger.addHandler(handler)
        test_logger.addFilter(ctx_filter)

        RequestContextFilter.set_context(request_id="req-abc-123", mission_id="mission-xyz")
        test_logger.info("Processing request")

        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed.get("request_id") == "req-abc-123"
        assert parsed.get("mission_id") == "mission-xyz"

        RequestContextFilter.clear_context()
        test_logger.removeHandler(handler)

    def test_correlation_ids_in_background_thread(self):
        """Correlation IDs propagate to background threads."""
        results = []

        def background_task():
            test_logger = logging.getLogger("test_bg")
            test_logger.setLevel(logging.DEBUG)
            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            handler.setFormatter(StructuredFormatter())
            ctx_filter = RequestContextFilter()
            handler.addFilter(ctx_filter)
            test_logger.addHandler(handler)
            test_logger.addFilter(ctx_filter)

            RequestContextFilter.set_context(request_id="bg-req", mission_id="bg-mission")
            test_logger.info("Background task")

            output = stream.getvalue()
            parsed = json.loads(output)
            results.append(parsed)
            test_logger.removeHandler(handler)

        t = threading.Thread(target=background_task)
        t.start()
        t.join()

        assert len(results) == 1
        assert results[0].get("request_id") == "bg-req"
        assert results[0].get("mission_id") == "bg-mission"
