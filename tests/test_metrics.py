"""Tests for Phase 9 metrics collector and endpoint."""

import pytest

from tros.api.metrics import MetricsCollector, get_metrics_collector, reset_metrics_collector


@pytest.fixture(autouse=True)
def _clean():
    reset_metrics_collector()
    yield
    reset_metrics_collector()


class TestMetricsCollector:
    def test_increment_counters(self):
        mc = MetricsCollector()
        mc.increment("missions_submitted")
        mc.increment("missions_completed", 3)
        snap = mc.get_snapshot()
        assert snap["missions_submitted"] == 1
        assert snap["missions_completed"] == 3

    def test_record_duration(self):
        mc = MetricsCollector()
        mc.record_duration(100.0)
        mc.record_duration(200.0)
        mc.record_duration(300.0)
        snap = mc.get_snapshot()
        assert snap["duration"]["count"] == 3
        assert snap["duration"]["avg_ms"] == 200.0
        assert snap["duration"]["min_ms"] == 100.0
        assert snap["duration"]["max_ms"] == 300.0

    def test_no_sensitive_data_exposed(self):
        mc = MetricsCollector()
        snap = mc.get_snapshot()
        # Only aggregate fields allowed
        allowed_keys = {
            "missions_submitted", "missions_completed", "missions_failed",
            "missions_cancelled", "recovery_count", "llm_errors",
            "atlas_errors", "sse_connections", "duration", "timestamp",
            # Phase 10 additions
            "request_count", "rate_limit_events", "auth_failures", "repository_errors",
        }
        assert set(snap.keys()) <= allowed_keys

    def test_reset(self):
        mc = MetricsCollector()
        mc.increment("missions_submitted", 5)
        mc.record_duration(100.0)
        mc.reset()
        snap = mc.get_snapshot()
        assert snap["missions_submitted"] == 0
        assert snap["duration"] == {}

    def test_singleton(self):
        c1 = get_metrics_collector()
        c2 = get_metrics_collector()
        assert c1 is c2

    def test_duration_percentiles(self):
        mc = MetricsCollector()
        for i in range(10):
            mc.record_duration(float((i + 1) * 100))
        snap = mc.get_snapshot()
        assert snap["duration"]["p50_ms"] == 500.0 or snap["duration"]["p50_ms"] == 600.0
        assert snap["duration"]["p95_ms"] >= 900.0
