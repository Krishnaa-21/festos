# OWNER: P2
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from app.core.clock import now
from app.core.registry import register_change_handler
from app.models.change import Assumption, ChangeSet
from app.schemas.assumptions import (
    AssumptionDependentsResponse,
    AssumptionHistoryItem,
    AssumptionItem,
)
from app.schemas.common import Actor, Severity, Violation

logger = logging.getLogger("festos.assumptions")

# In-memory typed cache for high-frequency reads
_ASSUMPTION_CACHE: Dict[str, Any] = {}

# Comprehensive metadata catalogue for all standard FestOS assumption keys
# (context section 10 and reference pack)
ASSUMPTION_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "cleaning_buffer_minutes": {
        "default": "180",
        "type": "integer",
        "owner": "P2",
        "source": "SPEC",
        "reason": "Turnaround buffer required between hostel bed occupants",
        "impact": "Recalculates turnaround and available bed intervals",
        "modules": ["accommodation", "schedule"],
        "desc": "Required buffer time (in minutes) for room cleaning and prep before new occupant arrives.",
    },
    "late_night_start": {
        "default": "22:00",
        "type": "time",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Campus noise boundary and transport curfew start",
        "impact": "Limits late night outdoor events and restricts transit",
        "modules": ["events", "transport", "accommodation"],
        "desc": "Defines beginning of quiet hours and curfew window.",
    },
    "late_night_end": {
        "default": "06:00",
        "type": "time",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Campus noise boundary and transport curfew end",
        "impact": "Restricts early morning scheduling and shuttle operations",
        "modules": ["events", "transport", "accommodation"],
        "desc": "Defines end of quiet hours and resumption of regular movement.",
    },
    "minor_age_threshold": {
        "default": "18",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Minor safety threshold requiring guardian/escort verification",
        "impact": "Forces guardian verification and restricts unverified external placements",
        "modules": ["imports", "accommodation", "transport"],
        "desc": "Age cutoff below which a participant is legally a minor and subject to safety restrictions.",
    },
    "setup_buffer_min": {
        "default": "15",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Venue setup buffer required before event heat begins",
        "impact": "Extends required venue booking window",
        "modules": ["schedule", "venues"],
        "desc": "Minimum preparation and sound-check window before event session start.",
    },
    "teardown_buffer_min": {
        "default": "15",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Venue clearing buffer after event heat completes",
        "impact": "Extends required venue booking window",
        "modules": ["schedule", "venues"],
        "desc": "Minimum clearing and reset window following event session end.",
    },
    "venue_travel_min": {
        "default": "15",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Default travel buffer between any two campus venues unless overridden in travel_time",
        "impact": "Flags participant transit schedule conflicts",
        "modules": ["schedule", "ops"],
        "desc": "Transit window allowed between events at different campus locations.",
    },
    "round_result_buffer_min": {
        "default": "60",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Judges tabulation and compilation buffer between competition stages",
        "impact": "Controls minimum gap before subsequent round start",
        "modules": ["schedule", "events"],
        "desc": "Time reserved for judges scoring compilation and leaderboard announcement.",
    },
    "semifinal_ratio": {
        "default": "0.5",
        "type": "float",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Proportion of preliminary competitors advancing to semifinal round",
        "impact": "Determines semifinal session count and participant qualification",
        "modules": ["events", "schedule"],
        "desc": "Advancement ratio from prelims to semifinals.",
    },
    "finalist_ratio": {
        "default": "0.10",
        "type": "float",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Proportion of participants advancing to finals",
        "impact": "Determines final heat capacity",
        "modules": ["events", "schedule"],
        "desc": "Fraction of preliminary field advancing to final round.",
    },
    "finalist_min": {
        "default": "8",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Minimum number of competitors in an event final",
        "impact": "Overrides finalist_ratio when participant count is small",
        "modules": ["events", "schedule"],
        "desc": "Floor for number of finalists in any multi-stage event.",
    },
    "checkin_buffer_min": {
        "default": "60",
        "type": "integer",
        "owner": "P2",
        "source": "SPEC",
        "reason": "Arrival check-in queue buffer before first event participation",
        "impact": "Affects arrival scheduling and early check-in queue sizing",
        "modules": ["checkin", "schedule"],
        "desc": "Buffer time allotted for badge issuance, kit collection, and room checkin before first event.",
    },
    "expected_participants_narrative": {
        "default": "2400",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Narrative planning figure (never forced; shown alongside 2,836 raw count)",
        "impact": "Reconciliation benchmark for gap analysis",
        "modules": ["imports", "reconciliation", "dashboard"],
        "desc": "Expected attendance figure from marketing and budget narratives, contrasted against raw roster.",
    },
    "external_budget_inr": {
        "default": "NULL",
        "type": "string",
        "owner": "P2",
        "source": "SPEC",
        "reason": "External accommodation budget ceiling (Director sets it; unset by default)",
        "impact": "Engine flags budget-unset mode; triggers Director approval once cost cap is reached",
        "modules": ["accommodation", "finance"],
        "desc": "Financial ceiling for external hotel room reservations.",
    },
    "external_property_accessibility": {
        "default": "UNVERIFIED",
        "type": "string",
        "owner": "P2",
        "source": "SPEC",
        "reason": "External properties lack verified accessibility data; wheelchair users are not placed externally",
        "impact": "Restricts placement of participants with physical accessibility needs",
        "modules": ["accommodation"],
        "desc": "Verification state of external properties regarding ramps and accessible bathrooms.",
    },
    "external_property_gender_suitability": {
        "default": "UNVERIFIED",
        "type": "string",
        "owner": "P2",
        "source": "SPEC",
        "reason": "External properties lack verified gender segregation structures",
        "impact": "Prevents unverified placements where gender constraints apply",
        "modules": ["accommodation"],
        "desc": "Verification state of external facilities for safe gender-segregated lodging.",
    },
    "equipment_default_quantity": {
        "default": "1",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Default requisition quantity per named equipment item unless text specifies otherwise",
        "impact": "Inventory demand allocation solver baseline",
        "modules": ["logistics", "events"],
        "desc": "Default unit count assumed per requested piece of equipment.",
    },
    "shuttle_capacity_seats": {
        "default": "12",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Placeholder shuttle van passenger capacity",
        "impact": "Affects transit throughput and trip frequency calculations",
        "modules": ["transport"],
        "desc": "Seating capacity assumed per transport shuttle van.",
    },
    "shuttle_vehicle_count": {
        "default": "3",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Placeholder fleet vehicle count available for shuttles",
        "impact": "Transit capacity constraint",
        "modules": ["transport"],
        "desc": "Number of shuttle vehicles in active service rotation.",
    },
    "shuttle_travel_min": {
        "default": "25",
        "type": "integer",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Average one-way travel duration between campus and external properties",
        "impact": "Transit schedule timing and departure buffer",
        "modules": ["transport"],
        "desc": "Estimated road transit minutes between external stays and campus.",
    },
    "transport_hours": {
        "default": "06:00-22:00",
        "type": "time_range",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Operating window for standard shuttle transit operations",
        "impact": "Restricts shuttle runs; requires special approval for late night runs",
        "modules": ["transport"],
        "desc": "Authorized hours during which shuttles operate regular loops.",
    },
    "accom_plan_c_weights": {
        "default": "cohesion 0.5, cost 0.3, travel 0.2",
        "type": "string",
        "owner": "P2",
        "source": "SPEC",
        "reason": "Plan C balanced accommodation solver optimization weights",
        "impact": "Determines trade-off balance between cohesion, cost, and travel",
        "modules": ["accommodation"],
        "desc": "Multi-objective weights applied in Plan C allocation.",
    },
    "include_leaders_escorts_in_demand": {
        "default": "true",
        "type": "boolean",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Include contingent leaders and escorts in total bed demand calculations",
        "impact": "Increases overall bed demand by ~76 beds",
        "modules": ["accommodation", "reconciliation"],
        "desc": "Controls whether leader/escort roles are factored into housing quotas.",
    },
    "count_unknown_accommodation_as_possible": {
        "default": "true",
        "type": "boolean",
        "owner": "P1",
        "source": "SPEC",
        "reason": "Report UNKNOWN accommodation requests separately as potential demand",
        "impact": "Highlights uncertainty and prevents under-allocating buffer beds",
        "modules": ["accommodation", "reconciliation"],
        "desc": "Whether unconfirmed housing requests are included in secondary demand forecasts.",
    },
    "late_arrival_policy": {
        "default": "PENDING_DIRECTOR_DECISION",
        "type": "string",
        "owner": "P2",
        "source": "SPEC",
        "reason": "Policy governing late entrant qualification and wildcard finals",
        "impact": "Requires explicit Festival Director decision and approval",
        "modules": ["schedule", "events", "approvals"],
        "desc": "Status of director policy regarding 1 Nov late-wave entrants.",
    },
}


