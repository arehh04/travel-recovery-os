"""Authentication provider abstraction — pluggable auth strategies (Phase 9).

Provides a protocol-based auth system with two built-in providers:
- DevAuthProvider: trusts X-Dev-User-Id header (development only)
- BearerTokenProvider: validates HMAC-SHA256 signed bearer tokens (production)

The factory function selects the provider based on settings.auth_mode.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from base64 import b64decode, b64encode
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request

from tros.api.auth import AuthContext
from tros.api.settings import AuthMode, get_settings

logger = logging.getLogger(__name__)


class AuthProvider(Protocol):
    """Protocol for authentication providers."""

    def authenticate(self, request: Request) -> AuthContext:
        """Authenticate a request and return an AuthContext.

        Raises HTTPException(401) if authentication fails.
        """
        ...


class DevAuthProvider:
    """Development auth provider — trusts X-Dev-User-Id header.

    In development mode, any request with the X-Dev-User-Id header is
    trusted. Missing header falls back to an anonymous dev user.
    """

    def authenticate(self, request: Request) -> AuthContext:
        user_id = request.headers.get("X-Dev-User-Id", "")
        if user_id:
            return AuthContext(
                user_id=user_id,
                tenant_id="dev",
                roles=["developer"],
                authenticated=True,
            )
        # Anonymous dev fallback
        return AuthContext(
            user_id="dev-user",
            tenant_id="dev",
            roles=["developer"],
            authenticated=True,
        )


class BearerTokenProvider:
    """Production auth provider — validates HMAC-SHA256 bearer tokens.

    Token format: base64(JSON payload) + "." + base64(HMAC-SHA256 signature)
    Payload must contain: sub (user_id), tid (tenant_id), roles (list), exp (unix timestamp)
    """

    def __init__(self, secret: str):
        if not secret:
            raise ValueError("BearerTokenProvider requires a non-empty secret")
        self._secret = secret.encode("utf-8")

    def authenticate(self, request: Request) -> AuthContext:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "AUTH_MISSING", "message": "Bearer token required", "retryable": False}},
            )

        raw_token = auth_header[7:]  # Strip "Bearer "
        # Never log the raw token
        logger.debug("Bearer token received (length=%d)", len(raw_token))

        # Split into payload and signature
        parts = raw_token.split(".")
        if len(parts) != 2:
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "AUTH_INVALID", "message": "Malformed token", "retryable": False}},
            )

        try:
            payload_b64, sig_b64 = parts
            payload_bytes = b64decode(payload_b64)
            payload = json.loads(payload_bytes)
        except Exception:
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "AUTH_INVALID", "message": "Malformed token payload", "retryable": False}},
            )

        # Verify HMAC signature
        expected_sig = hmac.new(self._secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
        try:
            actual_sig = b64decode(sig_b64)
        except Exception:
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "AUTH_INVALID", "message": "Malformed signature", "retryable": False}},
            )

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "AUTH_INVALID", "message": "Invalid token signature", "retryable": False}},
            )

        # Check expiration
        exp = payload.get("exp", 0)
        if time.time() > exp:
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "AUTH_EXPIRED", "message": "Token expired", "retryable": False}},
            )

        # Extract claims
        user_id = payload.get("sub", "")
        tenant_id = payload.get("tid", "")
        roles = payload.get("roles", [])

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "AUTH_INVALID", "message": "Missing sub claim", "retryable": False}},
            )

        return AuthContext(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles if isinstance(roles, list) else [roles],
            authenticated=True,
        )


def create_bearer_token(payload: dict, secret: str) -> str:
    """Create a signed bearer token (utility for testing).

    Args:
        payload: dict with sub, tid, roles, exp claims
        secret: HMAC signing secret

    Returns:
        Base64-encoded token string
    """
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = b64encode(payload_json.encode("utf-8")).decode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = b64encode(sig).decode("utf-8")
    return f"{payload_b64}.{sig_b64}"


def get_auth_provider() -> AuthProvider:
    """Factory: returns the auth provider based on settings.auth_mode."""
    settings = get_settings()
    if settings.auth_mode == AuthMode.BEARER:
        return BearerTokenProvider(secret=settings.auth_secret)
    return DevAuthProvider()
