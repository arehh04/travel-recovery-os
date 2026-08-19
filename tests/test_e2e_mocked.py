"""E2E mocked tests — full lifecycle with mocked MissionService (Phase 9).

Tests the complete request → response → poll → result flow
without real DeepSeek/Atlas calls.
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tros.api.app import create_app
from tros.api.deps import reset_execution_manager, get_execution_manager
from tros.api.settings import reset_settings_cache
from tros.api.rate_limit import reset_rate_limiters
from tros.service.result import MissionResult


def _mock_result():
    """Create a mock MissionResult."""
    from dataclasses import dataclass

    @dataclass
    class MockRec:
        flight_number: str = "AK701"
        carrier: str = "AirAsia"
        departure: str = "08:00"
        arrival: str = "09:45"
        duration_minutes: int = 105
        stops: int = 0
        price: float = 72.95
        currency: str = "USD"
        score: float = 0.92

    @dataclass
    class MockRecovery:
        occurred: bool = False
        attempts: int = 0
        reason: str = ""
        recovered: bool = False

    @dataclass
    class MockConflicts:
        count: int = 0
        has_critical: bool = False

    @dataclass
    class MockMeta:
        mission_id: str = "test-mission"
        execution_id: str = "test-exec"
        request_id: str = "test-key"
        status: str = "COMPLETED"
        duration_ms: int = 1500

    return MissionResult(
        mission_id="test-mission",
        execution_id="test-exec",
        status="completed",
        recommendation=MockRec(),
        alternatives=[],
        budget={"total": 500.0, "currency": "USD"},
        confidence=0.85,
        recovery=MockRecovery(),
        conflicts=MockConflicts(),
        execution_metadata=MockMeta(),
    )


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
    """Get the execution manager and mock its service."""
    manager = get_execution_manager()
    mock_service = MagicMock()
    mock_service.run.return_value = _mock_result()
    manager._service = mock_service
    return manager


class TestFullLifecycle:
    def test_create_returns_202(self, client, mocked_manager):
        """POST /missions should return 202 with mission_id."""
        response = client.post(
            "/api/v1/missions",
            json={
                "origin": "KUL",
                "destination": "SIN",
                "departure_date": "2026-08-20",
                "traveler_count": 1,
            },
            headers={"X-Dev-User-Id": "test-user"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "mission_id" in data
        assert data["status"] in ("PENDING", "RUNNING", "COMPLETED")

    def test_poll_status_returns_running(self, client, mocked_manager):
        """GET /missions/:id/status should return current status."""
        # Create mission
        create_resp = client.post(
            "/api/v1/missions",
            json={
                "origin": "KUL",
                "destination": "SIN",
                "departure_date": "2026-08-20",
                "traveler_count": 1,
            },
            headers={"X-Dev-User-Id": "test-user"},
        )
        mission_id = create_resp.json()["mission_id"]

        # Poll status
        time.sleep(0.3)
        status_resp = client.get(
            f"/api/v1/missions/{mission_id}/status",
            headers={"X-Dev-User-Id": "test-user"},
        )
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["mission_id"] == mission_id

    def test_get_result_after_completion(self, client, mocked_manager):
        """GET /missions/:id should return result after completion."""
        create_resp = client.post(
            "/api/v1/missions",
            json={
                "origin": "KUL",
                "destination": "SIN",
                "departure_date": "2026-08-20",
                "traveler_count": 1,
            },
            headers={"X-Dev-User-Id": "test-user"},
        )
        mission_id = create_resp.json()["mission_id"]

        # Wait for completion
        time.sleep(1.0)

        result_resp = client.get(
            f"/api/v1/missions/{mission_id}",
            headers={"X-Dev-User-Id": "test-user"},
        )
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"].upper() in ("COMPLETED", "RUNNING")

    def test_cancel_running_mission(self, client, mocked_manager):
        """POST /missions/:id/cancel should request cancellation."""
        create_resp = client.post(
            "/api/v1/missions",
            json={
                "origin": "KUL",
                "destination": "SIN",
                "departure_date": "2026-08-20",
                "traveler_count": 1,
            },
            headers={"X-Dev-User-Id": "test-user"},
        )
        mission_id = create_resp.json()["mission_id"]

        cancel_resp = client.post(
            f"/api/v1/missions/{mission_id}/cancel",
            headers={"X-Dev-User-Id": "test-user"},
        )
        # Should succeed (either CANCELLING or already terminal)
        assert cancel_resp.status_code == 200

    def test_idempotency_replay(self, client, mocked_manager):
        """Same idempotency key should return same mission_id."""
        body = {
            "origin": "KUL",
            "destination": "SIN",
            "departure_date": "2026-08-20",
            "traveler_count": 1,
        }
        headers = {"X-Dev-User-Id": "test-user", "Idempotency-Key": "same-key-123"}

        resp1 = client.post("/api/v1/missions", json=body, headers=headers)
        resp2 = client.post("/api/v1/missions", json=body, headers=headers)

        assert resp1.json()["mission_id"] == resp2.json()["mission_id"]

    def test_not_found_returns_404(self, client):
        """GET /missions/:nonexistent should return 404."""
        response = client.get(
            "/api/v1/missions/nonexistent",
            headers={"X-Dev-User-Id": "test-user"},
        )
        assert response.status_code == 404

    def test_metrics_endpoint(self, client):
        """GET /api/v1/metrics should return 200."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "missions_submitted" in data

    def test_health_endpoint(self, client):
        """GET /api/v1/health should return 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
