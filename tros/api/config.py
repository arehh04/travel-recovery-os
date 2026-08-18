"""API configuration — environment-driven settings (Phase 8)."""

import os


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# Server
API_HOST: str = _env("TR_OS_API_HOST", "0.0.0.0")
API_PORT: int = int(_env("TR_OS_API_PORT", "8000"))

# CORS
CORS_ORIGINS: list[str] = _env(
    "TR_OS_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "OPTIONS"]
CORS_ALLOW_HEADERS: list[str] = [
    "Content-Type",
    "Authorization",
    "Idempotency-Key",
    "X-Dev-User-Id",
    "X-Request-Id",
]

# Authentication
AUTH_ENABLED: bool = _env("TR_OS_AUTH_ENABLED", "false").lower() == "true"

# Logging
API_LOG_LEVEL: str = _env("TR_OS_LOG_LEVEL", "INFO")

# Rate limiting (requests per minute per IP, 0 = disabled)
RATE_LIMIT_RPM: int = int(_env("TR_OS_RATE_LIMIT_RPM", "60"))

# Request body limit (bytes)
MAX_BODY_SIZE: int = int(_env("TR_OS_MAX_BODY_SIZE", str(1024 * 1024)))  # 1MB
