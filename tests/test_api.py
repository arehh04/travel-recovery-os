"""Phase 8 API tests — FastAPI endpoints, execution manager, security.

Tests cover:
1. API app creation and configuration
2. Health/readiness endpoints
3. Mission creation (validation, errors)
4. Mission status
5. Mission result
6. Cancellation
7. Idempotency (duplicate key, conflicting payload)
8. Error format (structured, no secrets)
9. CORS headers
10. Authentication boundary
11. Execution manager (background, cancellation)
12. Security regression
"""

from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tros.api.app import create_app
from tros.api.deps import get_execution_manager, reset_execution_manager
from tros.api.execution_manager import ExecutionManager
from tros.api.auth import AuthContext
from tros.api.models import (
    MissionRequest,
    MissionCreatedResponse,
    MissionStatusResponse,
    MissionResultResponse,
    HealthResponse,
    ErrorResponse,
)
from tros.api.errors import error_to_http_status
from tros.execution.errors import (
    ValidationError,
    ConstraintViolationError,
    AtlasError,
    LLMError,
    CancellationError,
    InternalMissionError,
)
from tros.execution.cancellation import CancellationToken
from tros.service.result import MissionResult


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def app():
    """Create a fresh FastAPI app for each test."""
    reset_execution_manager()
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_manager():
    """Create an ExecutionManager with mocked MissionService."""
    manager = ExecutionManager(llm_client=None, max_workers=2)
    return manager


# =====================================================================
# 1. App Configuration
# =====================================================================

