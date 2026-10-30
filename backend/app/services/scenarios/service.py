# OWNER: P1
import logging
import os
import sqlite3
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.change_service import ChangeHandler, ChangeRequest, execute_change
from app.core.clock import now
from app.core.db import close_scenario_engine, get_engine, use_scenario
from app.core.registry import register_change_handler
from app.models.accommodation import ExternalProperty, Room, StayAssignment
from app.models.change import ChangeSet, Scenario
from app.models.events import Conflict
from app.models.ops import Incident
from app.models.participants import Participant
from app.schemas.common import Actor

logger = logging.getLogger("festos.scenarios.service")

SCENARIOS_DIR = "scenarios"
MAX_ACTIVE_SCENARIOS = 10
SCENARIO_MAX_AGE_HOURS = 48


def _cleanup_old_scenarios(session: Session) -> None:
    """Enforces retention limits on scenario history (max active count and max age)."""
    cutoff = now() - timedelta(hours=SCENARIO_MAX_AGE_HOURS)
    scenarios = session.exec(select(Scenario)).all()

    # Discard expired scenarios
    for scn in scenarios:
        if scn.status == "DRAFT" and scn.created_at < cutoff:
            logger.info(f"Auto-discarding expired scenario {scn.id}")
            scn.status = "DISCARDED"
            session.add(scn)
            close_scenario_engine(scn.id)
            db_path = os.path.join(SCENARIOS_DIR, f"{scn.id}.db")
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception as e:
                    logger.warning(f"Could not remove db file {db_path}: {e}")

    # Enforce active quota
    active = [s for s in scenarios if s.status == "DRAFT"]
    if len(active) > MAX_ACTIVE_SCENARIOS:
        active.sort(key=lambda s: s.created_at)
        excess = len(active) - MAX_ACTIVE_SCENARIOS
        for s_to_discard in active[:excess]:
            s_to_discard.status = "DISCARDED"
            session.add(s_to_discard)
            close_scenario_engine(s_to_discard.id)
            db_path = os.path.join(SCENARIOS_DIR, f"{s_to_discard.id}.db")
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception:
                    pass

    session.flush()


def fork_database(scenario_id: str, live_session: Session) -> str:
    """Forks the current live database state into scenarios/<scenario_id>.db using SQLite backup API.

    In a PostgreSQL production deployment, this would execute:
    CREATE SCHEMA scenario_<id> (or provision a copy-on-write clone DB).
    """
    os.makedirs(SCENARIOS_DIR, exist_ok=True)
    dest_path = os.path.join(SCENARIOS_DIR, f"{scenario_id}.db")
    if os.path.exists(dest_path):
        try:
            os.remove(dest_path)
        except Exception:
            pass

    live_engine = live_session.get_bind() if live_session is not None else get_engine()
    with live_engine.connect() as conn:
        raw_live_conn = conn.connection.dbapi_connection
        dst = sqlite3.connect(dest_path)
        raw_live_conn.backup(dst)
        dst.close()

    return dest_path


def create_scenario(
    session: Session,
    name: str,
    description: Optional[str] = None,
    actor_id: str = "SYSTEM",
) -> Dict[str, Any]:
    """Creates a new scenario by forking the live database into an isolated sandbox."""
    _cleanup_old_scenarios(session)

    scenario_id = f"scn_{uuid.uuid4().hex[:8]}"
    live_cs_count = len(session.exec(select(ChangeSet)).all())

    # Fork database
    dest_path = fork_database(scenario_id, session)

    scenario = Scenario(
        id=scenario_id,
        name=name,
        description=description,
        created_at=now(),
        created_by=actor_id,
        status="DRAFT",
        forked_at=now(),
        live_changeset_count_at_fork=live_cs_count,
        recorded_actions=[],
    )
    session.add(scenario)
    session.commit()

    return {
        "scenario_id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "status": scenario.status,
        "created_at": scenario.created_at.isoformat(),
        "forked_at": scenario.forked_at.isoformat(),
        "sandbox_url": f"sqlite:///./{dest_path.replace(os.sep, '/')}",
        "rebase_baseline_changesets": live_cs_count,
    }