def parse_typed_value(key: str, val_str: str) -> Tuple[Any, str]:
    """Converts a raw string value to its typed equivalent based on key definition.
    Returns: (typed_value, type_label)
    Raises ValueError if conversion fails.
    """
    definition = ASSUMPTION_DEFINITIONS.get(key, {})
    val_type = definition.get("type", "string")

    clean = val_str.strip() if val_str is not None else ""
    if clean.upper() == "NULL" or clean == "":
        return None, val_type

    if val_type == "integer":
        val = int(clean)
        if key in (
            "cleaning_buffer_minutes",
            "minor_age_threshold",
            "setup_buffer_min",
            "teardown_buffer_min",
            "venue_travel_min",
            "round_result_buffer_min",
            "checkin_buffer_min",
            "shuttle_travel_min",
            "shuttle_capacity_seats",
            "shuttle_vehicle_count",
            "finalist_min",
            "equipment_default_quantity",
        ) and val < 0:
            raise ValueError(f"Value for '{key}' cannot be negative: {val}")
        return val, "integer"
    elif val_type == "float":
        val_f = float(clean)
        if val_f < 0:
            raise ValueError(f"Value for '{key}' cannot be negative: {val_f}")
        return val_f, "float"
    elif val_type == "boolean":
        lower = clean.lower()
        if lower in ("true", "t", "yes", "y", "1"):
            return True, "boolean"
        elif lower in ("false", "f", "no", "n", "0"):
            return False, "boolean"
        raise ValueError(f"Invalid boolean value: '{clean}'")
    elif val_type == "time":
        # Format HH:MM
        parts = clean.split(":")
        if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
            raise ValueError(f"Invalid time format (expected HH:MM): '{clean}'")
        return clean, "time"
    elif val_type == "time_range":
        # Format HH:MM-HH:MM
        if "-" not in clean:
            raise ValueError(f"Invalid time range format (expected HH:MM-HH:MM): '{clean}'")
        return clean, "time_range"

    return clean, "string"


def get_assumption(key: str, session: Optional[Session] = None) -> Any:
    """Helper to fetch a typed assumption value with memory caching.
    Invalidates when assumptions are mutated.
    """
    if key in _ASSUMPTION_CACHE:
        return _ASSUMPTION_CACHE[key]

    definition = ASSUMPTION_DEFINITIONS.get(key)
    raw_val: Optional[str] = None

    if session is not None:
        row = session.exec(select(Assumption).where(Assumption.key == key)).first()
        if row:
            raw_val = row.value
    else:
        # Open quick DB session if available
        try:
            from app.core.db import get_engine
            with Session(get_engine()) as temp_session:
                row = temp_session.exec(select(Assumption).where(Assumption.key == key)).first()
                if row:
                    raw_val = row.value
        except Exception:
            pass

    if raw_val is None and definition:
        raw_val = definition["default"]

    if raw_val is None:
        return None

    try:
        typed_val, _ = parse_typed_value(key, raw_val)
        _ASSUMPTION_CACHE[key] = typed_val
        return typed_val
    except Exception:
        return raw_val


def invalidate_assumption_cache(key: Optional[str] = None) -> None:
    """Invalidates the in-memory assumption cache."""
    global _ASSUMPTION_CACHE
    if key:
        _ASSUMPTION_CACHE.pop(key, None)
    else:
        _ASSUMPTION_CACHE.clear()


# Alias for backward compatibility
ASSUMPTION_CATALOG = ASSUMPTION_DEFINITIONS
clear_assumption_cache = invalidate_assumption_cache


def update_assumption(
    session: Session,
    key: str,
    value: str,
    actor: Actor,
    reason: Optional[str] = None,
    dry_run: bool = False,
):
    from app.core.change_service import ChangeRequest, execute_change
    req = ChangeRequest(
        action="assumptions.update",
        entity_type="assumption",
        entity_id=key,
        payload={"key": key, "value": value, "new_value": value},
        reason=reason or f"Updated assumption {key}",
        actor=actor,
        dry_run=dry_run,
    )
    return execute_change(req, session)


