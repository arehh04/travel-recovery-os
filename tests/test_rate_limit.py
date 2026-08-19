"""Tests for Phase 9 rate limiting & abuse protection."""

import os
import time

import pytest

from tros.api.rate_limit import (
    InMemoryRateLimiter,
    MaxConcurrencyGuard,
    reset_rate_limiters,
)
from tros.api.settings import reset_settings_cache


@pytest.fixture(autouse=True)
def _clean():
    reset_settings_cache()
    reset_rate_limiters()
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            os.environ.pop(key, None)
    yield
    reset_settings_cache()
    reset_rate_limiters()


class TestInMemoryRateLimiter:
    def test_within_limit_passes(self):
        limiter = InMemoryRateLimiter(rpm=10)
        for i in range(10):
            allowed, info = limiter.is_allowed("user-1")
            assert allowed is True
            assert info["remaining"] == 10 - i - 1

    def test_rate_limit_exceeded(self):
        limiter = InMemoryRateLimiter(rpm=3)
        for _ in range(3):
            limiter.is_allowed("user-1")
        allowed, info = limiter.is_allowed("user-1")
        assert allowed is False
        assert info["remaining"] == 0

    def test_different_keys_independent(self):
        limiter = InMemoryRateLimiter(rpm=2)
        limiter.is_allowed("user-1")
        limiter.is_allowed("user-1")
        # user-1 is now limited, but user-2 should still work
        allowed, _ = limiter.is_allowed("user-2")
        assert allowed is True

    def test_rate_limit_reset_after_window(self):
        limiter = InMemoryRateLimiter(rpm=2, window_sec=0.1)
        limiter.is_allowed("user-1")
        limiter.is_allowed("user-1")
        # Should be blocked now
        allowed, _ = limiter.is_allowed("user-1")
        assert allowed is False
        # Wait for window to expire
        time.sleep(0.15)
        allowed, _ = limiter.is_allowed("user-1")
        assert allowed is True


class TestMaxConcurrencyGuard:
    def test_acquire_within_limit(self):
        guard = MaxConcurrencyGuard(max_concurrent=2)
        assert guard.acquire() is True
        assert guard.acquire() is True

    def test_acquire_exceeded(self):
        guard = MaxConcurrencyGuard(max_concurrent=2)
        guard.acquire()
        guard.acquire()
        assert guard.acquire() is False

    def test_release_allows_new_acquire(self):
        guard = MaxConcurrencyGuard(max_concurrent=1)
        guard.acquire()
        assert guard.acquire() is False
        guard.release()
        assert guard.acquire() is True

    def test_active_count(self):
        guard = MaxConcurrencyGuard(max_concurrent=5)
        guard.acquire()
        guard.acquire()
        assert guard.active == 2
        guard.release()
        assert guard.active == 1

    def test_concurrent_missions_rejected(self):
        guard = MaxConcurrencyGuard(max_concurrent=2)
        guard.acquire()
        guard.acquire()
        # Third request should be rejected
        assert guard.acquire() is False
        guard.release()
        # Now one slot is free
        assert guard.acquire() is True


class TestBodySizeCheck:
    def test_body_too_large_value(self):
        """Verify the max_body_size setting is accessible."""
        from tros.api.settings import get_settings
        settings = get_settings()
        assert settings.max_body_size == 1024 * 1024  # 1MB default
