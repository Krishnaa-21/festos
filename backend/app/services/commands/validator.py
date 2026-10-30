# OWNER: P1
from __future__ import annotations

import re
from typing import Optional, Tuple

from sqlmodel import Session

from app.core.errors import ForbiddenError, ValidationError
from app.core.rbac import has_permission
from app.schemas.common import Actor, Role
from app.services.commands.schemas import CommandIntent, StructuredCommand

INTENT_PERMISSIONS = {
    CommandIntent.SHOW_IMPACT: ["impact:read", "dashboard:read", "accommodation:read", "events:read"],
    CommandIntent.FIND_ACCOMMODATION_FOR_UNPLACED: ["accommodation:write", "accommodation:approve"],
    CommandIntent.AFFECTED_EVENTS_BY_EQUIPMENT: ["logistics:read", "events:read", "inventory:read", "dashboard:read"],
    CommandIntent.ALTERNATIVE_VENDORS_FOR_DIET: ["food:read", "vendors:read", "dashboard:read"],
    CommandIntent.LIST_LATE_ARRIVALS: ["participants:read", "dashboard:read"],
    CommandIntent.QUERY: ["dashboard:read", "participants:read"],
    CommandIntent.NAVIGATE: ["dashboard:read"],
}


def check_intent_permission(actor: Actor, intent: CommandIntent) -> None:
    """Verifies that the actor holds at least one permission allowing execution of the specified intent."""
    if not actor:
        raise ForbiddenError("Unauthenticated actor cannot execute commands")

    # Festival Director has all permissions
    if actor.role in (Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"):
        return

    allowed_perms = INTENT_PERMISSIONS.get(intent, ["dashboard:read"])
    if not any(has_permission(actor, perm) for perm in allowed_perms):
        raise ForbiddenError(
            f"Role '{actor.role}' lacks authorization to execute '{intent.value}'. Required permissions: {allowed_perms}"
        )


def validate_command(command: StructuredCommand, actor: Actor, session: Session) -> Tuple[bool, Optional[str]]:
    """Deterministically validates command existence, parameter integrity, and caller permissions."""
    # 1. RBAC check
    check_intent_permission(actor, command.intent)

    # 2. Parameter schema validation
    params = command.parameters or {}

    if command.intent == CommandIntent.SHOW_IMPACT:
        entity_id = params.get("entity_id")
        if not entity_id or not str(entity_id).strip():
            raise ValidationError("Entity ID is required for impact simulation")

    elif command.intent == CommandIntent.FIND_ACCOMMODATION_FOR_UNPLACED:
        plan_kind = params.get("plan_kind", "C")
        if str(plan_kind).upper() not in ("A", "B", "C"):
            raise ValidationError(f"Invalid accommodation plan kind: '{plan_kind}'. Expected A, B, or C")

    elif command.intent == CommandIntent.AFFECTED_EVENTS_BY_EQUIPMENT:
        item = params.get("item")
        if not item or not str(item).strip():
            raise ValidationError("Equipment item name is required")

    elif command.intent == CommandIntent.ALTERNATIVE_VENDORS_FOR_DIET:
        diet = params.get("diet")
        if not diet or not str(diet).strip():
            raise ValidationError("Dietary category is required")

    elif command.intent == CommandIntent.LIST_LATE_ARRIVALS:
        after_time = params.get("after_time", "22:00")
        if not re.match(r"^\d{2}:\d{2}$", str(after_time)):
            raise ValidationError(f"Invalid cutoff time format: '{after_time}'. Expected HH:MM (e.g. 22:00)")

    return True, None
