"""Authentication boundary — AuthContext and provider delegation (Phase 8/9).

Establishes an authentication boundary without building full user management.
Development mode: extracts user identity from X-Dev-User-Id header.
Production: validates HMAC-SHA256 bearer tokens via BearerTokenProvider.

The API never trusts raw client-provided user_id/tenant_id/role
without authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

# Header for dev-mode authentication
_dev_user_header = APIKeyHeader(name="X-Dev-User-Id", auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    """Authentication context for a request.

    In development mode, user_id comes from the X-Dev-User-Id header.
    In production, this would be populated by JWT/OAuth validation.
    """
    user_id: str = ""
    tenant_id: str = ""
    roles: list[str] = field(default_factory=list)
    authenticated: bool = False

    @property
    def is_anonymous(self) -> bool:
        return not self.authenticated


def get_auth_context(request: Request) -> AuthContext:
    """FastAPI dependency: extract or create AuthContext for the request.

    Delegates to the configured auth provider (dev or bearer).
    """
    from tros.api.auth_providers import get_auth_provider
    provider = get_auth_provider()
    return provider.authenticate(request)


def require_auth(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """FastAPI dependency: require authenticated user."""
    if not auth.authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth
