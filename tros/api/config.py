"""API configuration — backward-compatible aliases over Settings (Phase 8/9).

Phase 8 code imports module-level names from this module.
Phase 9 delegates all values to the validated Settings class.
Existing imports continue to work without changes.
"""

from __future__ import annotations

from tros.api.settings import get_settings


def _load() -> dict:
    """Load settings and expose as module-level names."""
    s = get_settings()
    return {
        "API_HOST": s.api_host,
        "API_PORT": s.api_port,
        "CORS_ORIGINS": s.cors_origins_list,
        "CORS_ALLOW_CREDENTIALS": s.cors_allow_credentials,
        "CORS_ALLOW_METHODS": s.cors_allow_methods_list,
        "CORS_ALLOW_HEADERS": s.cors_allow_headers_list,
        "AUTH_ENABLED": s.auth_enabled,
        "API_LOG_LEVEL": s.log_level,
        "RATE_LIMIT_RPM": s.rate_limit_rpm,
        "MAX_BODY_SIZE": s.max_body_size,
    }


def __getattr__(name: str):
    """Lazy attribute access — re-reads settings on each access."""
    attrs = _load()
    if name in attrs:
        return attrs[name]
    raise AttributeError(f"module 'tros.api.config' has no attribute {name!r}")


# Eagerly expose for static analysis / IDE support
_cfg = _load()
API_HOST: str = _cfg["API_HOST"]
API_PORT: int = _cfg["API_PORT"]
CORS_ORIGINS: list[str] = _cfg["CORS_ORIGINS"]
CORS_ALLOW_CREDENTIALS: bool = _cfg["CORS_ALLOW_CREDENTIALS"]
CORS_ALLOW_METHODS: list[str] = _cfg["CORS_ALLOW_METHODS"]
CORS_ALLOW_HEADERS: list[str] = _cfg["CORS_ALLOW_HEADERS"]
AUTH_ENABLED: bool = _cfg["AUTH_ENABLED"]
API_LOG_LEVEL: str = _cfg["API_LOG_LEVEL"]
RATE_LIMIT_RPM: int = _cfg["RATE_LIMIT_RPM"]
MAX_BODY_SIZE: int = _cfg["MAX_BODY_SIZE"]
