"""Tests for Phase 9 production configuration layer."""

import os
import pytest
from pydantic import ValidationError

from tros.api.settings import (
    AuthMode,
    Environment,
    Settings,
    get_settings,
    reset_settings_cache,
)


@pytest.fixture(autouse=True)
def _clear_settings():
    """Reset settings cache before each test."""
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove TR_OS_ env vars to isolate tests."""
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            monkeypatch.delenv(key, raising=False)


class TestSettingsDefaults:
    def test_default_environment(self):
        s = Settings()
        assert s.environment == Environment.DEVELOPMENT

    def test_default_host(self):
        s = Settings()
        assert s.api_host == "0.0.0.0"

    def test_default_port(self):
        s = Settings()
        assert s.api_port == 8000

    def test_default_max_workers(self):
        s = Settings()
        assert s.max_workers == 4

    def test_default_rate_limit(self):
        s = Settings()
        assert s.rate_limit_rpm == 60

    def test_default_max_body_size(self):
        s = Settings()
        assert s.max_body_size == 1024 * 1024

    def test_default_sse_heartbeat(self):
        s = Settings()
        assert s.sse_heartbeat_sec == 15

    def test_default_idempotency_ttl(self):
        s = Settings()
        assert s.idempotency_ttl_sec == 3600


class TestSettingsEnvironmentOverrides:
    def test_env_port(self, monkeypatch):
        monkeypatch.setenv("TR_OS_API_PORT", "9000")
        s = Settings()
        assert s.api_port == 9000

    def test_env_cors_origins(self, monkeypatch):
        monkeypatch.setenv("TR_OS_CORS_ORIGINS", "https://example.com,https://app.com")
        s = Settings()
        assert s.cors_origins_list == ["https://example.com", "https://app.com"]

    def test_env_environment(self, monkeypatch):
        monkeypatch.setenv("TR_OS_ENVIRONMENT", "testing")
        s = Settings()
        assert s.environment == Environment.TESTING

    def test_env_auth_mode(self, monkeypatch):
        monkeypatch.setenv("TR_OS_AUTH_MODE", "bearer")
        s = Settings()
        assert s.auth_mode == AuthMode.BEARER


class TestSettingsProductionValidation:
    def test_production_wildcard_cors_rejected(self, monkeypatch):
        monkeypatch.setenv("TR_OS_ENVIRONMENT", "production")
        monkeypatch.setenv("TR_OS_CORS_ORIGINS", "*")
        with pytest.raises(ValidationError, match="wildcard|CORS|cors_origins"):
            Settings()

    def test_production_bearer_without_secret_rejected(self, monkeypatch):
        monkeypatch.setenv("TR_OS_ENVIRONMENT", "production")
        monkeypatch.setenv("TR_OS_AUTH_MODE", "bearer")
        # No auth secret set
        with pytest.raises(ValidationError, match="AUTH_SECRET"):
            Settings()

    def test_production_bearer_with_secret_accepted(self, monkeypatch):
        monkeypatch.setenv("TR_OS_ENVIRONMENT", "production")
        monkeypatch.setenv("TR_OS_AUTH_MODE", "bearer")
        monkeypatch.setenv("TR_OS_AUTH_SECRET", "my-secret-key")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-validkey123456789012345")
        monkeypatch.setenv("TR_OS_ATLAS_AUTH_TOKEN", "valid-atlas-token")
        s = Settings()
        assert s.auth_mode == AuthMode.BEARER
        assert s.auth_secret == "my-secret-key"

    def test_production_valid_config(self, monkeypatch):
        monkeypatch.setenv("TR_OS_ENVIRONMENT", "production")
        monkeypatch.setenv("TR_OS_AUTH_MODE", "dev")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-validkey123456789012345")
        monkeypatch.setenv("TR_OS_ATLAS_AUTH_TOKEN", "valid-atlas-token")
        s = Settings()
        assert s.is_production
        assert not s.is_development

    def test_development_allows_wildcard_cors(self):
        s = Settings(cors_origins="*")
        assert "*" in s.cors_origins_list

    def test_is_development(self):
        s = Settings()
        assert s.is_development
        assert not s.is_production


class TestSettingsSingleton:
    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset_clears_cache(self):
        s1 = get_settings()
        reset_settings_cache()
        s2 = get_settings()
        assert s1 is not s2
