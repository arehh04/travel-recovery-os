"""Stress tests — concurrent missions with mocked service (Phase 9)."""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tros.api.app import create_app
from tros.api.deps import reset_execution_manager, get_execution_manager
from tros.api.settings import reset_settings_cache
from tros.api.rate_limit import reset_rate_limiters


@pytest.fixture(autouse=True)
def _clean():
    reset_settings_cache()
    reset_execution_manager()
    reset_rate_limiters()
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            os.environ.pop(key, None)
    yield
    reset_settings_cache()
    reset_execution_manager()
    reset_rate_limiters()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mocked_manager():
    manager = get_execution_manager()
    mock_service = MagicMock()
    mock_result = MagicMock()
    mock_result.status = "completed"
    mock_result.confidence = 0.9
    mock_result.recommendation = None
    mock_result.alternatives = []
    mock_result.budget = 500.0
    mock_result.recovery = MagicMock(occurred=False, attempts=0, reason="", recovered=False)
    mock_result.conflicts = MagicMock(count=0, has_critical=False)
    mock_result.execution_metadata = MagicMock(
        mission_id="m", execution_id="e", request_id="r", status="COMPLETED", duration_ms=100
    )
    mock_service.run.return_value = mock_result
    manager._service = mock_service
    return manager


class TestConcurrentMissions:
    def test_5_concurrent_missions(self, client, mocked_manager):
        """Submit 5 missions concurrently — all should succeed."""
        results = []
        errors = []

        def submit_mission(i):
            try:
                resp = client.post(
                    "/api/v1/missions",
                    json={
                        "origin": "KUL",
                        "destination": "SIN",
                        "departure_date": "2026-08-20",
                        "traveler_count": 1,
                    },
                    headers={"X-Dev-User-Id": f"user-{i}"},
                )
                results.append(resp.status_code)
            except Exception as e:
                errors.append(str(e))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(submit_mission, i) for i in range(5)]
            for f in futures:
                f.result()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        # All should return 202
        assert all(code == 202 for code in results)

    def test_queue_overflow_behavior(self, client):
        """When max concurrent is low, overflow should be handled gracefully."""
        import os
        os.environ["TR_OS_MAX_CONCURRENT_MISSIONS"] = "1"
        reset_settings_cache()
        reset_execution_manager()
        reset_rate_limiters()

        manager = get_execution_manager()
        mock_service = MagicMock()
        # Make service block
        event = threading.Event()
        mock_service.run.side_effect = lambda **kw: event.wait(timeout=5)
        manager._service = mock_service

        app = create_app()
        tc = TestClient(app)

        # First should succeed
        r1 = tc.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "SIN", "departure_date": "2026-08-20", "traveler_count": 1},
            headers={"X-Dev-User-Id": "user-1"},
        )
        assert r1.status_code == 202

        # Second should get 503 (queue full)
        r2 = tc.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20", "traveler_count": 1},
            headers={"X-Dev-User-Id": "user-2"},
        )
        assert r2.status_code == 503

        event.set()
        manager.shutdown(wait=False)

        # Clean up env
        os.environ.pop("TR_OS_MAX_CONCURRENT_MISSIONS", None)
        reset_settings_cache()
        reset_execution_manager()

    def test_throughput_measurement(self, client, mocked_manager):
        """Measure throughput: how many missions per second."""
        start = time.time()
        n = 10
        for i in range(n):
            client.post(
                "/api/v1/missions",
                json={
                    "origin": "KUL",
                    "destination": "SIN",
                    "departure_date": "2026-08-20",
                    "traveler_count": 1,
                },
                headers={"X-Dev-User-Id": f"user-{i}"},
            )
        elapsed = time.time() - start
        throughput = n / elapsed if elapsed > 0 else n
        # Should handle at least 5 missions per second
        assert throughput > 5, f"Throughput too low: {throughput:.1f} missions/sec"
