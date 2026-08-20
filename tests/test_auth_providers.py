"""Tests for Phase 9 auth provider abstraction."""

import os
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from tros.api.auth_providers import (
    BearerTokenProvider,
    DevAuthProvider,
    create_bearer_token,
    get_auth_provider,
)
from tros.api.settings import reset_settings_cache


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Reset settings and clean env vars."""
    reset_settings_cache()
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            monkeypatch.delenv(key, raising=False)
    yield
    reset_settings_cache()


def _make_request(headers: dict | None = None) -> MagicMock:
    """Create a mock Request with the given headers."""
    request = MagicMock()
    request.headers = headers or {}
    return request


class TestDevAuthProvider:
    def test_header_present(self):
        provider = DevAuthProvider()
        request = _make_request({"X-Dev-User-Id": "alice"})
        ctx = provider.authenticate(request)
        assert ctx.user_id == "alice"
        assert ctx.tenant_id == "dev"
        assert ctx.authenticated is True

    def test_header_missing(self):
        provider = DevAuthProvider()
        request = _make_request({})
        ctx = provider.authenticate(request)
        assert ctx.user_id == "dev-user"
        assert ctx.authenticated is True

    def test_anonymous_fallback(self):
        provider = DevAuthProvider()
        request = _make_request({"X-Dev-User-Id": ""})
        ctx = provider.authenticate(request)
        assert ctx.user_id == "dev-user"


class TestBearerTokenProvider:
    SECRET = "test-secret-key"

    def _make_token(self, payload: dict, secret: str | None = None) -> str:
        return create_bearer_token(payload, secret or self.SECRET)

    def test_valid_token(self):
        provider = BearerTokenProvider(self.SECRET)
        token = self._make_token({
            "sub": "user-123",
            "tid": "tenant-1",
            "roles": ["admin"],
            "exp": time.time() + 3600,
        })
        request = _make_request({"Authorization": f"Bearer {token}"})
        ctx = provider.authenticate(request)
        assert ctx.user_id == "user-123"
        assert ctx.tenant_id == "tenant-1"
        assert ctx.roles == ["admin"]
        assert ctx.authenticated is True

    def test_missing_token_401(self):
        provider = BearerTokenProvider(self.SECRET)
        request = _make_request({})
        with pytest.raises(HTTPException) as exc_info:
            provider.authenticate(request)
        assert exc_info.value.status_code == 401

    def test_malformed_token_401(self):
        provider = BearerTokenProvider(self.SECRET)
        request = _make_request({"Authorization": "Bearer not-a-valid-token"})
        with pytest.raises(HTTPException) as exc_info:
            provider.authenticate(request)
        assert exc_info.value.status_code == 401

    def test_expired_token_401(self):
        provider = BearerTokenProvider(self.SECRET)
        token = self._make_token({
            "sub": "user-123",
            "tid": "tenant-1",
            "roles": [],
            "exp": time.time() - 3600,  # expired
        })
        request = _make_request({"Authorization": f"Bearer {token}"})
        with pytest.raises(HTTPException) as exc_info:
            provider.authenticate(request)
        assert exc_info.value.status_code == 401

    def test_wrong_signature_401(self):
        provider = BearerTokenProvider(self.SECRET)
        token = self._make_token(
            {"sub": "user-123", "tid": "t", "roles": [], "exp": time.time() + 3600},
            secret="wrong-secret",
        )
        request = _make_request({"Authorization": f"Bearer {token}"})
        with pytest.raises(HTTPException) as exc_info:
            provider.authenticate(request)
        assert exc_info.value.status_code == 401

    def test_token_not_in_logs(self, caplog):
        """Ensure raw tokens are never logged."""
        provider = BearerTokenProvider(self.SECRET)
        token = self._make_token({
            "sub": "user-123",
            "tid": "tenant-1",
            "roles": [],
            "exp": time.time() + 3600,
        })
        import logging
        with caplog.at_level(logging.DEBUG):
            request = _make_request({"Authorization": f"Bearer {token}"})
            provider.authenticate(request)
        # Verify raw token not in any log message
        for record in caplog.records:
            assert token not in record.getMessage()


class TestAuthProviderFactory:
    def test_dev_mode_returns_dev_provider(self, monkeypatch):
        monkeypatch.setenv("TR_OS_AUTH_MODE", "dev")
        provider = get_auth_provider()
        assert isinstance(provider, DevAuthProvider)

    def test_bearer_mode_returns_bearer_provider(self, monkeypatch):
        monkeypatch.setenv("TR_OS_AUTH_MODE", "bearer")
        monkeypatch.setenv("TR_OS_AUTH_SECRET", "my-secret")
        provider = get_auth_provider()
        assert isinstance(provider, BearerTokenProvider)
