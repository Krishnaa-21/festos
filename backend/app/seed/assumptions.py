# OWNER: P1
from sqlmodel import Session, select

from app.core.clock import now
from app.core.registry import register_seeder
from app.models.change import Assumption

DEFAULT_ASSUMPTIONS = [
    # Reference Pack Assumptions (data/reference/assumptions.csv)
    ("cleaning_hours_between_occupants", "3", "P2", "SPEC", "Hours needed between occupants for hostel turnaround", "Cleaning buffer"),
    ("cleaning_buffer_minutes", "180", "P2", "SPEC", "One configurable cleaning buffer assumption", "Recalculates turnaround"),
    ("late_night_window", "22:00-06:00 arrival or departure needs transport=yes", "P1", "SPEC", "Night transit restriction", "Requires transport=yes"),
    ("late_night_start", "22:00", "P1", "SPEC", "Noise boundary start", "Limits late night events"),
    ("late_night_end", "06:00", "P1", "SPEC", "Noise boundary end", "Restricts early morning scheduling"),
    ("minor_age_below", "18", "P1", "SPEC", "Age threshold for minors requiring guardian approval", "Safety restriction"),
    ("minor_age_threshold", "18", "P1", "SPEC", "Minor participant threshold", "Forces guardian / escort checks"),
    ("setup_teardown_min_each_side", "15", "P1", "SPEC", "Setup and teardown buffer on each side of event session", "Adds turnaround window"),
    ("setup_buffer_min", "15", "P1", "SPEC", "Pre-event setup", "Adds room prep time"),
    ("teardown_buffer_min", "15", "P1", "SPEC", "Post-event teardown", "Adds teardown window"),
    ("travel_min_between_venues", "15", "P1", "SPEC", "Travel time estimate between campus venues", "Flags transit conflicts"),
    ("venue_travel_min", "15", "P1", "SPEC", "Default venue travel time", "Flags transit conflicts"),
    ("result_buffer_min_between_rounds", "60", "P1", "SPEC", "Judge evaluation and result compilation buffer", "Controls subsequent round start"),
    ("round_result_buffer_min", "60", "P1", "SPEC", "Judges buffer", "Controls subsequent round start"),
    ("semi_fraction_of_prelims", "0.5", "P1", "SPEC", "Semifinal advancement proportion", "Affects stage counts"),
    ("semifinal_ratio", "0.5", "P1", "SPEC", "Semifinal advancement proportion", "Affects stage counts"),
    ("finalists_fraction_min8", "0.1", "P1", "SPEC", "Finalist advancement proportion with min 8", "Affects stage counts"),
    ("finalist_ratio", "0.10", "P1", "SPEC", "Finalist advancement proportion", "Affects stage counts"),
    ("finalist_min", "8", "P1", "SPEC", "Minimum finalists", "Affects stage counts"),
    ("checkin_buffer_min_before_first_event", "60", "P2", "SPEC", "Arrival check-in queue buffer before first event", "Affects arrival scheduling"),
    ("checkin_buffer_min", "60", "P2", "SPEC", "Arrival check-in queue buffer", "Affects arrival scheduling"),
    ("venue_capacity_means", "max simultaneous competitors in one heat (conservative)", "P1", "SPEC", "Capacity interpretation", "Heat sizing"),
    ("accessibility_mapping", "Wheelchair->accessible=yes room (hard); Ground floor->floor 0 (hard); Near washroom / Visual assistance -> no room data exists: kept visible, flagged for manual confirmation", "P2", "SPEC", "Accessibility constraint mapping", "Room allocation"),
    ("gender_classes", "Female->girls blocks, Male->boys blocks, Non-binary/Prefer not to say/blank -> never auto-placed in a gendered block", "P2", "SPEC", "Gender segregation rule", "Prevents illegal placement"),
    ("external_property_data", "no accessibility or gender-segregation info exists: unverified, so hard-need people are NOT placed there", "P2", "SPEC", "External property safety gate", "Requires verification"),
    ("budget", "not supplied in pack: cost is shown per plan, override control required once a ceiling is set", "P2", "SPEC", "Budget ceiling", "Director sets budget; engine flags unset"),
    ("venue_features", "venues.csv has no feature tags: mapping in VENUE_OK is an assumption, editable", "P1", "SPEC", "Venue capability mapping", "Schedule feasibility"),
    ("events_without_times", "events.csv has no start time/venue: schedule is generated, not imported", "P1", "SPEC", "Generated schedule flag", "Labels schedules ASSUMED"),
    ("equipment_units_per_session", "1 per named item unless the text says 2 (e.g. 2 mics, 2 extension cords)", "P1", "SPEC", "Default equipment requisition", "Inventory allocation"),
    ("equipment_default_quantity", "1", "P1", "SPEC", "Default equipment requisition", "Inventory allocation"),
    ("prelim_waves", "E=30 Oct, M=31 Oct (main), L=1 Nov morning for people not on site earlier; L entrants join finals as wildcards (director decision, fairness risk)", "P1", "SPEC", "Prelim schedule wave allocation", "Wildcard finals risk"),
    ("expected_participants_narrative", "2400", "P1", "SPEC", "Narrative figure", "Shown beside raw count (2836)"),
    ("external_budget_inr", "NULL", "P2", "SPEC", "External accommodation budget", "Director sets budget; engine flags unset"),
    ("external_property_accessibility", "UNVERIFIED", "P2", "SPEC", "External accessibility", "Must be verified before placement"),
    ("external_property_gender_suitability", "UNVERIFIED", "P2", "SPEC", "External gender suitability", "Must be verified before placement"),
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
