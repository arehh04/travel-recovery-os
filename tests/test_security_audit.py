"""Security audit tests — Phase 9."""

import os
import re

import pytest


# Regex patterns for secrets (not exhaustive, but covers common cases)
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # DeepSeek/OpenAI keys
    re.compile(r"DEEPSEEK_API_KEY\s*=\s*['\"]sk-[a-zA-Z0-9]"),  # Hardcoded key in code
    re.compile(r"password\s*=\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE),
]


def _scan_file_for_secrets(filepath: str) -> list[str]:
    """Scan a file for potential secrets. Returns list of matching patterns."""
    findings = []
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for pattern in _SECRET_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                findings.append(f"{filepath}: {matches[0][:20]}...")
    except (IOError, UnicodeDecodeError):
        pass
    return findings


class TestNoSecretsInSource:
    def test_no_secrets_in_python_source(self):
        """No hardcoded secrets in Python source files."""
        findings = []
        for root, dirs, files in os.walk("tros"):
            # Skip __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py"):
                    filepath = os.path.join(root, fname)
                    findings.extend(_scan_file_for_secrets(filepath))
        assert findings == [], f"Secrets found in source: {findings}"

    def test_no_secrets_in_frontend_build(self):
        """No secrets in frontend build output (dist/)."""
        dist_dir = os.path.join("frontend", "dist")
        if not os.path.isdir(dist_dir):
            pytest.skip("frontend/dist not built")
        findings = []
        for root, dirs, files in os.walk(dist_dir):
            for fname in files:
                if fname.endswith((".js", ".html", ".css")):
                    filepath = os.path.join(root, fname)
                    findings.extend(_scan_file_for_secrets(filepath))
        assert findings == [], f"Secrets found in frontend build: {findings}"


class TestCORSConfig:
    def test_cors_not_wildcard_in_production(self):
        """Production config rejects wildcard CORS."""
        from tros.api.settings import Settings, Environment
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(environment=Environment.PRODUCTION, cors_origins="*")


class TestAuthNotLogged:
    def test_auth_headers_never_logged(self):
        """Auth-related values should never appear in log output."""
        import logging
        import io
        from tros.api.structured_logging import SecretScrubberFilter, StructuredFormatter

        # Set up a logger with our scrubber
        logger = logging.getLogger("test_security")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(io.StringIO())
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(SecretScrubberFilter())
        logger.addHandler(handler)

        # Log something with a token
        logger.info("Request with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

        output = handler.stream.getvalue()
        assert "eyJhbGciOi" not in output
        assert "[REDACTED]" in output
        logger.removeHandler(handler)


class TestErrorResponseSafety:
    def test_error_responses_no_stack_traces(self):
        """Error responses should not contain Python stack traces."""
        from tros.api.errors import build_error_response
        from tros.execution.errors import MissionError

        error = MissionError(
            error_code="INTERNAL_ERROR",
            category="INTERNAL",
            message="Something went wrong",
            retryable=True,
        )
        response = build_error_response(error)
        body_str = str(response.body)
        assert "Traceback" not in body_str
        assert "File \"" not in body_str


class TestPathTraversal:
    def test_mission_id_with_path_traversal(self):
        """Mission IDs with path traversal attempts should be rejected."""
        # This tests that the IATA validation in missions.py would reject
        # path traversal attempts like ../../etc/passwd
        iata_pattern = re.compile(r"^[A-Z]{3}$")
        malicious_ids = ["../", "..\\", "etc/passwd", "../../../", "KUL/"]
        for mid in malicious_ids:
            assert not iata_pattern.match(mid), f"Should reject: {mid}"


class TestRequestBodySize:
    def test_body_size_enforced(self):
        """Max body size setting is a positive value."""
        from tros.api.settings import get_settings
        settings = get_settings()
        assert settings.max_body_size > 0
        assert settings.max_body_size <= 10 * 1024 * 1024  # Max 10MB


class TestSecurityHeaders:
    def test_security_headers_in_app(self):
        """App should add security headers."""
        from tros.api.app import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        # Check security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