# -------------------------------------------------------------
# ChangeService Handler: assumptions.update
# -------------------------------------------------------------
@register_change_handler("assumptions.update")

class AssumptionUpdateHandler:
    def validate(self, req: Any, session: Session) -> List[Violation]:
        violations: List[Violation] = []
        payload = req.payload or {}
        key = payload.get("key") or req.entity_id
        val_str = str(payload.get("value", ""))

        if not key:
            violations.append(
                Violation(code="MISSING_KEY", severity=Severity.CRITICAL, hard=True, message="Assumption key is required")
            )
            return violations

        # Validate typed value conversion
        try:
            parse_typed_value(key, val_str)
        except ValueError as e:
            violations.append(
                Violation(
                    code="INVALID_ASSUMPTION_VALUE",
                    severity=Severity.HIGH,
                    hard=True,
                    message=f"Invalid value for assumption '{key}': {e}",
                )
            )

        return violations

    def snapshot(self, req: Any, session: Session) -> Dict[str, Any]:
        key = req.payload.get("key") or req.entity_id
        row = session.exec(select(Assumption).where(Assumption.key == key)).first()
        if row:
            return {
                "id": row.id,
                "key": row.key,
                "value": row.value,
                "owner": row.owner,
                "source": row.source,
                "reason": row.reason,
                "impact_if_changed": row.impact_if_changed,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        return {}

    def apply(self, req: Any, session: Session) -> Dict[str, Any]:
        payload = req.payload or {}
        key = payload.get("key") or req.entity_id
        new_val = str(payload.get("value", "")).strip()

        row = session.exec(select(Assumption).where(Assumption.key == key)).first()
        old_val = row.value if row else None

        if row:
            row.value = new_val
            if req.reason:
                row.reason = req.reason
            row.updated_at = now()
            session.add(row)
        else:
            defn = ASSUMPTION_DEFINITIONS.get(key, {})
            row = Assumption(
                key=key,
                value=new_val,
                owner=defn.get("owner", "P2"),
                source=defn.get("source", "SPEC"),
                reason=req.reason or defn.get("reason", "Operational configuration"),
                impact_if_changed=defn.get("impact", "Modifies system calculation"),
                updated_at=now(),
            )
            session.add(row)

        session.flush()

        # Invalidate in-memory cache
        invalidate_assumption_cache(key)

        defn = ASSUMPTION_DEFINITIONS.get(key, {})
        return {
            "key": key,
            "old_value": old_val,
            "new_value": new_val,
            "dependent_modules": defn.get("modules", []),
        }

    def risk(self, req: Any) -> str:
        key = req.payload.get("key") or req.entity_id
        # High impact parameters require Director review unless Director role
        if key in ("minor_age_threshold", "cleaning_buffer_minutes", "late_arrival_policy", "expected_participants_narrative"):
            return "HIGH"
        return "LOW"

    def revert(self, change_set: Any, session: Session) -> None:
        prev = change_set.previous_state or {}
        key = prev.get("key")
        old_val = prev.get("value")
        if key and old_val is not None:
            row = session.exec(select(Assumption).where(Assumption.key == key)).first()
            if row:
                row.value = old_val
                row.updated_at = now()
                session.add(row)
                session.flush()
                invalidate_assumption_cache(key)


# -------------------------------------------------------------
# Read / Query Operations for Endpoints
# -------------------------------------------------------------
def list_assumptions(
    session: Session, owner: Optional[str] = None, q: Optional[str] = None
) -> List[AssumptionItem]:
    """Lists all assumptions from DB complemented by baseline metadata."""
    query = select(Assumption)
    if owner:
        query = query.where(Assumption.owner == owner.upper())
    results = session.exec(query).all()

    items: List[AssumptionItem] = []
    seen_keys = set()

    for row in results:
        seen_keys.add(row.key)
        defn = ASSUMPTION_DEFINITIONS.get(row.key, {})
        typed_val, val_type = parse_typed_value(row.key, row.value)

        # Check search query q
        if q:
            ql = q.lower()
            if ql not in row.key.lower() and ql not in row.reason.lower() and ql not in row.impact_if_changed.lower():
                continue

        items.append(
            AssumptionItem(
                id=row.id,
                key=row.key,
                value=row.value,
                typed_value=typed_val,
                type=val_type,
                owner=row.owner,
                source=row.source,
                reason=row.reason,
                impact_if_changed=row.impact_if_changed,
                updated_at=row.updated_at,
            )
        )

    # If any defined assumptions are not yet seeded, expose them as baseline
    for k, defn in ASSUMPTION_DEFINITIONS.items():
        if k not in seen_keys:
            if owner and defn.get("owner", "").upper() != owner.upper():
                continue
            if q:
                ql = q.lower()
                if ql not in k.lower() and ql not in defn.get("reason", "").lower():
                    continue
            typed_val, val_type = parse_typed_value(k, defn["default"])
            items.append(
                AssumptionItem(
                    id=f"asm_{k}",
                    key=k,
                    value=defn["default"],
                    typed_value=typed_val,
                    type=val_type,
                    owner=defn["owner"],
                    source=defn["source"],
                    reason=defn["reason"],
                    impact_if_changed=defn["impact"],
                    updated_at=now(),
                )
            )

    items.sort(key=lambda x: x.key)
    return items


def get_assumption_detail(session: Session, key: str) -> Optional[AssumptionItem]:
    row = session.exec(select(Assumption).where(Assumption.key == key)).first()
    defn = ASSUMPTION_DEFINITIONS.get(key, {})
    if not row and not defn:
        return None

    raw_val = row.value if row else defn["default"]
    typed_val, val_type = parse_typed_value(key, raw_val)

    return AssumptionItem(
        id=row.id if row else f"asm_{key}",
        key=key,
        value=raw_val,
        typed_value=typed_val,
        type=val_type,
        owner=row.owner if row else defn.get("owner", "P2"),
        source=row.source if row else defn.get("source", "SPEC"),
        reason=row.reason if row else defn.get("reason", "Operational configuration"),
        impact_if_changed=row.impact_if_changed if row else defn.get("impact", "Modifies system calculation"),
        updated_at=row.updated_at if row else now(),
    )


def get_assumption_history(session: Session, key: str) -> List[AssumptionHistoryItem]:
    """Fetches change history for an assumption key via ChangeSet records."""
    change_sets = session.exec(
        select(ChangeSet)
        .where(ChangeSet.action == "assumptions.update")
        .order_by(ChangeSet.applied_at.desc())
    ).all()

    history: List[AssumptionHistoryItem] = []
    for cs in change_sets:
        payload = cs.payload or {}
        cs_key = payload.get("key") or cs.entity_id
        if cs_key == key:
            prev = cs.previous_state or {}
            history.append(
                AssumptionHistoryItem(
                    change_set_id=cs.id,
                    actor_id=cs.actor_id,
                    actor_role=cs.actor_role,
                    previous_value=prev.get("value"),
                    new_value=str(payload.get("value", "")),
                    reason=cs.reason,
                    applied_at=cs.applied_at,
                )
            )
    return history


def get_assumption_dependents(
    key_or_session: Any = None,
    key: Optional[str] = None,
    session: Optional[Session] = None,
) -> AssumptionDependentsResponse:
    target_key = key if key is not None else str(key_or_session)

    defn = ASSUMPTION_DEFINITIONS.get(target_key, {})
    return AssumptionDependentsResponse(
        key=target_key,
        dependent_modules=defn.get("modules", ["system"]),
        description=defn.get(
            "desc",
            f"Configurable parameter affecting calculations across {', '.join(defn.get('modules', ['system']))}",
        ),
    )



def seed_all_assumptions(session: Session) -> int:
    """Seeds all 25 baseline assumption keys into database if not present."""
    count = 0
    for key, defn in ASSUMPTION_DEFINITIONS.items():
        existing = session.exec(select(Assumption).where(Assumption.key == key)).first()
        if not existing:
            asm = Assumption(
                key=key,
                value=defn["default"],
                owner=defn["owner"],
                source=defn["source"],
                reason=defn["reason"],
                impact_if_changed=defn["impact"],
                updated_at=now(),
            )
            session.add(asm)
            count += 1
    session.flush()
    invalidate_assumption_cache()
    return count

