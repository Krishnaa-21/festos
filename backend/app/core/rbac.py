# OWNER: P3
from typing import Dict, List

from app.core.errors import ForbiddenError
from app.schemas.common import Actor, Role

# Full RBAC matrix for the nine festival roles per FESTOS_CONTEXT Section 9 and Spec Section 18
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    Role.FESTIVAL_DIRECTOR.value: [
        "*:*"
    ],
    Role.ACCOMMODATION_LEAD.value: [
        "accommodation:read",
        "accommodation:write",
        "accommodation:approve",
        "accommodation:export",
        "accommodation:sensitive",
        "participants:read",
        "participants:sensitive",
        "contingents:read",
        "venues:read",
        "reports:read",
        "assumptions:read",
    ],
    Role.EVENT_LEAD.value: [
        "events:read",
        "events:write",
        "events:approve",
        "events:export",
        "schedule:read",
        "schedule:write",
        "schedule:approve",
        "venues:read",
        "venues:write",
        "staff:read",
        "staff:write",
        "participants:read",
        "reports:read",
        "assumptions:read",
    ],
    Role.LOGISTICS_MANAGER.value: [
        "logistics:read",
        "logistics:write",
        "logistics:export",
        "inventory:read",
        "inventory:write",
        "inventory:export",
        "venues:read",
        "events:read",
        "transport:read",
        "reports:read",
        "assumptions:read",
    ],
    Role.MERCHANDISE_MANAGER.value: [
        "merchandise:read",
        "merchandise:write",
        "merchandise:export",
        "participants:read",
        "contingents:read",
        "reports:read",
        "assumptions:read",
    ],
    Role.FOOD_OPS_MANAGER.value: [
        "food:read",
        "food:write",
        "food:export",
        "vendors:read",
        "vendors:write",
        "vendors:export",
        "notifications:read",
        "notifications:write",
        "reports:read",
        "assumptions:read",
    ],
    Role.FINANCE_MANAGER.value: [
        "finance:read",
        "finance:write",
        "finance:approve",
        "finance:export",
        "vendors:read",
        "logistics:read",
        "merchandise:read",
        "reports:read",
        "reports:export",
        "assumptions:read",
    ],
    Role.VOLUNTEER.value: [
        "checkin:read",
        "checkin:write",
        "merchandise:read",
        "merchandise:write",
        "events:read",
        "venues:read",
    ],
    Role.AUDITOR.value: [
        "audit:read",
        "audit:export",
        "overrides:read",
        "approvals:read",
        "*:read",
    ],
}


def normalize_permission(perm: str) -> str:
    """Normalize permission string by removing extraneous whitespace around colon."""
    if ":" in perm:
        parts = perm.split(":", 1)
        return f"{parts[0].strip()}:{parts[1].strip()}"
    return perm.strip()


def get_role_permissions(role: str) -> List[str]:
    """Retrieve list of granted permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(actor: Actor, required_permission: str) -> bool:
    """Check if actor holds the required permission."""
    if not actor:
        return False

    role = actor.role
    if role in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"]:
        return True

    granted = ROLE_PERMISSIONS.get(role, [])
    req_norm = normalize_permission(required_permission)
    req_mod, req_act = req_norm.split(":", 1) if ":" in req_norm else (req_norm, "*")

    for g in granted:
        g_norm = normalize_permission(g)
        if g_norm == "*:*" or g_norm == req_norm:
            return True
        if ":" in g_norm:
            g_mod, g_act = g_norm.split(":", 1)
            # Match *:read or module:*
            if (g_mod == "*" or g_mod == req_mod) and (g_act == "*" or g_act == req_act):
                return True

    return False


def check_permission(actor: Actor, required_permission: str) -> None:
    """Enforce permission, raising ForbiddenError if check fails."""
    if not has_permission(actor, required_permission):
        raise ForbiddenError(f"Missing required permission: '{required_permission}' for role '{actor.role}'")


def get_all_permissions_matrix() -> Dict[str, List[str]]:
    """Return dictionary of all roles and their assigned permissions."""
    return ROLE_PERMISSIONS
