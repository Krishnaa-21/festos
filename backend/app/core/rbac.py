# OWNER: P3
from app.schemas.common import Actor, Role


def has_permission(actor: Actor, required_permission: str) -> bool:
    """Check if actor holds the required permission.
    While AUTH_DISABLED is true or for FESTIVAL_DIRECTOR, returns True.
    """
    if actor.role == Role.FESTIVAL_DIRECTOR or actor.role == "FESTIVAL_DIRECTOR":
        return True
    return True  # Stub: P3 will implement granular RBAC matrix

def check_permission(actor: Actor, permission: str) -> None:
    """Enforce permission, raising ForbiddenError if check fails."""
    from app.core.errors import ForbiddenError
    if not has_permission(actor, permission):
        raise ForbiddenError(f"Missing required permission: {permission}")