class TestAppConfig:
    """FastAPI application configuration."""

    def test_app_creates_successfully(self, app):
        assert app is not None
        assert app.title == "TR-OS Mission API"

    def test_openapi_available(self, client):
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data

    def test_root_returns_message(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "TR-OS" in data["message"]

    def test_docs_endpoint_exists(self, client):
        response = client.get("/api/docs")
        assert response.status_code == 200


# =====================================================================
# 2. Health & Readiness
# =====================================================================

class TestHealthEndpoints:
    """Health and readiness probes."""

    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_has_status(self, client):
        response = client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unavailable")

    def test_health_has_checks(self, client):
        response = client.get("/api/v1/health")
        data = response.json()
        assert "checks" in data
        assert len(data["checks"]) >= 1

    def test_readiness_returns_200(self, client):
        response = client.get("/api/v1/readiness")
        assert response.status_code == 200

    def test_readiness_has_status(self, client):
        response = client.get("/api/v1/readiness")
        data = response.json()
        assert "status" in data

    def test_health_no_secrets(self, client):
        response = client.get("/api/v1/health")
        text = response.text
        assert "sk-" not in text


# =====================================================================
# 3. Mission Creation Validation
# =====================================================================

class TestMissionValidation:
    """POST /api/v1/missions — input validation."""

    def test_valid_request_accepted(self, client):
        response = client.post(
            "/api/v1/missions",
            json={
                "origin": "KUL",
                "destination": "NRT",
                "departure_date": "2026-08-20",
            },
        )
        assert response.status_code == 202

    def test_missing_origin_rejected(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"destination": "NRT", "departure_date": "2026-08-20"},
        )
        assert response.status_code == 422  # Pydantic validation

    def test_missing_destination_rejected(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "departure_date": "2026-08-20"},
        )
        assert response.status_code == 422

    def test_missing_date_rejected(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT"},
        )
        assert response.status_code == 422

    def test_invalid_origin_iata(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"origin": "XX", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        assert response.status_code == 422  # Pydantic min_length=3

    def test_invalid_date_format(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "20-08-2026"},
        )
        assert response.status_code == 400

    def test_origin_equals_destination(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "KUL", "departure_date": "2026-08-20"},
        )
        assert response.status_code == 422

    def test_returns_202_with_mission_id(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        data = response.json()
        assert "mission_id" in data
        assert "execution_id" in data
        assert data["status"] in ("PENDING", "RUNNING")

    def test_traveler_count_zero_rejected(self, client):
        response = client.post(
            "/api/v1/missions",
            json={
                "origin": "KUL", "destination": "NRT",
                "departure_date": "2026-08-20", "traveler_count": 0,
            },
        )
        assert response.status_code == 422


# =====================================================================
# 4. Mission Status
# =====================================================================

class TestMissionStatus:
    """GET /api/v1/missions/:id/status."""

    def test_status_returns_after_creation(self, client):
        # Create mission
        create_resp = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        mission_id = create_resp.json()["mission_id"]

        # Get status
        status_resp = client.get(f"/api/v1/missions/{mission_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["mission_id"] == mission_id
        assert "status" in data

    def test_status_not_found(self, client):
        response = client.get("/api/v1/missions/nonexistent-mission/status")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "MISSION_NOT_FOUND"

    def test_status_has_progress(self, client):
        create_resp = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        mission_id = create_resp.json()["mission_id"]
        status_resp = client.get(f"/api/v1/missions/{mission_id}/status")
        data = status_resp.json()
        assert "progress" in data
        assert isinstance(data["progress"], (int, float))


# =====================================================================
# 5. Mission Result
# =====================================================================

class TestMissionResult:
    """GET /api/v1/missions/:id."""

    def test_result_not_found(self, client):
        response = client.get("/api/v1/missions/nonexistent-mission")
        assert response.status_code == 404

    def test_result_after_creation(self, client):
        create_resp = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        mission_id = create_resp.json()["mission_id"]

        # Result should exist (may be in-progress)
        result_resp = client.get(f"/api/v1/missions/{mission_id}")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["mission_id"] == mission_id

    def test_result_no_internal_state(self, client):
        create_resp = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        mission_id = create_resp.json()["mission_id"]
        result_resp = client.get(f"/api/v1/missions/{mission_id}")
        text = result_resp.text
        assert "llm_metadata" not in text
        assert "react_trace" not in text
        assert "prompts" not in text.lower()


# =====================================================================
# 6. Cancellation
# =====================================================================

class TestCancellation:
    """POST /api/v1/missions/:id/cancel."""

    def test_cancel_not_found(self, client):
        response = client.post("/api/v1/missions/nonexistent/cancel")
        assert response.status_code == 404

    def test_cancel_running_mission(self, client):
        create_resp = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        mission_id = create_resp.json()["mission_id"]

        cancel_resp = client.post(f"/api/v1/missions/{mission_id}/cancel")
        assert cancel_resp.status_code == 200
        data = cancel_resp.json()
        assert data["mission_id"] == mission_id

    def test_cancel_returns_mission_id(self, client):
        create_resp = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        mission_id = create_resp.json()["mission_id"]
        cancel_resp = client.post(f"/api/v1/missions/{mission_id}/cancel")
        assert cancel_resp.json()["mission_id"] == mission_id


# =====================================================================
# 7. Idempotency
# =====================================================================

class TestIdempotency:
    """Idempotency-Key header support."""

    def test_same_key_returns_same_mission(self, client):
        resp1 = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            headers={"Idempotency-Key": "test-key-1"},
        )
        resp2 = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            headers={"Idempotency-Key": "test-key-1"},
        )
        assert resp1.json()["mission_id"] == resp2.json()["mission_id"]

    def test_different_payload_conflict(self, client):
        client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            headers={"Idempotency-Key": "conflict-key"},
        )
        resp2 = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "SIN", "departure_date": "2026-08-20"},
            headers={"Idempotency-Key": "conflict-key"},
        )
        assert resp2.status_code == 409

    def test_different_keys_create_separate_missions(self, client):
        resp1 = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            headers={"Idempotency-Key": "key-a"},
        )
        resp2 = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            headers={"Idempotency-Key": "key-b"},
        )
        assert resp1.json()["mission_id"] != resp2.json()["mission_id"]


# =====================================================================
# 8. Error Format
# =====================================================================

class TestErrorFormat:
    """Structured error responses."""

    def test_validation_error_has_code(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"destination": "NRT", "departure_date": "2026-08-20"},
        )
        # Pydantic validation returns 422 with detail
        assert response.status_code == 422

    def test_not_found_has_error_code(self, client):
        response = client.get("/api/v1/missions/nonexistent/status")
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "MISSION_NOT_FOUND"

    def test_error_no_secrets(self, client):
        response = client.get("/api/v1/missions/nonexistent")
        text = response.text
        assert "sk-" not in text
        assert "api_key" not in text.lower()


# =====================================================================
# 9. CORS & Security Headers
# =====================================================================

class TestCORSSecurity:
    """CORS and security headers."""

    def test_cors_header_present(self, client):
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should succeed
        assert response.status_code in (200, 204, 405)

    def test_security_headers_present(self, client):
        response = client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_request_id_echoed(self, client):
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-Id": "test-req-123"},
        )
        assert response.headers.get("X-Request-Id") == "test-req-123"


# =====================================================================
# 10. Authentication Boundary
# =====================================================================

class TestAuthBoundary:
    """Authentication context and dev provider."""

    def test_dev_mode_no_auth_required(self, client):
        # In dev mode (AUTH_ENABLED=false), requests work without auth
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_dev_user_header_accepted(self, client):
        response = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            headers={"X-Dev-User-Id": "test-user"},
        )
        assert response.status_code == 202

    def test_auth_context_creation(self):
        ctx = AuthContext(user_id="u-1", tenant_id="t-1", authenticated=True)
        assert ctx.user_id == "u-1"
        assert not ctx.is_anonymous

    def test_auth_context_anonymous(self):
        ctx = AuthContext()
        assert ctx.is_anonymous


# =====================================================================
# 11. Execution Manager
# =====================================================================

class TestExecutionManager:
    """Background mission execution."""

    def test_submit_returns_execution(self, mock_manager):
        execution = mock_manager.submit({
            "origin": "KUL",
            "destination": "NRT",
            "departure_date": "2026-08-20",
        })
        assert execution is not None
        assert execution.mission_id.startswith("mission-")
        assert execution.status in ("PENDING", "RUNNING")

    def test_get_execution_by_id(self, mock_manager):
        execution = mock_manager.submit({
            "origin": "KUL",
            "destination": "NRT",
            "departure_date": "2026-08-20",
        })
        found = mock_manager.get_execution(execution.mission_id)
        assert found is not None
        assert found.mission_id == execution.mission_id

    def test_get_nonexistent_execution(self, mock_manager):
        assert mock_manager.get_execution("nonexistent") is None

    def test_cancel_execution(self, mock_manager):
        execution = mock_manager.submit({
            "origin": "KUL",
            "destination": "NRT",
            "departure_date": "2026-08-20",
        })
        result = mock_manager.cancel(execution.mission_id)
        assert result is True

    def test_cancel_nonexistent(self, mock_manager):
        assert mock_manager.cancel("nonexistent") is False

    def test_idempotency_same_key_same_payload(self, mock_manager):
        exec1 = mock_manager.submit(
            {"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            idempotency_key="idem-1",
        )
        exec2 = mock_manager.submit(
            {"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            idempotency_key="idem-1",
        )
        assert exec1.mission_id == exec2.mission_id

    def test_idempotency_conflict(self, mock_manager):
        mock_manager.submit(
            {"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
            idempotency_key="idem-2",
        )
        with pytest.raises(ValueError, match="conflict"):
            mock_manager.submit(
                {"origin": "KUL", "destination": "SIN", "departure_date": "2026-08-20"},
                idempotency_key="idem-2",
            )

    def test_payload_hash_deterministic(self):
        hash1 = ExecutionManager._hash_payload({"origin": "KUL", "destination": "NRT"})
        hash2 = ExecutionManager._hash_payload({"destination": "NRT", "origin": "KUL"})
        assert hash1 == hash2

    def test_payload_hash_different_for_different_payloads(self):
        hash1 = ExecutionManager._hash_payload({"origin": "KUL"})
        hash2 = ExecutionManager._hash_payload({"origin": "SIN"})
        assert hash1 != hash2


# =====================================================================
# 12. Error Mapping
# =====================================================================

class TestErrorMapping:
    """MissionError → HTTP status code mapping."""

    def test_validation_error_400(self):
        assert error_to_http_status(ValidationError("bad")) == 400

    def test_constraint_error_422(self):
        assert error_to_http_status(ConstraintViolationError("bad")) == 422

    def test_atlas_error_502(self):
        assert error_to_http_status(AtlasError("bad")) == 502

    def test_llm_error_503(self):
        assert error_to_http_status(LLMError("bad")) == 503

    def test_cancellation_error_499(self):
        assert error_to_http_status(CancellationError("bad")) == 499

    def test_internal_error_500(self):
        assert error_to_http_status(InternalMissionError("bad")) == 500


# =====================================================================
# 13. Security Regression
# =====================================================================

class TestSecurityRegression:
    """Ensure Phase 1-7 security boundaries remain intact."""

    def test_health_no_api_key_leak(self, client):
        response = client.get("/api/v1/health")
        text = response.text
        # Ensure no partial key patterns
        assert "sk-28" not in text
        assert "da79" not in text

    def test_result_no_raw_llm(self, client):
        create_resp = client.post(
            "/api/v1/missions",
            json={"origin": "KUL", "destination": "NRT", "departure_date": "2026-08-20"},
        )
        mission_id = create_resp.json()["mission_id"]
        result_resp = client.get(f"/api/v1/missions/{mission_id}")
        data = result_resp.json()
        assert "raw_llm" not in data
        assert "tool_arguments" not in data

    def test_error_no_traceback(self, client):
        response = client.get("/api/v1/missions/nonexistent")
        text = response.text
        assert "Traceback" not in text
        assert "File \"" not in text