def list_scenarios(
    session: Session,
    status_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists scenarios with optional status filter."""
    query = select(Scenario).order_by(Scenario.created_at.desc())
    if status_filter:
        query = query.where(Scenario.status == status_filter.upper())

    scenarios = session.exec(query).all()
    items = []
    for s in scenarios:
        items.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "status": s.status,
            "created_by": s.created_by,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "actions_count": len(s.recorded_actions or []),
        })

    return {
        "scenarios": items,
        "total": len(items),
    }


def get_scenario(session: Session, scenario_id: str) -> Optional[Dict[str, Any]]:
    """Returns scenario details and recorded actions."""
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        return None

    return {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "status": scenario.status,
        "created_by": scenario.created_by,
        "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
        "forked_at": scenario.forked_at.isoformat() if scenario.forked_at else None,
        "recorded_actions": scenario.recorded_actions or [],
    }


def execute_action_in_scenario(
    session: Session,
    scenario_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: Dict[str, Any],
    reason: Optional[str] = None,
    actor: Optional[Actor] = None,
) -> Dict[str, Any]:
    """Applies a ChangeRequest exclusively inside the scenario's sandbox database."""
    scenario = session.get(Scenario, scenario_id)
    if not scenario or scenario.status != "DRAFT":
        raise ValueError(f"Scenario '{scenario_id}' is not in active DRAFT status")

    act = actor or Actor(id="usr_sim", name="Simulation Operator", role="FESTIVAL_DIRECTOR")
    req = ChangeRequest(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        reason=reason or f"Simulated action in {scenario_id}",
        actor=act,
    )

    # Execute in sandbox DB
    with use_scenario(scenario_id):
        scen_engine = get_engine()
        with Session(scen_engine) as scen_session:
            result = execute_change(req, scen_session)
            scen_session.commit()

    # Record action in live scenario metadata
    recorded = list(scenario.recorded_actions or [])
    recorded.append({
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
        "reason": reason,
        "applied_at": now().isoformat(),
    })
    scenario.recorded_actions = recorded
    session.add(scenario)
    session.commit()

    return {
        "scenario_id": scenario_id,
        "action": action,
        "status": "APPLIED_IN_SANDBOX",
        "result": result.data,
    }


def _compute_state_metrics(s: Session) -> Dict[str, Any]:
    """Calculates key operational metrics for state comparison."""
    # Beds
    rooms = s.exec(select(Room)).all()
    ext_props = s.exec(select(ExternalProperty)).all()
    total_beds = sum(r.capacity for r in rooms if r.status == "AVAILABLE") + sum(p.beds for p in ext_props)

    stay_asns = s.exec(select(StayAssignment).where(StayAssignment.status == "ACTIVE")).all()
    occupied_beds = len(stay_asns)
    available_beds = max(0, total_beds - occupied_beds)

    # Participants unplaced
    all_participants = s.exec(select(Participant).where(Participant.status.in_(["EXPECTED", "ARRIVED", "CHECKED_IN"]))).all()
    assigned_pids = {sa.participant_id for sa in stay_asns}
    unplaced = sum(1 for p in all_participants if p.id not in assigned_pids and p.accommodation_requested in ("YES", "UNKNOWN"))

    # Cost calculation
    cost_inr = sum(p.beds * p.cost_per_bed_night for p in ext_props)

    # Conflicts
    conflicts_count = len(s.exec(select(Conflict).where(Conflict.status == "OPEN")).all())

    return {
        "available_beds": available_beds,
        "unplaced_participants": unplaced,
        "cost_inr": float(cost_inr),
        "conflicts_count": conflicts_count,
        "high_risks_count": unplaced + conflicts_count,
    }


def compare_scenario(session: Session, scenario_id: str) -> Dict[str, Any]:
    """Computes metric diffs comparing live state vs simulated sandbox state."""
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        raise ValueError(f"Scenario '{scenario_id}' not found")

    # 1. Live state metrics
    live_state = _compute_state_metrics(session)

    # 2. Simulated sandbox state metrics
    with use_scenario(scenario_id):
        scen_engine = get_engine()
        with Session(scen_engine) as scen_session:
            sim_state = _compute_state_metrics(scen_session)

    # 3. Deltas
    diff = {
        "beds_delta": sim_state["available_beds"] - live_state["available_beds"],
        "unplaced_delta": sim_state["unplaced_participants"] - live_state["unplaced_participants"],
        "cost_delta_inr": round(sim_state["cost_inr"] - live_state["cost_inr"], 2),
        "conflicts_delta": sim_state["conflicts_count"] - live_state["conflicts_count"],
        "risks_delta": sim_state["high_risks_count"] - live_state["high_risks_count"],
    }

    summary_text = (
        f"Scenario '{scenario.name}' results in: "
        f"{diff['beds_delta']:+d} beds, "
        f"{diff['unplaced_delta']:+d} unplaced participants, "
        f"₹{diff['cost_delta_inr']:+.2f} cost change, "
        f"{diff['conflicts_delta']:+d} conflicts."
    )

    return {
        "scenario_id": scenario_id,
        "live_state": live_state,
        "simulated_state": sim_state,
        "diff": diff,
        "summary": summary_text,
    }


def commit_scenario(
    session: Session,
    scenario_id: str,
    actor: Actor,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Replays all recorded scenario changes onto the live production database."""
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        raise ValueError(f"Scenario '{scenario_id}' not found")
    if scenario.status != "DRAFT":
        raise ValueError(f"Scenario '{scenario_id}' cannot be committed (current status: {scenario.status})")

    # Rebase check: verify if live state mutated since fork
    current_live_cs_count = len(session.exec(select(ChangeSet)).all())
    rebase_status = "CLEAN"
    warnings = []
    if current_live_cs_count > scenario.live_changeset_count_at_fork:
        rebase_status = "DIVERGED"
        warnings.append(
            f"Live database has mutated since this scenario was forked "
            f"({current_live_cs_count} live changesets vs {scenario.live_changeset_count_at_fork} at fork). "
            f"Changes were replayed on top of current live state."
        )

    # Replay recorded actions on LIVE session
    replayed_ids = []
    for action_rec in (scenario.recorded_actions or []):
        req = ChangeRequest(
            action=action_rec["action"],
            entity_type=action_rec.get("entity_type", "scenario_entity"),
            entity_id=action_rec.get("entity_id", "sim_entity"),
            payload=action_rec.get("payload", {}),
            reason=reason or action_rec.get("reason") or f"Committed from scenario {scenario_id}",
            actor=actor,
        )
        res = execute_change(req, session)
        if res.change_set_id:
            replayed_ids.append(res.change_set_id)

    scenario.status = "COMMITTED"
    session.add(scenario)
    session.commit()

    # Close and clean sandbox engine
    close_scenario_engine(scenario_id)

    return {
        "scenario_id": scenario_id,
        "status": "COMMITTED",
        "replayed_actions_count": len(scenario.recorded_actions or []),
        "rebase_status": rebase_status,
        "live_changesets_created": replayed_ids,
        "warnings": warnings,
    }


def discard_scenario(session: Session, scenario_id: str) -> Dict[str, Any]:
    """Discards a scenario and deletes its sandbox database file."""
    scenario = session.get(Scenario, scenario_id)
    if scenario:
        scenario.status = "DISCARDED"
        session.add(scenario)
        session.commit()

    close_scenario_engine(scenario_id)
    db_path = os.path.join(SCENARIOS_DIR, f"{scenario_id}.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception as e:
            logger.warning(f"Could not remove sandbox db {db_path}: {e}")

    return {"scenario_id": scenario_id, "status": "DISCARDED"}


@register_change_handler("incident.simulate")
class IncidentSimulateHandler(ChangeHandler):
    """Change handler allowing simulated incident to be replayed or logged cleanly."""

    def validate(self, req: ChangeRequest, session: Session) -> List[Any]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        payload = req.payload
        inc = Incident(
            title=f"{payload.get('incident_type')} at {payload.get('target_id')}",
            description=payload.get("details") or "Simulated incident",
            severity=int(payload.get("severity", 4)),
            status="OPEN",
        )
        session.add(inc)
        session.flush()
        return {"incident_id": inc.id}


def simulate_incident_in_scenario(
    session: Session,
    scenario_id: str,
    incident_type: str,
    target_id: str,
    severity: int = 4,
    details: Optional[str] = None,
    actor: Optional[Actor] = None,
) -> Dict[str, Any]:
    """Incident simulation adapter allowing Prompt 14 drills to test crises in a sandbox."""
    scenario = session.get(Scenario, scenario_id)
    if not scenario or scenario.status != "DRAFT":
        raise ValueError(f"Scenario '{scenario_id}' is not in active DRAFT status")

    act = actor or Actor(id="usr_incident", name="Incident Simulator", role="FESTIVAL_DIRECTOR")

    people_affected = 0
    actions_required = []

    with use_scenario(scenario_id):
        scen_engine = get_engine()
        with Session(scen_engine) as scen_session:
            # 1. Create incident record in sandbox
            inc = Incident(
                title=f"{incident_type} at {target_id}",
                description=details or f"Simulated {incident_type} drill",
                severity=int(severity),
                reported_by=act.name,
                status="OPEN",
            )
            scen_session.add(inc)

            # 2. Apply simulated disruption
            if "HOSTEL" in incident_type.upper():
                rooms = scen_session.exec(select(Room).where(Room.block == target_id)).all()
                if not rooms:
                    # Target may be single room or general block
                    rooms = scen_session.exec(select(Room)).all()[:10]
                for r in rooms:
                    r.status = "MAINTENANCE"
                    scen_session.add(r)
                people_affected = sum(r.capacity for r in rooms)
                actions_required.extend([
                    f"Reallocate {people_affected} residents to external properties",
                    f"Schedule {max(1, people_affected // 15)} emergency shuttle runs",
                ])
            elif "VENDOR" in incident_type.upper():
                people_affected = 250
                actions_required.extend([
                    "Activate backup vendor contract",
                    "Reroute 250 dietary meal vouchers",
                ])

            scen_session.commit()
            inc_id = inc.id

    # Record action in scenario metadata
    recorded = list(scenario.recorded_actions or [])
    recorded.append({
        "action": "incident.simulate",
        "entity_type": "incident",
        "entity_id": inc_id,
        "payload": {
            "incident_type": incident_type,
            "target_id": target_id,
            "severity": severity,
            "details": details,
        },
        "applied_at": now().isoformat(),
    })
    scenario.recorded_actions = recorded
    session.add(scenario)
    session.commit()

    return {
        "scenario_id": scenario_id,
        "incident_id": inc_id,
        "status": "SIMULATED",
        "impact": {
            "affected_people": people_affected,
            "immediate_actions_required": actions_required,
        },
    }
