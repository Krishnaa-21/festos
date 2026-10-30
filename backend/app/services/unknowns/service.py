# OWNER: P2 (P1 implementing field-verification parts)
"""Service layer for UNKNOWN fields verification queue, owner assignments, and confirmation tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlmodel import Session, func, select

from app.core.change_service import ChangeRequest, execute_change
from app.core.clock import now
from app.core.config import settings
from app.models.participants import FieldVerification, Participant
from app.schemas.common import Actor

CRITICALITY_MAP: Dict[str, int] = {
    "accommodation_requested": 4,
    "gender": 4,
    "diet": 3,
    "arrival_at": 3,
    "departure_at": 3,
    "tshirt_size": 2,
}

OWNER_MAP: Dict[str, str] = {
    "accommodation_requested": "ACCOMMODATION_LEAD",
    "gender": "ACCOMMODATION_LEAD",
    "diet": "FOOD_OPS_MANAGER",
    "arrival_at": "LOGISTICS_MANAGER",
    "departure_at": "LOGISTICS_MANAGER",
    "tshirt_size": "MERCHANDISE_MANAGER",
}

IMPACT_TEXT_MAP: Dict[str, str] = {
    "accommodation_requested": "Beds cannot be definitively blocked in Plan A/B without confirmed housing requirement.",
    "gender": "Room allocation cannot enforce campus gender segregation safety constraints.",
    "diet": "Catering procurement buffers risk meal shortages or food waste.",
    "arrival_at": "Transport and reception desks cannot schedule arrival waves without ETA.",
    "departure_at": "Luggage storage and checkout waves cannot be planned without ETD.",
    "tshirt_size": "Merchandise packing desk cannot pre-kit kit bags for arrival check-in.",
}


def get_unknown_queue(session: Session) -> Dict[str, Any]:
    """Generates the operational unknown fields queue ranked by Count x Criticality."""
    # Count UNKNOWN fields in Participant table
    queue = []
    total_unresolved = 0

    field_specs = [
        ("accommodation_requested", "participant"),
        ("gender", "participant"),
        ("diet", "participant"),
        ("tshirt_size", "participant"),
    ]

    for field_name, entity_type in field_specs:
        cnt = session.exec(
            select(func.count(Participant.id)).where(getattr(Participant, field_name) == "UNKNOWN")
        ).one()

        if cnt > 0:
            criticality = CRITICALITY_MAP.get(field_name, 1)
            score = cnt * criticality
            owner = OWNER_MAP.get(field_name, "OPERATIONS")
            impact_text = IMPACT_TEXT_MAP.get(field_name, "Operational verification required.")

            # Sample IDs
            samples = session.exec(
                select(Participant.id).where(getattr(Participant, field_name) == "UNKNOWN").limit(5)
            ).all()

            queue.append({
                "field": field_name,
                "entity_type": entity_type,
                "count": cnt,
                "criticality": criticality,
                "score": score,
                "owner": owner,
                "impact_text": impact_text,
                "sample_entity_ids": list(samples),
            })
            total_unresolved += cnt

    # Sort descending by score (Count x Criticality)
    queue.sort(key=lambda x: x["score"], reverse=True)

    return {
        "total_unresolved_fields": total_unresolved,
        "queue": queue,
    }


def list_unknown_items(
    session: Session,
    field: str,
    contingent_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    """Lists specific participant records that have an UNKNOWN value for a given field."""
    if not hasattr(Participant, field):
        raise ValueError(f"Field '{field}' is not a valid participant attribute.")

    query = select(Participant).where(getattr(Participant, field) == "UNKNOWN")
    if contingent_id:
        query = query.where(Participant.contingent_id == contingent_id)

    subq = query.subquery()
    total = session.exec(select(func.count()).select_from(subq)).one()

    offset = (page - 1) * page_size
    participants = session.exec(query.order_by(Participant.id.asc()).offset(offset).limit(page_size)).all()

    items = []
    owner = OWNER_MAP.get(field, "OPERATIONS")
    for p in participants:
        items.append({
            "id": p.id,
            "name": p.name,
            "college": p.college,
            "contingent_id": p.contingent_id,
            "field": field,
            "current_value": "UNKNOWN",
            "status": "UNKNOWN",
            "owner": owner,
        })

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def generate_confirmation_token(
    entity_type: str,
    entity_id: str,
    field: str,
    expires_in_minutes: int = 1440,
    role: str = "LEADER",
) -> Dict[str, Any]:
    """Generates a cryptographically signed, expiring, field-scoped confirmation token."""
    expire_at = now() + timedelta(minutes=expires_in_minutes)
    payload = {
        "sub": f"{entity_type}:{entity_id}:{field}",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field": field,
        "role": role,
        "exp": int(expire_at.timestamp()),
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{sig}"

    return {
        "token": token,
        "expires_at": expire_at.isoformat(),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field": field,
    }


def verify_confirmation_token(token: str) -> Dict[str, Any]:
    """Verifies a signed token and extracts claims, or raises on invalid/expired token."""
    parts = token.strip().split(".")
    if len(parts) != 2:
        raise ValueError("Invalid confirmation token structure.")
    payload_b64, sig = parts

    rem = len(payload_b64) % 4
    payload_b64_padded = payload_b64 + ("=" * (4 - rem) if rem else "")

    expected_sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("Invalid confirmation token: signature mismatch.")

    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64_padded)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid confirmation token payload: {e}")

    if "exp" in payload and time.time() > payload["exp"]:
        raise ValueError("Confirmation token has expired.")

    return payload


def confirm_token_submission(
    session: Session,
    token: str,
    value: str,
    source: str = "LEADER_TOKEN_SUBMISSION",
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Validates confirmation token and records verified value via ChangeService."""
    claims = verify_confirmation_token(token)
    entity_type = claims["entity_type"]
    entity_id = claims["entity_id"]
    field = claims["field"]
    role = claims.get("role", "LEADER")

    actor = Actor(
        id=f"token_{role.lower()}",
        role=role,
        name=f"Signed Token ({role})",
    )

    req = ChangeRequest(
        action="unknowns.verify_field",
        entity_type=entity_type,
        entity_id=entity_id,
        payload={
            "field": field,
            "value": value,
            "source": source,
            "verifier": f"token_{role}",
        },
        reason=comment or f"Field {field} confirmed via signed token submission.",
        actor=actor,
    )

    result = execute_change(req, session)
    if result.status == "REJECTED":
        raise ValueError(f"Verification rejected: {result.violations}")

    return {
        "status": "VERIFIED",
        "entity_id": entity_id,
        "field": field,
        "value": value,
        "verified_at": now().isoformat(),
    }


def get_field_history(
    session: Session,
    entity_type: str,
    entity_id: str,
    field: str,
) -> List[Dict[str, Any]]:
    """Retrieves chronological verification records for a specific entity field."""
    verifications = session.exec(
        select(FieldVerification).where(
            FieldVerification.entity_type == entity_type,
            FieldVerification.entity_id == entity_id,
            FieldVerification.field == field,
        ).order_by(FieldVerification.created_at.desc())
    ).all()

    return [
        {
            "id": v.id,
            "status": v.status,
            "value": v.value,
            "source": v.source,
            "verified_by": v.verified_by,
            "verified_at": v.verified_at.isoformat() if v.verified_at else None,
            "owner": v.owner,
        }
        for v in verifications
    ]
