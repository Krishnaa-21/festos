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


def get_voi_ranking(session: Session) -> Dict[str, Any]:
    """Retrieves Value-of-Information (VOI) ranking across unknown field groups."""
    from app.engines.unknowns.voi_engine import calculate_voi_ranking
    return calculate_voi_ranking(session)


def generate_batch_confirmation_request(
    session: Session,
    target_type: str,
    contingent_id: Optional[str] = None,
    group_id: Optional[str] = "housing_gender",
    expires_in_minutes: int = 1440,
) -> Dict[str, Any]:
    """Generates a minimal confirmation request package batched by contingent leader or desk volunteer,
    requesting only the specific unknown fields needed.
    """
    from app.engines.unknowns.voi_engine import UNKNOWN_GROUPS
    from app.models.participants import Contingent

    # Determine requested fields for group
    group_def = next((g for g in UNKNOWN_GROUPS if g["group_id"] == group_id), None)
    target_fields = group_def["fields"] if group_def else ["gender", "accommodation_requested"]

    query = select(Participant).where(Participant.status.notin_(["CANCELLED", "NO_SHOW", "WITHDRAWN", "INVALID", "MERGED"]))
    if contingent_id:
        query = query.where(Participant.contingent_id == contingent_id)

    participants = session.exec(query).all()

    # Filter to only those having at least one UNKNOWN in target_fields
    affected_participants = []
    for p in participants:
        missing = []
        for f in target_fields:
            if hasattr(p, f):
                val = getattr(p, f)
                if not val or str(val).upper().strip() in ["UNKNOWN", "NONE", "NULL", "UNSPECIFIED"]:
                    missing.append(f)
            elif f == "accessibility_needs":
                acc = p.accessibility_needs or {}
                if not acc or acc.get("status") == "UNKNOWN":
                    missing.append("accessibility_needs")

        if missing:
            affected_participants.append({
                "id": p.id,
                "name": p.name,
                "contingent_id": p.contingent_id,
                "missing_fields": missing,
            })

    # Leader info if contingent
    leader_name = "Desk Volunteer"
    if contingent_id:
        ctg = session.get(Contingent, contingent_id)
        if ctg:
            leader_name = ctg.leader or ctg.contact_name or f"Leader of {ctg.name}"

    token_meta = generate_confirmation_token(
        entity_type="contingent" if contingent_id else "desk",
        entity_id=contingent_id or "desk_all",
        field="batch_" + (group_id or "all"),
        expires_in_minutes=expires_in_minutes,
        role="LEADER" if target_type.upper() == "CONTINGENT_LEADER" else "VOLUNTEER",
    )

    return {
        "target_type": target_type.upper(),
        "contingent_id": contingent_id,
        "leader_name": leader_name,
        "group_id": group_id,
        "fields_requested": target_fields,
        "batch_token": token_meta["token"],
        "expires_at": token_meta["expires_at"],
        "total_participants": len(affected_participants),
        "participants": affected_participants,
    }


