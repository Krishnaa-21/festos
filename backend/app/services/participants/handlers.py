# OWNER: P1
"""Change handlers for participant mutations, state transitions, merges, and field verification.

All mutations go through ChangeService with validation, audit snapshots, and bus event emissions.
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.core.bus import publish
from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.clock import now
from app.core.registry import register_change_handler
from app.models.inventory import MerchClaim
from app.models.participants import (
    Contingent,
    DuplicateCandidate,
    FieldVerification,
    MergeRecord,
    Participant,
    Registration,
)
from app.schemas.common import Severity, Violation

VALID_STATUSES = {
    "EXPECTED",
    "ARRIVED",
    "CHECKED_IN",
    "CHECKED_OUT",
    "CANCELLED",
    "NO_SHOW",
    "WITHDRAWN",
    "INVALID",
    "MERGED",
}

ALLOWED_TRANSITIONS = {
    "EXPECTED": {"ARRIVED", "CANCELLED", "NO_SHOW", "WITHDRAWN", "INVALID", "MERGED"},
    "ARRIVED": {"CHECKED_IN", "CANCELLED", "WITHDRAWN", "MERGED"},
    "CHECKED_IN": {"CHECKED_OUT", "WITHDRAWN", "MERGED"},
    "CHECKED_OUT": {"WITHDRAWN"},
    "CANCELLED": set(),
    "NO_SHOW": {"ARRIVED"},  # Late arrival recovery
    "WITHDRAWN": set(),
    "INVALID": {"EXPECTED"},  # Corrected dates
    "MERGED": set(),
}


def _participant_to_dict(p: Participant) -> Dict[str, Any]:
    """Serializes a Participant row to a full dictionary snapshot."""
    return {
        "id": p.id,
        "canonical_participant_id": p.canonical_participant_id,
        "source_row_id": p.source_row_id,
        "contingent_id": p.contingent_id,
        "name": p.name,
        "college": p.college,
        "email": p.email,
        "phone": p.phone,
        "gender": p.gender,
        "diet": p.diet,
        "housing_preference": p.housing_preference,
        "accessibility_needs": copy.deepcopy(p.accessibility_needs or {}),
        "accommodation_requested": p.accommodation_requested,
        "tshirt_size": p.tshirt_size,
        "arrival_at": p.arrival_at.isoformat() if p.arrival_at else None,
        "departure_at": p.departure_at.isoformat() if p.departure_at else None,
        "dob": p.dob,
        "age": p.age,
        "role": p.role,
        "status": p.status,
        "version": p.version,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _restore_participant_from_dict(p: Participant, data: Dict[str, Any]) -> None:
    """Restores exact byte-identical values onto a Participant model."""
    p.canonical_participant_id = data.get("canonical_participant_id")
    p.source_row_id = data.get("source_row_id")
    p.contingent_id = data.get("contingent_id")
    p.name = data.get("name", "UNKNOWN")
    p.college = data.get("college")
    p.email = data.get("email")
    p.phone = data.get("phone")
    p.gender = data.get("gender", "UNKNOWN")
    p.diet = data.get("diet", "UNKNOWN")
    p.housing_preference = data.get("housing_preference", "UNKNOWN")
    p.accessibility_needs = copy.deepcopy(data.get("accessibility_needs") or {})
    p.accommodation_requested = data.get("accommodation_requested", "UNKNOWN")
    p.tshirt_size = data.get("tshirt_size")
    if data.get("arrival_at"):
        p.arrival_at = datetime.fromisoformat(data["arrival_at"])
    else:
        p.arrival_at = None
    if data.get("departure_at"):
        p.departure_at = datetime.fromisoformat(data["departure_at"])
    else:
        p.departure_at = None
    p.dob = data.get("dob")
    p.age = data.get("age")
    p.role = data.get("role", "PARTICIPANT")
    p.status = data.get("status", "EXPECTED")
    p.version = data.get("version", 1)
    if data.get("created_at"):
        p.created_at = datetime.fromisoformat(data["created_at"])
    if data.get("updated_at"):
        p.updated_at = datetime.fromisoformat(data["updated_at"])


# ==============================================================================
# 1. Participant Create
# ==============================================================================
@register_change_handler("participant.create")
class ParticipantCreateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        payload = req.payload
        violations: List[Violation] = []
        name = payload.get("name", "").strip()
        if not name:
            violations.append(Violation(
                code="REQUIRED_FIELD_MISSING",
                severity=Severity.HIGH,
                hard=True,
                message="Participant name is required.",
                entity_refs=[{"type": "participant", "id": req.entity_id}],
            ))
        return violations

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        payload = req.payload
        pid = req.entity_id or f"par_{uuid.uuid4().hex[:10]}"
        p = Participant(
            id=pid,
            canonical_participant_id=pid,
            source_row_id=pid,
            contingent_id=payload.get("contingent_id"),
            name=payload.get("name", "UNKNOWN"),
            college=payload.get("college"),
            email=payload.get("email"),
            phone=payload.get("phone"),
            gender=payload.get("gender") or "UNKNOWN",
            diet=payload.get("diet") or "UNKNOWN",
            housing_preference=payload.get("housing_preference") or "UNKNOWN",
            accessibility_needs=payload.get("accessibility_needs") or {},
            accommodation_requested=payload.get("accommodation_requested") or "UNKNOWN",
            tshirt_size=payload.get("tshirt_size") or "UNKNOWN",
            arrival_at=payload.get("arrival_at"),
            departure_at=payload.get("departure_at"),
            dob=payload.get("dob"),
            age=payload.get("age"),
            role=payload.get("role", "PARTICIPANT"),
            status=payload.get("status", "EXPECTED"),
            version=1,
            created_at=now(),
            updated_at=now(),
        )
        session.add(p)
        session.flush()
        return _participant_to_dict(p)


# ==============================================================================
# 2. Participant Update
# ==============================================================================
@register_change_handler("participant.update")
class ParticipantUpdateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = session.get(Participant, req.entity_id)
        if not p:
            return [Violation(
                code="PARTICIPANT_NOT_FOUND",
                severity=Severity.CRITICAL,
                hard=True,
                message=f"Participant {req.entity_id} not found",
            )]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = session.get(Participant, req.entity_id)
        return _participant_to_dict(p) if p else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = session.get(Participant, req.entity_id)
        if not p:
            return {}
        payload = req.payload
        for field in ("name", "college", "email", "phone", "gender", "diet",
                      "housing_preference", "accessibility_needs",
                      "accommodation_requested", "tshirt_size", "role", "age", "dob"):
            if field in payload:
                setattr(p, field, payload[field])

        p.version += 1
        p.updated_at = now()
        session.add(p)
        session.flush()
        return _participant_to_dict(p)


# ==============================================================================
# 3. Participant Change Status (State Machine)
# ==============================================================================
@register_change_handler("participant.change_status")
class ParticipantStatusHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        p = session.get(Participant, req.entity_id)
        if not p:
            return [Violation(
                code="PARTICIPANT_NOT_FOUND",
                severity=Severity.CRITICAL,
                hard=True,
                message=f"Participant {req.entity_id} not found",
            )]

        new_status = req.payload.get("status")
        if not new_status or new_status not in VALID_STATUSES:
            return [Violation(
                code="INVALID_STATUS",
                severity=Severity.HIGH,
                hard=True,
                message=f"Status '{new_status}' is not a recognized participant status.",
            )]

        allowed = ALLOWED_TRANSITIONS.get(p.status, set())
        # Director override allowed with recorded reason
        if new_status not in allowed and req.actor.role not in ("FESTIVAL_DIRECTOR", "ADMIN"):
            return [Violation(
                code="INVALID_STATE_TRANSITION",
                severity=Severity.HIGH,
                hard=True,
                message=f"Cannot transition participant status from '{p.status}' to '{new_status}'. Allowed: {sorted(list(allowed))}",
            )]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = session.get(Participant, req.entity_id)
        return _participant_to_dict(p) if p else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = session.get(Participant, req.entity_id)
        if not p:
            return {}

        previous_status = p.status
        new_status = req.payload["status"]
        p.status = new_status
        p.version += 1
        p.updated_at = now()
        session.add(p)
        session.flush()

        # Publish participant.status_changed domain event on the bus
        publish(
            "participant.status_changed",
            {
                "participant_id": p.id,
                "previous_status": previous_status,
                "new_status": new_status,
                "reason": req.reason,
                "actor_id": req.actor.id,
                "actor_role": req.actor.role,
                "timestamp": now().isoformat(),
            },
        )

        return {
            "participant_id": p.id,
            "previous_status": previous_status,
            "new_status": new_status,
            "version": p.version,
        }


# ==============================================================================
# 4. Participant Merge
# ==============================================================================
@register_change_handler("participant.merge")
class ParticipantMergeHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        canonical_id = req.payload.get("canonical_id")
        merged_id = req.payload.get("merged_id")

        p_canon = session.get(Participant, canonical_id)
        p_merged = session.get(Participant, merged_id)

        if not p_canon or not p_merged:
            return [Violation(
                code="PARTICIPANT_NOT_FOUND",
                severity=Severity.CRITICAL,
                hard=True,
                message=f"Participants {canonical_id} and {merged_id} must both exist for merge.",
            )]

        if p_canon.id == p_merged.id:
            return [Violation(
                code="SELF_MERGE_DISALLOWED",
                severity=Severity.HIGH,
                hard=True,
                message="Cannot merge a participant into itself.",
            )]

        if p_merged.status == "MERGED":
            return [Violation(
                code="ALREADY_MERGED",
                severity=Severity.HIGH,
                hard=True,
                message=f"Participant {merged_id} has already been merged into {p_merged.canonical_participant_id}.",
            )]

        # HARD CONSTRAINT: Conflicting merchandise claims block merge for review
        canon_claims = session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == canonical_id)).all()
        merged_claims = session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == merged_id)).all()

        canon_items = {c.item_id: c for c in canon_claims}
        for mc in merged_claims:
            if mc.item_id in canon_items:
                return [Violation(
                    code="CONFLICTING_MERCH_CLAIMS",
                    severity=Severity.CRITICAL,
                    hard=True,
                    message=f"Merge blocked: Both participants hold conflicting merchandise claims for item {mc.item_id}.",
                )]

        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        canonical_id = req.payload.get("canonical_id")
        merged_id = req.payload.get("merged_id")
        p_canon = session.get(Participant, canonical_id)
        p_merged = session.get(Participant, merged_id)
        return {
            "canonical_before": _participant_to_dict(p_canon) if p_canon else {},
            "merged_before": _participant_to_dict(p_merged) if p_merged else {},
        }

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        canonical_id = req.payload["canonical_id"]
        merged_id = req.payload["merged_id"]
        candidate_id = req.payload.get("candidate_id")

        p_canon = session.get(Participant, canonical_id)
        p_merged = session.get(Participant, merged_id)
        if not p_canon or not p_merged:
            return {}

        canon_before = _participant_to_dict(p_canon)
        merged_before = _participant_to_dict(p_merged)

        # 1. Fill missing/UNKNOWN values on canonical record from merged record
        if p_canon.diet in ("UNKNOWN", "", None) and p_merged.diet not in ("UNKNOWN", "", None):
            p_canon.diet = p_merged.diet
        if p_canon.gender in ("UNKNOWN", "", None) and p_merged.gender not in ("UNKNOWN", "", None):
            p_canon.gender = p_merged.gender
        if p_canon.tshirt_size in ("UNKNOWN", "", None) and p_merged.tshirt_size not in ("UNKNOWN", "", None):
            p_canon.tshirt_size = p_merged.tshirt_size
        if p_canon.accommodation_requested in ("UNKNOWN", "", None) and p_merged.accommodation_requested not in ("UNKNOWN", "", None):
            p_canon.accommodation_requested = p_merged.accommodation_requested
        if not p_canon.phone and p_merged.phone:
            p_canon.phone = p_merged.phone
        if not p_canon.age and p_merged.age:
            p_canon.age = p_merged.age

        p_canon.version += 1
        p_canon.updated_at = now()
        session.add(p_canon)

        # 2. Mark merged participant as MERGED
        p_merged.status = "MERGED"
        p_merged.canonical_participant_id = canonical_id
        p_merged.version += 1
        p_merged.updated_at = now()
        session.add(p_merged)

        # 3. Repoint linked registrations
        merged_regs = session.exec(select(Registration).where(Registration.participant_id == merged_id)).all()
        repointed_reg_ids: List[str] = []
        for reg in merged_regs:
            # Check if canonical already has this registration
            existing_canon_reg = session.exec(
                select(Registration).where(
                    Registration.participant_id == canonical_id,
                    Registration.event_id == reg.event_id,
                )
            ).first()
            if not existing_canon_reg:
                reg.participant_id = canonical_id
                reg.version += 1
                reg.updated_at = now()
                session.add(reg)
                repointed_reg_ids.append(reg.id)

        # 4. Repoint linked merchandise claims
        merged_claims = session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == merged_id)).all()
        repointed_claim_ids: List[str] = []
        for clm in merged_claims:
            clm.canonical_participant_id = canonical_id
            clm.version += 1
            clm.updated_at = now()
            session.add(clm)
            repointed_claim_ids.append(clm.id)

        # 5. Record MergeRecord for full byte-identical undo
        merge_rec = MergeRecord(
            canonical_participant_id=canonical_id,
            merged_participant_id=merged_id,
            merge_details={
                "canonical_before": canon_before,
                "merged_before": merged_before,
                "repointed_registrations": repointed_reg_ids,
                "repointed_claims": repointed_claim_ids,
                "candidate_id": candidate_id,
            },
            reason=req.reason,
            merged_by=req.actor.id,
            merged_at=now(),
            is_reverted=False,
        )
        session.add(merge_rec)

        # 6. Mark DuplicateCandidate resolved if specified
        if candidate_id:
            cand = session.get(DuplicateCandidate, candidate_id)
            if cand:
                cand.status = "RESOLVED"
                session.add(cand)

        session.flush()

        return {
            "merge_record_id": merge_rec.id,
            "canonical_id": canonical_id,
            "merged_id": merged_id,
            "repointed_registrations_count": len(repointed_reg_ids),
            "repointed_claims_count": len(repointed_claim_ids),
        }


# ==============================================================================
# 5. Participant Undo Merge
# ==============================================================================
@register_change_handler("participant.undo_merge")
class ParticipantUndoMergeHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        merge_id = req.entity_id or req.payload.get("merge_id")
        rec = session.get(MergeRecord, merge_id)
        if not rec:
            return [Violation(
                code="MERGE_RECORD_NOT_FOUND",
                severity=Severity.CRITICAL,
                hard=True,
                message=f"MergeRecord {merge_id} not found.",
            )]
        if rec.is_reverted:
            return [Violation(
                code="ALREADY_REVERTED",
                severity=Severity.HIGH,
                hard=True,
                message=f"Merge {merge_id} has already been undone.",
            )]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        merge_id = req.entity_id or req.payload.get("merge_id")
        rec = session.get(MergeRecord, merge_id)
        return {"merge_record_id": merge_id, "is_reverted": rec.is_reverted if rec else False}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        merge_id = req.entity_id or req.payload.get("merge_id")
        rec = session.get(MergeRecord, merge_id)
        if not rec:
            return {}

        details = rec.merge_details
        canon_before = details.get("canonical_before", {})
        merged_before = details.get("merged_before", {})
        repointed_regs = details.get("repointed_registrations", [])
        repointed_claims = details.get("repointed_claims", [])
        candidate_id = details.get("candidate_id")

        p_canon = session.get(Participant, rec.canonical_participant_id)
        p_merged = session.get(Participant, rec.merged_participant_id)

        # 1. Restore byte-identical fields for both participants
        if p_merged and merged_before:
            _restore_participant_from_dict(p_merged, merged_before)
            session.add(p_merged)

        if p_canon and canon_before:
            _restore_participant_from_dict(p_canon, canon_before)
            session.add(p_canon)

        # 2. Restore repointed registrations back to merged participant
        for reg_id in repointed_regs:
            reg = session.get(Registration, reg_id)
            if reg:
                reg.participant_id = rec.merged_participant_id
                reg.version += 1
                reg.updated_at = now()
                session.add(reg)

        # 3. Restore repointed claims back to merged participant
        for clm_id in repointed_claims:
            clm = session.get(MerchClaim, clm_id)
            if clm:
                clm.canonical_participant_id = rec.merged_participant_id
                clm.version += 1
                clm.updated_at = now()
                session.add(clm)

        # 4. Mark MergeRecord as reverted
        rec.is_reverted = True
        rec.reverted_at = now()
        rec.reverted_by = req.actor.id
        session.add(rec)

        # 5. Restore candidate status to PENDING
        if candidate_id:
            cand = session.get(DuplicateCandidate, candidate_id)
            if cand:
                cand.status = "PENDING"
                session.add(cand)

        session.flush()

        return {
            "merge_record_id": rec.id,
            "restored_canonical_id": rec.canonical_participant_id,
            "restored_participant_id": rec.merged_participant_id,
            "status": "REVERTED",
        }


# ==============================================================================
# 6. Field Verification Handler
# ==============================================================================
@register_change_handler("unknowns.verify_field")
class FieldVerifyHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        payload = req.payload
        field = payload.get("field")
        value = payload.get("value")
        if not field or value is None:
            return [Violation(
                code="REQUIRED_FIELD_MISSING",
                severity=Severity.HIGH,
                hard=True,
                message="Field name and verified value must be provided.",
            )]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        p = session.get(Participant, req.entity_id)
        if p and hasattr(p, req.payload.get("field", "")):
            return {req.payload["field"]: getattr(p, req.payload["field"])}
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        payload = req.payload
        entity_type = req.entity_type or payload.get("entity_type", "participant")
        entity_id = req.entity_id or payload.get("entity_id")
        field = payload.get("field")
        value = payload.get("value")
        source = payload.get("source", "DESK_VERIFICATION")
        verifier = payload.get("verifier") or req.actor.id

        if entity_type == "participant":
            p = session.get(Participant, entity_id)
            if p and hasattr(p, field):
                setattr(p, field, value)
                p.version += 1
                p.updated_at = now()
                session.add(p)

        ver = FieldVerification(
            entity_type=entity_type,
            entity_id=entity_id,
            field=field,
            status="VERIFIED",
            value=str(value),
            source=source,
            verified_by=verifier,
            verified_at=now(),
            owner=req.actor.role,
            created_at=now(),
        )
        session.add(ver)
        session.flush()

        return {
            "verification_id": ver.id,
            "entity_id": entity_id,
            "field": field,
            "value": value,
            "status": "VERIFIED",
        }


# ==============================================================================
# 7. Contingent Update Handler
# ==============================================================================
@register_change_handler("contingent.update")
class ContingentUpdateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        c = session.get(Contingent, req.entity_id)
        if not c:
            return [Violation(
                code="CONTINGENT_NOT_FOUND",
                severity=Severity.CRITICAL,
                hard=True,
                message=f"Contingent {req.entity_id} not found.",
            )]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        c = session.get(Contingent, req.entity_id)
        return {
            "id": c.id,
            "name": c.name,
            "preferences": c.preferences,
            "contact_name": c.contact_name,
            "contact_phone": c.contact_phone,
            "contact_email": c.contact_email,
            "version": c.version,
        } if c else {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        c = session.get(Contingent, req.entity_id)
        if not c:
            return {}
        payload = req.payload
        for f in ("preferences", "contact_name", "contact_phone", "contact_email", "leader", "escort"):
            if f in payload:
                setattr(c, f, payload[f])

        c.version += 1
        c.updated_at = now()
        session.add(c)
        session.flush()
        return {
            "id": c.id,
            "name": c.name,
            "preferences": c.preferences,
            "version": c.version,
        }
