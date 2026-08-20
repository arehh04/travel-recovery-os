"""Tests for Phase 9 SSE hardening."""

import os

import pytest

from tros.api.routes.events import _format_sse, _next_event_id, _sanitize_event
from tros.api.settings import reset_settings_cache


@pytest.fixture(autouse=True)
def _clean():
    reset_settings_cache()
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            os.environ.pop(key, None)
    yield
    reset_settings_cache()


class TestSSEFormat:
    def test_format_sse_basic(self):
        result = _format_sse("mission.running", {"mission_id": "m1"}, "42")
        assert "id: 42" in result
        assert "event: mission.running" in result
        assert '"mission_id": "m1"' in result
        assert result.endswith("\n\n")

    def test_format_sse_no_id(self):
        result = _format_sse("heartbeat", {"type": "heartbeat"})
        assert "id:" not in result
        assert "event: heartbeat" in result

    def test_event_ids_monotonic(self):
        """Event IDs should be monotonically increasing."""
        ids = [_next_event_id() for _ in range(5)]
        # All unique
        assert len(set(ids)) == 5
        # All numeric and increasing
        int_ids = [int(i) for i in ids]
        assert int_ids == sorted(int_ids)
        assert all(int_ids[i] < int_ids[i + 1] for i in range(len(int_ids) - 1))


class TestSanitizeEvent:
    def test_no_secrets_in_events(self):
        """Sanitizer should strip sensitive fields."""
        event = {
            "type": "mission.progress",
            "mission_id": "m1",
            "prompt": "Find flights from KUL to SIN",
            "raw_llm": "some raw output",
            "api_key": "sk-secret",
            "phase": "searching",
        }
        sanitized = _sanitize_event(event)
        assert "prompt" not in sanitized
        assert "raw_llm" not in sanitized
        assert "api_key" not in sanitized
        assert sanitized["type"] == "mission.progress"
        assert sanitized["mission_id"] == "m1"
        assert sanitized["phase"] == "searching"

    def test_normal_fields_preserved(self):
        event = {"type": "mission.progress", "progress": 50, "phase": "ranking"}
        sanitized = _sanitize_event(event)
        assert sanitized == event


class TestTerminalEvents:
    def test_terminal_event_types(self):
        from tros.api.routes.events import _TERMINAL_EVENTS
        assert "mission.completed" in _TERMINAL_EVENTS
        assert "mission.failed" in _TERMINAL_EVENTS
        assert "mission.cancelled" in _TERMINAL_EVENTS
        assert "mission.progress" not in _TERMINAL_EVENTS


class TestDisconnectDetection:
    def test_sanitize_stack_trace(self):
        """Stack traces should be stripped."""
        event = {"type": "error", "stack_trace": "Traceback..."}
        sanitized = _sanitize_event(event)
        assert "stack_trace" not in sanitized

    def test_sanitize_token(self):
        """Token fields should be stripped."""
        event = {"type": "auth", "token": "Bearer abc123"}
        sanitized = _sanitize_event(event)
        assert "token" not in sanitized
        assert "secret" not in sanitized

    def test_sanitize_secret(self):
        event = {"type": "config", "secret": "my-secret-value"}
        sanitized = _sanitize_event(event)
        assert "secret" not in sanitized
