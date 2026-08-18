"""Authentication boundary — AuthContext and dev provider (Phase 8).

Establishes an authentication boundary without building full user management.
Development mode: extracts user identity from X-Dev-User-Id header.
Production: replaceable with JWT/OAuth middleware.

The API never trusts raw client-provided user_id/tenant_id/role
without authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from tros.api.config import AUTH_ENABLED


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


def get_auth_context(
    request: Request,
    dev_user_id: Optional[str] = Security(_dev_user_header),
) -> AuthContext:
    """FastAPI dependency: extract or create AuthContext for the request.

    In development mode (AUTH_ENABLED=false), creates a dev context from
    the X-Dev-User-Id header or a default anonymous user.

    In production mode (AUTH_ENABLED=true), requires valid authentication.
    """
    if not AUTH_ENABLED:
        # Development mode: trust the header for convenience
        user_id = dev_user_id or "dev-user"
        return AuthContext(
            user_id=user_id,
            tenant_id="dev",
            roles=["developer"],
            authenticated=True,
        )

    # Production mode: require real authentication
    # For now, reject if no valid auth mechanism is present
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    # Placeholder for JWT/OAuth validation
    # In production, parse and validate the token here
    raise HTTPException(
        status_code=501,
        detail="Production authentication not yet implemented",
    )


def require_auth(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """FastAPI dependency: require authenticated user."""
    if not auth.authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth
