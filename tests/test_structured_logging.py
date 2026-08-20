"""Tests for Phase 9 structured logging."""

import json
import logging

from tros.api.structured_logging import (
    SecretScrubberFilter,
    StructuredFormatter,
    scrub_secrets,
    setup_structured_logging,
)


class TestSecretScrubber:
    def test_strips_api_keys(self):
        text = "Using API key sk-abc123def456ghi789jkl012mno345 for auth"
        result = scrub_secrets(text)
        assert "sk-abc" not in result
        assert "[REDACTED]" in result

    def test_strips_bearer_tokens(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        result = scrub_secrets(text)
        assert "eyJhbGciOi" not in result
        assert "[REDACTED]" in result

    def test_strips_json_api_key(self):
        text = '{"api_key": "sk-secret1234567890abcdef", "other": "value"}'
        result = scrub_secrets(text)
        assert "sk-secret" not in result

    def test_strips_json_secret(self):
        text = '{"secret": "my-secret-value", "data": "ok"}'
        result = scrub_secrets(text)
        assert "my-secret-value" not in result

    def test_preserves_normal_text(self):
        text = "Mission completed for KUL to SIN"
        result = scrub_secrets(text)
        assert result == text


class TestStructuredFormatter:
    def test_json_format_output(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_extra_fields(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Mission done",
            args=None,
            exc_info=None,
        )
        record.mission_id = "m-123"
        record.duration_ms = 4500
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["mission_id"] == "m-123"
        assert parsed["duration_ms"] == 4500


class TestSecretScrubberFilter:
    def test_filter_scrubs_message(self):
        filt = SecretScrubberFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Using sk-abc123def456ghi789jkl012mno345",
            args=None,
            exc_info=None,
        )
        filt.filter(record)
        assert "sk-abc" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_filter_scrubs_args(self):
        filt = SecretScrubberFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Token: %s",
            args=("Bearer eyJhbGciOiJIUzI1NiIs",),
            exc_info=None,
        )
        filt.filter(record)
        assert "eyJhbGciOi" not in str(record.args)


class TestSetup:
    def test_setup_doesnt_raise(self):
        """setup_structured_logging should not raise."""
        setup_structured_logging("INFO")
