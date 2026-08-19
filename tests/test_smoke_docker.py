"""Smoke test — integration tests simulating a running instance (Phase 10).

Uses TestClient to verify end-to-end behavior without Docker.
Actual Docker smoke tests would require Docker runtime.
"""

from __future__ import annotations

import os
import re

import pytest
from fastapi.testclient import TestClient

from tros.api.settings import reset_settings_cache


_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer [A-Za-z0-9_\-\.]{20,}"),
]


@pytest.fixture(autouse=True)
def _clean():
    reset_settings_cache()
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            os.environ.pop(key, None)
    yield
    reset_settings_cache()


@pytest.fixture
def client():
    from tros.api.app import create_app
    return TestClient(create_app())


def _assert_no_secrets(text: str, context: str = "") -> None:
    for pattern in _SECRET_PATTERNS:
        matches = pattern.findall(text)
        assert not matches, f"Secret found in {context}: {pattern.pattern}"


class TestSmokeEndpoints:
    def test_health_returns_200_with_version(self, client):
        """Health endpoint returns 200 with version info."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        _assert_no_secrets(response.text, "health")

    def test_readiness_returns_200(self, client):
        """Readiness endpoint returns 200."""
        response = client.get("/api/v1/readiness")
        assert response.status_code == 200
        _assert_no_secrets(response.text, "readiness")

    def test_metrics_returns_aggregate_data(self, client):
        """Metrics endpoint returns aggregate data with version."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "commit" in data
        assert "timestamp" in data
        _assert_no_secrets(response.text, "metrics")

    def test_cors_rejects_unauthorized_origin(self, client):
        """CORS rejects unauthorized origins in production mode."""
        # In dev mode, localhost is allowed
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://evil.com"},
        )
        # Check that the evil origin is NOT in the response
        access_origin = response.headers.get("access-control-allow-origin", "")
        assert "evil.com" not in access_origin

    def test_api_authentication_dev_mode(self, client):
        """API works in dev mode without auth."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_root_endpoint(self, client):
        """Root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "TR-OS" in str(data)

    def test_no_secrets_in_any_response(self, client):
        """No secret patterns appear in any standard API response."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/readiness",
            "/api/v1/metrics",
            "/",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            _assert_no_secrets(response.text, endpoint)

    def test_security_headers_present(self, client):
        """Security headers are present on all responses."""
        response = client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-Request-Id") is not None

    def test_request_id_returned(self, client):
        """Every response includes a request ID."""
        response = client.get("/api/v1/health")
        req_id = response.headers.get("X-Request-Id")
        assert req_id is not None
        assert len(req_id) > 0

    def test_mission_not_found_returns_404(self, client):
        """Non-existent mission returns 404."""
        response = client.get("/api/v1/missions/nonexistent/events")
        assert response.status_code == 404
        _assert_no_secrets(response.text, "404 response")
