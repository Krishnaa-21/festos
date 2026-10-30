# OWNER: P3
from typing import Optional

from fastapi import Header, Request

from app.core.config import settings
from app.schemas.common import Actor, Role


async def get_actor(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Actor:
    """Dependency that returns the current authenticated Actor.
    While AUTH_DISABLED=true, returns a dev FESTIVAL_DIRECTOR.
    """
    if settings.AUTH_DISABLED:
        return Actor(
            id="usr_director_dev",
            name="Dev Festival Director",
            role=Role.FESTIVAL_DIRECTOR.value,
            contingent_id=None
        )

    # If auth header provided, parse or decode JWT (stub for P3)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
        if payload:
            return Actor(
                id=payload.get("sub", "usr_actor"),
                name=payload.get("name", "Authenticated User"),
                role=payload.get("role", Role.VOLUNTEER.value),
                contingent_id=payload.get("contingent_id")
            )

    return Actor(
        id="usr_anonymous",
        name="Anonymous Guest",
        role=Role.VOLUNTEER.value,
        contingent_id=None
    )