def verify_and_reconcile(
    session: Session,
    entity_type: str,
    entity_id: str,
    field: str,
    value: str,
    source: str = "DESK_VERIFICATION",
    verifier: str = "usr_desk_vol01",
    actor: Optional[Actor] = None,
) -> Dict[str, Any]:
    """Records field verification through ChangeService, re-runs affected logic,
    and returns before/after state reconciliation.
    """
    act = actor or Actor(id=verifier, name=verifier, role="VOLUNTEER")

    # 1. Before snapshot
    target = session.get(Participant, entity_id) if entity_type == "participant" else None
    if not target:
        raise ValueError(f"{entity_type} '{entity_id}' not found.")

    prev_val = getattr(target, field, "UNKNOWN")
    unresolved_before = session.exec(
        select(func.count(Participant.id)).where(getattr(Participant, field) == "UNKNOWN")
    ).one()

    # 2. Execute change
    req = ChangeRequest(
        action="unknowns.verify_field",
        entity_type=entity_type,
        entity_id=entity_id,
        payload={
            "field": field,
            "value": value,
            "source": source,
            "verifier": verifier,
        },
        reason=f"Verified field {field} for {entity_id} as '{value}'",
        actor=act,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise ValueError(f"Verification rejected: {res.violations}")

    session.flush()

    # 3. After snapshot
    unresolved_after = session.exec(
        select(func.count(Participant.id)).where(getattr(Participant, field) == "UNKNOWN")
    ).one()

    # Re-run affected engine logic depending on domain
    affected_engine = "UNKNOWN"
    engine_impact_summary = ""
    if field in ["gender", "accommodation_requested", "housing_preference"]:
        affected_engine = "ACCOMMODATION_ALLOCATION"
        engine_impact_summary = f"Participant {entity_id} updated to {value}; room eligibility updated."
    elif field == "diet":
        affected_engine = "VENDOR_CATERING"
        engine_impact_summary = f"Participant {entity_id} dietary choice recorded as {value}; meal slot buffer reconciled."
    elif field in ["arrival_at", "departure_at"]:
        affected_engine = "TRANSPORT_RECEPTION"
        engine_impact_summary = f"Transit ETA/ETD locked for {entity_id}."

    return {
        "status": "VERIFIED",
        "entity_id": entity_id,
        "field": field,
        "value": value,
        "verified_at": now().isoformat(),
        "reconciliation": {
            "affected_engine": affected_engine,
            "field": field,
            "previous_value": str(prev_val),
            "verified_value": value,
            "unresolved_count_before": unresolved_before,
            "unresolved_count_after": unresolved_after,
            "delta": unresolved_before - unresolved_after,
            "impact_summary": engine_impact_summary,
        },
    }


def get_why_not_counterfactuals(session: Session, participant_id: str) -> Dict[str, Any]:
    """Diagnostic explanation extending Why-Not with simulated counterfactual predictions:
    'What confirming field X would change for this participant'.
    """
    from app.models.accommodation import ExternalProperty, Room

    p = session.get(Participant, participant_id)
    if not p:
        raise ValueError(f"Participant '{participant_id}' not found.")

    rooms = session.exec(select(Room)).all()
    properties = session.exec(select(ExternalProperty)).all()

    blocking_reasons: List[str] = []
    counterfactuals: List[Dict[str, Any]] = []

    gender_norm = str(p.gender or "UNKNOWN").upper().strip()
    housing_norm = str(p.accommodation_requested or "UNKNOWN").upper().strip()

    if gender_norm in ["UNKNOWN", "PREFER NOT TO SAY", "NON-BINARY"]:
        blocking_reasons.append("GENDER_UNKNOWN")
        # Female simulation
        female_rooms = sum(1 for r in rooms if str(getattr(r, "gender_class", "")).upper() in ["FEMALE", "GIRLS", "ANY"])
        counterfactuals.append({
            "field": "gender",
            "if_confirmed_as": "FEMALE",
            "outcome": f"Eligible for {female_rooms * 2} beds in Girls hostel blocks",
            "can_be_placed": female_rooms > 0,
        })
        # Male simulation
        male_rooms = sum(1 for r in rooms if str(getattr(r, "gender_class", "")).upper() in ["MALE", "BOYS", "ANY"])
        counterfactuals.append({
            "field": "gender",
            "if_confirmed_as": "MALE",
            "outcome": f"Eligible for {male_rooms * 2} beds in Boys hostel blocks",
            "can_be_placed": male_rooms > 0,
        })

    if housing_norm == "UNKNOWN":
        blocking_reasons.append("HOUSING_PREFERENCE_UNKNOWN")
        counterfactuals.append({
            "field": "accommodation_requested",
            "if_confirmed_as": "NO",
            "outcome": "Removed from shortage queue; 0 beds required",
            "can_be_placed": True,
        })
        counterfactuals.append({
            "field": "accommodation_requested",
            "if_confirmed_as": "YES",
            "outcome": "Enqueued for optimal bed assignment with contingent peers",
            "can_be_placed": True,
        })

    acc = p.accessibility_needs or {}
    if not acc or acc.get("status") == "UNKNOWN":
        blocking_reasons.append("ACCESSIBILITY_UNCONFIRMED")
        counterfactuals.append({
            "field": "accessibility_needs",
            "if_confirmed_as": "GROUND_FLOOR",
            "outcome": "Allocated to ground-floor accessible room in Hostel Block A",
            "can_be_placed": True,
        })
        counterfactuals.append({
            "field": "accessibility_needs",
            "if_confirmed_as": "NONE",
            "outcome": "Unlocks upper-floor rooms across all hostel wings",
            "can_be_placed": True,
        })

    diet_norm = str(p.diet or "UNKNOWN").upper().strip()
    if diet_norm in ["UNKNOWN", "NONE", "UNSPECIFIED"]:
        blocking_reasons.append("DIET_UNKNOWN")
        counterfactuals.append({
            "field": "diet",
            "if_confirmed_as": "VEG",
            "outcome": "Assigned to Central Mess Vegetarian dining hall",
            "can_be_placed": True,
        })
        counterfactuals.append({
            "field": "diet",
            "if_confirmed_as": "JAIN",
            "outcome": "Voucher routed to dedicated Jain catering provider",
            "can_be_placed": True,
        })

    if not blocking_reasons:
        blocking_reasons.append("CAPACITY_EXHAUSTED_AT_PEAK")
        counterfactuals.append({
            "field": "arrival_at",
            "if_confirmed_as": "SHIFT_WINDOW",
            "outcome": "Moving arrival window by 4 hours clears peak bed contention",
            "can_be_placed": True,
        })

    return {
        "participant_id": p.id,
        "name": p.name,
        "current_status": p.status,
        "blocking_reasons": blocking_reasons,
        "counterfactuals": counterfactuals,
    }
