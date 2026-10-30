# OWNER: P3
import functools
import re
from typing import Any, Dict, Optional, Union

from sqlmodel import Session, col, select

from app.core.clock import now
from app.schemas.common import Actor, Role

PHONE_MASK = "+91-XXXXX-{tail}"
EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?(\d{4})")

SENSITIVE_PATTERNS = {
    "phone": ("phone", "contact_number", "mobile", "telephone", "emergency_phone"),
    "email": ("email", "contact_email", "emergency_email"),
    "medical": ("medical", "medical_notes", "medical_conditions", "health_info", "allergies"),
    "accessibility": ("accessibility", "accessibility_details", "special_needs", "disability_notes"),
    "room": ("room_number", "bed_id", "room_data", "hostel_room", "room_allocation"),
    "guardian": ("guardian_name", "guardian_phone", "guardian_email", "guardian_contact", "escort_contact"),
}


def mask_phone(val: Optional[str]) -> str:
    if not val:
        return "UNKNOWN"
    clean_digits = re.sub(r"\D", "", str(val))
    if len(clean_digits) >= 4:
        return f"+91-XXXXX-{clean_digits[-4:]}"
    return "+91-XXXXX-XXXX"


def mask_email(val: Optional[str]) -> str:
    if not val:
        return "UNKNOWN"
    s = str(val)
    if "@" in s:
        user_part, domain = s.split("@", 1)
        first_char = user_part[0] if user_part else "u"
        return f"{first_char}***@{domain}"
    return "***@***.***"


def _is_active_break_glass(
    actor_id: str,
    entity_key: str,
    field_name: str,
    session: Optional[Session]
) -> bool:
    """Check if an active break-glass grant exists for actor, entity, and field."""
    if not session or not entity_key or not actor_id:
        return False
    try:
        from app.models.audit import BreakGlassGrant
        current_time = now()
        stmt = (
            select(BreakGlassGrant)
            .where(
                BreakGlassGrant.user_id == actor_id,
                BreakGlassGrant.entity == entity_key,
                BreakGlassGrant.field == field_name,
                BreakGlassGrant.expires_at > current_time,
                col(BreakGlassGrant.is_revoked).is_(False)
            )
        )
        grant = session.exec(stmt).first()
        return grant is not None
    except Exception:
        return False


def mask_fields(
    data: Union[Dict[str, Any], Any],
    actor: Optional[Actor],
    entity_key: Optional[str] = None,
    session: Optional[Session] = None
) -> Any:
    """Mask sensitive fields according to actor role and active break-glass grants."""
    if not actor:
        actor_role = "ANONYMOUS"
        actor_id = ""
    else:
        actor_role = actor.role
        actor_id = actor.id

    # Festival Director has full unmasked visibility
    if actor_role in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR"]:
        return data

    is_dict = isinstance(data, dict)
    if is_dict:
        res = dict(data)
    elif hasattr(data, "model_dump"):
        res = data.model_dump()
    elif hasattr(data, "dict"):
        res = data.dict()
    elif hasattr(data, "__dict__"):
        res = dict(data.__dict__)
    else:
        return data

    # Role exemptions for specific operational domains
    can_view_room = actor_role in [Role.ACCOMMODATION_LEAD.value, "ACCOMMODATION_LEAD"]
    can_view_accessibility = actor_role in [Role.ACCOMMODATION_LEAD.value, "ACCOMMODATION_LEAD"]
    can_view_guardian = actor_role in [Role.EVENT_LEAD.value, "EVENT_LEAD"]

    for k, v in list(res.items()):
        if v is None:
            continue

        lower_k = k.lower()

        # Guardian data
        if any(p in lower_k for p in SENSITIVE_PATTERNS["guardian"]):
            if not can_view_guardian and not _is_active_break_glass(actor_id, entity_key or "", k, session):
                res[k] = "[PROTECTED GUARDIAN DATA]"

        # Medical data
        elif any(p in lower_k for p in SENSITIVE_PATTERNS["medical"]):
            if not _is_active_break_glass(actor_id, entity_key or "", k, session):
                res[k] = "[PROTECTED MEDICAL DATA]"

        # Accessibility data
        elif any(p in lower_k for p in SENSITIVE_PATTERNS["accessibility"]):
            if not can_view_accessibility and not _is_active_break_glass(actor_id, entity_key or "", k, session):
                res[k] = "[PROTECTED ACCESSIBILITY DATA]"

        # Room data
        elif any(p in lower_k for p in SENSITIVE_PATTERNS["room"]):
            if not can_view_room and not _is_active_break_glass(actor_id, entity_key or "", k, session):
                res[k] = "[PROTECTED ROOM DATA]"

        # Phone masking
        elif any(p in lower_k for p in SENSITIVE_PATTERNS["phone"]):
            if not _is_active_break_glass(actor_id, entity_key or "", k, session):
                res[k] = mask_phone(str(v))

        # Email masking
        elif any(p in lower_k for p in SENSITIVE_PATTERNS["email"]):
            if not _is_active_break_glass(actor_id, entity_key or "", k, session):
                res[k] = mask_email(str(v))

    return res


def mask_log_message(msg: str) -> str:
    """Mask email addresses and phone numbers in operational logs."""
    if not isinstance(msg, str):
        return str(msg)
    # Mask emails
    msg = EMAIL_PATTERN.sub(r"\1***@\2", msg)
    # Mask phones
    msg = PHONE_PATTERN.sub("+91-XXXXX-XXXX", msg)
    return msg


def export_allowed(module_name: str):
    """Decorator to enforce export permission on endpoints."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            from app.core.rbac import check_permission
            actor = kwargs.get("actor")
            if not actor:
                for arg in args:
                    if isinstance(arg, Actor):
                        actor = arg
                        break
            if actor:
                check_permission(actor, f"{module_name}:export")
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
