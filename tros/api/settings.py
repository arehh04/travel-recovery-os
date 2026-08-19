"""Production configuration layer — Pydantic settings with env separation (Phase 9).

Provides a validated, typed configuration with environment separation:
- development: relaxed auth, localhost origins
- testing: deterministic defaults
- production: strict validation, no wildcard CORS, required secrets

All secrets loaded from environment variables, never hardcoded.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class AuthMode(str, Enum):
    DEV = "dev"
    BEARER = "bearer"


class Settings(BaseSettings):
    """TR-OS application settings.

    All values can be overridden via environment variables with TR_OS_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="TR_OS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Non-prefixed env vars (external services)
    @model_validator(mode="before")
    @classmethod
    def load_external_env(cls, data: dict) -> dict:
        """Load non-prefixed environment variables for external services."""
        if not data.get("deepseek_api_key"):
            import os
            val = os.environ.get("DEEPSEEK_API_KEY", "")
            if val:
                data["deepseek_api_key"] = val
        return data

    # Environment
    environment: Environment = Environment.DEVELOPMENT

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,OPTIONS"
    cors_allow_headers: str = "Content-Type,Authorization,Idempotency-Key,X-Dev-User-Id,X-Request-Id"

    # Authentication
    auth_mode: AuthMode = AuthMode.DEV
    auth_secret: str = ""  # HMAC secret for bearer token validation

    # LLM
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"

    # Timeouts (seconds)
    mission_timeout_sec: int = 120
    llm_timeout_sec: int = 60
    atlas_timeout_sec: int = 30

    # Recovery
    max_recovery_attempts: int = 2

    # SSE
    sse_heartbeat_sec: int = 15
    sse_max_connection_sec: int = 600  # 10 minutes

    # Execution
    max_workers: int = 4
    max_concurrent_missions: int = 10
    idempotency_ttl_sec: int = 3600  # 1 hour

    # Rate limiting
    rate_limit_rpm: int = 60
    max_body_size: int = 1024 * 1024  # 1MB

    # Database (Phase 10)
    database_url: str = "data/tros.db"  # SQLite file path
    worker_count: int = 1  # Must remain 1 in production (in-process state)

    # External service tokens (Phase 10)
    atlas_auth_token: str = ""  # Atlas API authentication token
    deepseek_api_key: str = ""  # DeepSeek API key (from DEEPSEEK_API_KEY env)

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_allow_methods_list(self) -> list[str]:
        return [m.strip() for m in self.cors_allow_methods.split(",") if m.strip()]

    @property
    def cors_allow_headers_list(self) -> list[str]:
        return [h.strip() for h in self.cors_allow_headers.split(",") if h.strip()]

    @model_validator(mode="after")
    def validate_production(self):
        """Production-specific validation."""
        if self.environment == Environment.PRODUCTION:
            # No wildcard CORS in production
            if "*" in self.cors_origins_list:
                raise ValueError(
                    "Production environment must not allow wildcard CORS origins"
                )
            # Auth secret required for bearer mode
            if self.auth_mode == AuthMode.BEARER and not self.auth_secret:
                raise ValueError(
                    "TR_OS_AUTH_SECRET is required in production with bearer auth mode"
                )
            # Port sanity
            if self.api_port < 1 or self.api_port > 65535:
                raise ValueError(f"Invalid API port: {self.api_port}")
            # DeepSeek API key validation
            if not self.deepseek_api_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY is required in production"
                )
            if self.deepseek_api_key.startswith("sk-your"):
                raise ValueError(
                    "DEEPSEEK_API_KEY must not be a placeholder value"
                )
            # Atlas auth token
            if not self.atlas_auth_token:
                raise ValueError(
                    "TR_OS_ATLAS_AUTH_TOKEN is required in production"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def auth_enabled(self) -> bool:
        """Auth is always enabled in production, optional in development."""
        if self.is_production:
            return True
        return self.auth_mode != AuthMode.DEV or bool(self.auth_secret)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings (singleton)."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the settings cache (for testing)."""
    get_settings.cache_clear()
