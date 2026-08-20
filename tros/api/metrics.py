"""Metrics collector — aggregate observability data (Phase 9).

Thread-safe counters for mission lifecycle, error rates, and performance.
Exposes only aggregate numbers — never sensitive mission content.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class MetricsCollector:
    """Collects and exposes aggregate metrics for observability."""

    def __init__(self, window_size: int = 100):
        self._lock = threading.Lock()
        self._counters = {
            "missions_submitted": 0,
            "missions_completed": 0,
            "missions_failed": 0,
            "missions_cancelled": 0,
            "recovery_count": 0,
            "llm_errors": 0,
            "atlas_errors": 0,
            "sse_connections": 0,
            # Phase 10 additions
            "request_count": 0,
            "rate_limit_events": 0,
            "auth_failures": 0,
            "repository_errors": 0,
        }
        # Duration tracking (rolling window)
        self._durations = deque(maxlen=window_size)
        # Request latency tracking per endpoint (Phase 10)
        self._request_latencies: dict[str, deque] = {}

    def increment(self, counter: str, value: int = 1) -> None:
        """Increment a named counter."""
        with self._lock:
            if counter in self._counters:
                self._counters[counter] += value
            else:
                # Allow dynamic counters (Phase 10)
                self._counters[counter] = self._counters.get(counter, 0) + value

    def record_request(self, method: str, path: str, status: int, duration_ms: float) -> None:
        """Record a request with endpoint-level latency tracking (Phase 10)."""
        with self._lock:
            self._counters["request_count"] = self._counters.get("request_count", 0) + 1
            key = f"{method}:{path}"
            if key not in self._request_latencies:
                self._request_latencies[key] = deque(maxlen=100)
            self._request_latencies[key].append(duration_ms)

    def record_duration(self, duration_ms: float) -> None:
        """Record a mission duration."""
        with self._lock:
            self._durations.append(duration_ms)

    def get_snapshot(self) -> dict:
        """Get a snapshot of all metrics.

        Returns only aggregate numbers — no sensitive data.
        """
        with self._lock:
            counters = dict(self._counters)
            durations = list(self._durations)

        # Compute duration statistics
        duration_stats = {}
        if durations:
            sorted_d = sorted(durations)
            n = len(sorted_d)
            duration_stats = {
                "avg_ms": round(sum(sorted_d) / n, 1),
                "min_ms": round(sorted_d[0], 1),
                "max_ms": round(sorted_d[-1], 1),
                "p50_ms": round(sorted_d[n // 2], 1),
                "p95_ms": round(sorted_d[int(n * 0.95)], 1) if n > 1 else round(sorted_d[0], 1),
                "count": n,
            }

        return {
            **counters,
            "duration": duration_stats,
            "timestamp": time.time(),
        }

    def get_request_stats(self) -> dict:
        """Get per-endpoint request statistics (Phase 10)."""
        with self._lock:
            stats = {}
            for endpoint, latencies in self._request_latencies.items():
                d = sorted(latencies)
                n = len(d)
                if n > 0:
                    stats[endpoint] = {
                        "count": n,
                        "avg_ms": round(sum(d) / n, 1),
                        "p50_ms": round(d[n // 2], 1),
                        "p95_ms": round(d[int(n * 0.95)], 1) if n > 1 else round(d[0], 1),
                    }
            return stats

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self._lock:
            for key in self._counters:
                self._counters[key] = 0
            self._durations.clear()


# Module-level singleton
_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the singleton metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def reset_metrics_collector() -> None:
    """Reset the singleton (for testing)."""
    global _collector
    _collector = None
