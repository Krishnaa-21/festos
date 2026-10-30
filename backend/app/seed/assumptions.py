# OWNER: P1
from sqlmodel import Session, select

from app.core.clock import now
from app.core.registry import register_seeder
from app.models.change import Assumption

DEFAULT_ASSUMPTIONS = [
    ("cleaning_buffer_minutes", "180", "P2", "SPEC", "One configurable cleaning buffer assumption", "Recalculates turnaround"),
    ("late_night_start", "22:00", "P1", "SPEC", "Noise boundary start", "Limits late night events"),
    ("late_night_end", "06:00", "P1", "SPEC", "Noise boundary end", "Restricts early morning scheduling"),
    ("minor_age_threshold", "18", "P1", "SPEC", "Minor participant threshold", "Forces guardian / escort checks"),
    ("setup_buffer_min", "15", "P1", "SPEC", "Pre-event setup", "Adds room prep time"),
    ("teardown_buffer_min", "15", "P1", "SPEC", "Post-event teardown", "Adds teardown window"),
    ("venue_travel_min", "15", "P1", "SPEC", "Default venue travel time", "Flags transit conflicts"),
    ("round_result_buffer_min", "60", "P1", "SPEC", "Judges buffer", "Controls subsequent round start"),
    ("semifinal_ratio", "0.5", "P1", "SPEC", "Semifinal advancement proportion", "Affects stage counts"),
    ("finalist_ratio", "0.10", "P1", "SPEC", "Finalist advancement proportion", "Affects stage counts"),
    ("finalist_min", "8", "P1", "SPEC", "Minimum finalists", "Affects stage counts"),
    ("checkin_buffer_min", "60", "P2", "SPEC", "Arrival check-in queue buffer", "Affects arrival scheduling"),
    ("expected_participants_narrative", "2400", "P1", "SPEC", "Narrative figure", "Shown beside raw count (2836)"),
    ("external_budget_inr", "NULL", "P2", "SPEC", "External accommodation budget", "Director sets budget; engine flags unset"),
    ("external_property_accessibility", "UNVERIFIED", "P2", "SPEC", "External accessibility", "Must be verified before placement"),
    ("external_property_gender_suitability", "UNVERIFIED", "P2", "SPEC", "External gender suitability", "Must be verified before placement"),
    ("equipment_default_quantity", "1", "P1", "SPEC", "Default equipment requisition", "Inventory allocation"),
    ("shuttle_capacity_seats", "12", "P1", "SPEC", "Shuttle van capacity placeholder", "Transit capacity solver"),
    ("shuttle_vehicle_count", "3", "P1", "SPEC", "Fleet vehicle count placeholder", "Transit throughput"),
    ("shuttle_travel_min", "25", "P1", "SPEC", "Average transit duration", "Transit timing"),
    ("transport_hours", "06:00-22:00", "P1", "SPEC", "Operating window for shuttles", "Restricts shuttle runs"),
    ("accom_plan_c_weights", "cohesion 0.5, cost 0.3, travel 0.2", "P2", "SPEC", "Plan C balanced weights", "Accommodation solver optimization"),
    ("include_leaders_escorts_in_demand", "true", "P1", "SPEC", "Include leaders/escorts in room count", "Increases total bed demand"),
    ("count_unknown_accommodation_as_possible", "true", "P1", "SPEC", "Treat UNKNOWN accommodation as possible demand", "Reported separately from confirmed"),
    ("late_arrival_policy", "PENDING_DIRECTOR_DECISION", "P2", "SPEC", "Late arrival policy", "Requires Director approval"),
]

@register_seeder(name="seed_assumptions", order=10)
def seed_assumptions(session: Session) -> None:
    """Seed baseline operational assumptions into the database."""
    for key, val, owner, source, reason, impact in DEFAULT_ASSUMPTIONS:
        existing = session.exec(select(Assumption).where(Assumption.key == key)).first()
        if not existing:
            asm = Assumption(
                key=key,
                value=val,
                owner=owner,
                source=source,
                reason=reason,
                impact_if_changed=impact,
                updated_at=now()
            )
            session.add(asm)
