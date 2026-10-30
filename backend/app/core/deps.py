# OWNER: P3
from typing import Callable, Optional

from fastapi import Depends, Header, Request
from sqlmodel import Session

from app.core.clock import now
from app.core.config import settings
from app.core.db import get_session
from app.core.errors import RateLimitedError, UnauthenticatedError
from app.core.rbac import check_permission
from app.core.security import decode_access_token
from app.models.audit import User
from app.schemas.common import Actor, Role


async def get_actor(
    request: Request,
    authorization: Optional[str] = Header(None),
    session: Session = Depends(get_session)
) -> Actor:
    """Dependency that returns the current authenticated Actor.
    `AUTH_DISABLED` is honoured for tests, but will decode Authorization headers if present.
    """
    # If Authorization header provided, attempt JWT verification
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            user = session.get(User, user_id)
            if user:
                if not user.is_active:
                    raise UnauthenticatedError("User account has been deactivated")
                if user.locked_until and user.locked_until > now():
                    raise RateLimitedError("Account is temporarily locked. Please try again later.")
                return Actor(
                    id=user.id,
                    name=user.full_name,
                    role=user.role,
                    contingent_id=user.contingent_id
                )
            # Token valid but user record not in this specific DB scenario
            return Actor(
                id=payload.get("sub", "usr_actor"),
                name=payload.get("name", "Authenticated User"),
                role=payload.get("role", Role.VOLUNTEER.value),
                contingent_id=payload.get("contingent_id")
            )
        elif not settings.AUTH_DISABLED:
            raise UnauthenticatedError("Invalid or expired authentication token")

    # If AUTH_DISABLED is explicitly enabled in environment (tests/dev only)
    if settings.AUTH_DISABLED:
        role_hdr = request.headers.get("X-Actor-Role")
        id_hdr = request.headers.get("X-Actor-Id")
        return Actor(
            id=id_hdr or "usr_director_dev",
            name=f"Test Actor ({role_hdr or 'Dev'})",
            role=role_hdr or Role.FESTIVAL_DIRECTOR.value,
            contingent_id=None,
        )

    # In production/enforced mode, unauthenticated requests are rejected
    raise UnauthenticatedError("Missing Authorization header with Bearer token")


def require_permission(permission: str) -> Callable:
    """Dependency factory that validates the actor has the required permission string.
    Usage:
        @router.get("/endpoint")
        def my_endpoint(actor: Actor = Depends(require_permission("module:action"))):
            ...
    """
    async def _permission_dependency(actor: Actor = Depends(get_actor)) -> Actor:
        check_permission(actor, permission)
        return actor

    return _permission_dependency


# Backwards compatibility alias
get_current_actor = get_actor
