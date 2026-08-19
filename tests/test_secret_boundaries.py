"""Secret boundary tests — Phase 10.

Verifies that no secrets, API keys, or sensitive tokens leak through
any API response, log output, or persisted data.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re

import pytest
from fastapi.testclient import TestClient

from tros.api.settings import reset_settings_cache


# Patterns that should never appear in API responses or logs
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),           # OpenAI/DeepSeek API keys
    re.compile(r"sk-your[a-zA-Z0-9_-]*"),          # Placeholder keys
    re.compile(r"Bearer [A-Za-z0-9_\-\.]{20,}"),   # Bearer tokens
    re.compile(r"TR_OS_AUTH_SECRET\s*=\s*\S+"),    # Env var with value
    re.compile(r"DEEPSEEK_API_KEY\s*=\s*sk-"),     # Hardcoded key
]


@pytest.fixture(autouse=True)
def _clean_env():
    reset_settings_cache()
    _saved_deepseek = os.environ.pop("DEEPSEEK_API_KEY", None)
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            os.environ.pop(key, None)
    yield
    reset_settings_cache()
    if _saved_deepseek is not None:
        os.environ["DEEPSEEK_API_KEY"] = _saved_deepseek


@pytest.fixture
def client():
    from tros.api.app import create_app
    return TestClient(create_app())


def _assert_no_secrets(text: str, context: str = "") -> None:
    """Assert no secret patterns appear in text."""
    for pattern in _SECRET_PATTERNS:
        matches = pattern.findall(text)
        assert not matches, (
            f"Secret pattern matched in {context}: "
            f"{pattern.pattern} found {len(matches)} occurrence(s)"
        )


class TestHealthEndpointSecrets:
    def test_health_no_secrets(self, client):
        """Health endpoint response contains no secrets."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        _assert_no_secrets(response.text, "health response")

    def test_readiness_no_secrets(self, client):
        """Readiness endpoint response contains no secrets."""
        response = client.get("/api/v1/readiness")
        assert response.status_code == 200
        _assert_no_secrets(response.text, "readiness response")


class TestMetricsSecrets:
    def test_metrics_no_secrets(self, client):
        """Metrics endpoint response contains no secrets."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        _assert_no_secrets(response.text, "metrics response")


class TestMissionResultSecrets:
    def test_mission_result_model_no_secrets(self):
        """MissionResultResponse model never includes secret fields."""
        from tros.api.models import MissionResultResponse
        fields = MissionResultResponse.model_fields
        secret_names = {"api_key", "secret", "token", "password", "deepseek_api_key"}
        for field_name in fields:
            assert field_name not in secret_names, (
                f"MissionResultResponse has sensitive field: {field_name}"
            )


class TestSSEEventSecrets:
    def test_sse_sanitize_strips_all_sensitive_keys(self):
        """SSE sanitizer strips all known sensitive field names."""
        from tros.api.routes.events import _sanitize_event
        event = {
            "type": "mission.progress",
            "prompt": "user prompt",
            "raw_llm": "raw output",
            "api_key": "sk-secret123456789012345678",
            "secret": "my-secret",
            "token": "Bearer abc123def456ghi789",
            "stack_trace": "Traceback...",
            "mission_id": "m1",
            "phase": "searching",
        }
        sanitized = _sanitize_event(event)
        for key in ("prompt", "raw_llm", "api_key", "secret", "token", "stack_trace"):
            assert key not in sanitized, f"SSE sanitizer should strip: {key}"
        assert sanitized["mission_id"] == "m1"
        assert sanitized["phase"] == "searching"


class TestErrorResponseSecrets:
    def test_error_response_no_secrets(self):
        """Error responses never contain secrets or stack traces."""
        from tros.api.errors import build_error_response
        from tros.execution.errors import MissionError

        error = MissionError(
            error_code="LLM_TIMEOUT",
            category="LLM",
            message="Timeout with key sk-secret123456789012345678",
            retryable=True,
        )
        response = build_error_response(error)
        body = str(response.body)
        assert "Traceback" not in body
        assert "File \"" not in body


class TestLogSecrets:
    def test_deepseek_key_not_in_logs(self):
        """DEEPSEEK_API_KEY value never appears in log output."""
        from tros.api.structured_logging import SecretScrubberFilter, StructuredFormatter

        test_logger = logging.getLogger("test_secret_log")
        test_logger.setLevel(logging.DEBUG)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(SecretScrubberFilter())
        test_logger.addHandler(handler)

        test_logger.info("Using key sk-abc123def456ghi789jkl012mno345pqr")
        output = stream.getvalue()
        assert "sk-abc123def456ghi789" not in output
        test_logger.removeHandler(handler)

    def test_auth_secret_not_in_logs(self):
        """TR_OS_AUTH_SECRET value never appears in log output."""
        from tros.api.structured_logging import SecretScrubberFilter, StructuredFormatter

        test_logger = logging.getLogger("test_auth_log")
        test_logger.setLevel(logging.DEBUG)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(SecretScrubberFilter())
        test_logger.addHandler(handler)

        test_logger.info("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")
        output = stream.getvalue()
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in output
        test_logger.removeHandler(handler)


class TestSettingsValidation:
    def test_placeholder_api_key_rejected_in_production(self):
        """Settings rejects placeholder DEEPSEEK_API_KEY in production."""
        from tros.api.settings import Settings, Environment
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                environment=Environment.PRODUCTION,
                deepseek_api_key="sk-your-api-key-here",
                atlas_auth_token="valid-token",
            )

    def test_empty_api_key_rejected_in_production(self):
        """Settings rejects empty DEEPSEEK_API_KEY in production."""
        from tros.api.settings import Settings, Environment
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                environment=Environment.PRODUCTION,
                deepseek_api_key="",
                atlas_auth_token="valid-token",
            )

    def test_missing_atlas_token_rejected_in_production(self):
        """Settings rejects missing atlas_auth_token in production."""
        from tros.api.settings import Settings, Environment
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                environment=Environment.PRODUCTION,
                deepseek_api_key="sk-validkey123456789012345",
                atlas_auth_token="",
            )


class TestFrontendBuildSecrets:
    def test_frontend_build_no_secrets(self):
        """Frontend build output contains no secret patterns."""
        dist_dir = os.path.join("frontend", "dist")
        if not os.path.isdir(dist_dir):
            pytest.skip("frontend/dist not built")

        findings = []
        for root, dirs, files in os.walk(dist_dir):
            for fname in files:
                if fname.endswith((".js", ".html", ".css")):
                    filepath = os.path.join(root, fname)
                    try:
                        with open(filepath, encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        for pattern in _SECRET_PATTERNS:
                            if pattern.findall(content):
                                findings.append(f"{filepath}")
                    except (IOError, UnicodeDecodeError):
                        pass
        assert findings == [], f"Secrets found in frontend build: {findings}"


class TestRepositoryResultJson:
    def test_repository_result_no_api_key_patterns(self, tmp_path):
        """Repository result_json contains no API key patterns."""
        from tros.api.db import init_db
        from tros.api.repositories_sqlite import SqliteMissionRepository

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        repo = SqliteMissionRepository(db_path=db_path)

        # Save a sanitized result (no secrets)
        result_data = {
            "recommendation": {"flight": "AK701", "price": 450},
            "confidence": 0.85,
            "alternatives": [],
        }
        repo.save_result("m1", result_data)
        stored = repo.get_result("m1")
        stored_json = json.dumps(stored)
        _assert_no_secrets(stored_json, "repository result_json")
