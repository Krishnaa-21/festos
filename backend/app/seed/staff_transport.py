# OWNER: P1
"""Seeder for Staff profiles, shifts, external properties, transport fleet, shuttle runs, and minor guardian approvals.

Order: 60 (after assumptions: 10, participants: 15, users: 20, events: 30, inventory: 40).
"""
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from app.core.config import settings
from app.core.registry import register_seeder
from app.models.accommodation import ExternalProperty
from app.models.participants import Participant
from app.models.staff import Shift, Staff
from app.models.transport import (
    GuardianApproval,
    Route,
    ShuttleRun,
    Transport,
)

logger = logging.getLogger("festos.seed.staff_transport")


def _find_data_file(filename: str) -> Optional[Path]:
    """Resolves data file path from settings.DATA_DIR or common repo locations."""
    candidates = [
        Path(settings.DATA_DIR) / filename,
        Path("data/raw") / filename,
        Path("../data/raw") / filename,
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


ROLE_SKILLS_MAP = {
    "Registration Desk": ["registration", "checkin", "crowd_management", "first_aid"],
    "Hospitality": ["hospitality", "escort", "guest_management", "communication"],
    "Events Team": ["stage_ops", "crowd_control", "event_coordination", "audio_visual"],
    "Logistics Head": ["logistics", "inventory", "transport", "dispatch"],
    "Merchandise Desk": ["merchandise", "inventory", "cash_handling"],
    "Food Coordinator": ["catering", "dietary", "queue_management"],
    "Volunteer": ["volunteer", "general_support", "crowd_control", "runner"],
    "Festival Director": ["leadership", "crisis_management", "coordination"],
}


@register_seeder(name="seed_staff_transport", order=60)
def seed_staff_transport(session: Session) -> None:
    """Seeds staff profiles from core_team.csv, default shifts, external stays, vehicles, and minor approvals."""
    logger.info("Starting staff and transport seeder (order 60)...")

    # ------------------------------------------------------------------
    # 1. Seed Core Team Staff (48 members)
    # ------------------------------------------------------------------
    staff_file = _find_data_file("core_team.csv")
    staff_records = []
    if staff_file:
        with open(staff_file, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mid = row.get("member_id", "").strip()
                name = row.get("name", "").strip()
                role = row.get("role", "Volunteer").strip()
                shift = row.get("shift", "").strip()
                phone = row.get("phone", "").strip()

                if not mid:
                    continue

                existing = session.get(Staff, mid)
                skills = ROLE_SKILLS_MAP.get(role, ["volunteer", "general_support"])
                if not existing:
                    stf = Staff(
                        id=mid,
                        name=name,
                        role=role,
                        shift=shift,
                        phone=phone,
                        email=f"{mid.lower()}@aarohan2026.festos.org",
                        skills=skills,
                        status="ACTIVE",
                        is_participant=False,
                    )
                    session.add(stf)
                    staff_records.append(stf)
                else:
                    existing.name = name
                    existing.role = role
                    existing.shift = shift
                    existing.phone = phone
                    existing.skills = skills
                    session.add(existing)
                    staff_records.append(existing)

        session.flush()
        logger.info(f"Seeded {len(staff_records)} core team staff profiles.")

    # ------------------------------------------------------------------
    # 2. Seed Baseline Shifts across Festival Dates
    # ------------------------------------------------------------------
    # Festival dates: 2026-10-30, 2026-10-31, 2026-11-01
    fest_dates = ["2026-10-30", "2026-10-31", "2026-11-01"]
    existing_shifts = session.exec(select(Shift)).first()
    if not existing_shifts and staff_records:
        created_shifts = 0
        for d_str in fest_dates:
            day_dt = datetime.fromisoformat(f"{d_str}T00:00:00+00:00")
            for stf in staff_records:
                shift_band = stf.shift or "06:00-14:00"
                parts = shift_band.split("-")
                if len(parts) != 2:
                    continue
                start_h, start_m = [int(x) for x in parts[0].split(":")]
                end_h, end_m = [int(x) for x in parts[1].split(":")]

                st_time = day_dt.replace(hour=start_h, minute=start_m)
                if end_h < start_h:  # overnight shift: e.g. 22:00 to 06:00
                    et_time = (day_dt + timedelta(days=1)).replace(hour=end_h, minute=end_m)
                else:
                    et_time = day_dt.replace(hour=end_h, minute=end_m)

                shf = Shift(
                    staff_id=stf.id,
                    role_required=stf.role,
                    location="Campus Festival Grounds",
                    venue_id="V01",
                    start_at=st_time,
                    end_at=et_time,
                    handover_notes="Standard scheduled operational shift",
                    status="SCHEDULED",
                )
                session.add(shf)
                created_shifts += 1

        session.flush()
        logger.info(f"Seeded {created_shifts} scheduled shifts across festival days.")

    # ------------------------------------------------------------------
    # 3. Seed External Properties from external_stays.csv
    # ------------------------------------------------------------------
    ext_file = _find_data_file("external_stays.csv")
    if ext_file:
        with open(ext_file, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("property_id", "").strip()
                pname = row.get("property_name", "").strip()
                beds = int(row.get("beds", 0) or 0)
                cost = float(row.get("cost_per_bed_per_night", 0) or 0)
                dist = float(row.get("distance_km", 0) or 0)
                trans = row.get("transport_availability", "yes").strip()

                if not pid:
                    continue

                prop = session.get(ExternalProperty, pid)
                if not prop:
                    prop = ExternalProperty(
                        id=pid,
                        name=pname,
                        beds=beds,
                        cost_per_bed_night=cost,
                        distance_km=dist,
                        transport_availability=trans,
                        transport_limited=(trans.lower() == "limited"),
                        status="ACTIVE",
                    )
                    session.add(prop)
                else:
                    prop.name = pname
                    prop.beds = beds
                    prop.cost_per_bed_night = cost
                    prop.distance_km = dist
                    prop.transport_availability = trans
                    prop.transport_limited = (trans.lower() == "limited")
                    session.add(prop)
        session.flush()

    # ------------------------------------------------------------------
    # 4. Seed Shuttle Fleet and Default Routes
    # ------------------------------------------------------------------
    fleet_data = [
        ("trn_01", "MP-09-AB-1234", "SHUTTLE_MINIBUS", 15, "Ramesh Kumar", "+91-9826011111"),
        ("trn_02", "MP-09-CD-5678", "SHUTTLE_MINIBUS", 15, "Suresh Singh", "+91-9826022222"),
        ("trn_03", "MP-09-EF-9012", "SHUTTLE_MINIBUS", 15, "Mahesh Verma", "+91-9826033333"),
        ("trn_04", "MP-09-GH-3456", "SHUTTLE_MINIBUS", 15, "Dinesh Yadav", "+91-9826044444"),
    ]
    for tid, vnum, vtype, cap, dname, dphone in fleet_data:
        existing_t = session.get(Transport, tid)
        if not existing_t:
            session.add(Transport(
                id=tid,
                vehicle_number=vnum,
                vehicle_type=vtype,
                capacity=cap,
                driver_name=dname,
                driver_phone=dphone,
                status="ACTIVE",
            ))

    # Routes to external properties
    properties = session.exec(select(ExternalProperty)).all()
    for prop in properties:
        r_id = f"rot_{prop.id.lower()}"
        existing_r = session.get(Route, r_id)
        if not existing_r:
            session.add(Route(
                id=r_id,
                name=f"Campus to {prop.name}",
                origin="CAMPUS",
                destination=prop.name,
                property_id=prop.id,
                travel_time_min=25,
                distance_km=prop.distance_km,
            ))

    session.flush()

    # Seed baseline scheduled shuttle runs if empty
    existing_runs = session.exec(select(ShuttleRun)).first()
    if not existing_runs and properties:
        for idx, prop in enumerate(properties):
            v_id = f"trn_0{(idx % 4) + 1}"
            run_times = [
                ("2026-10-31T00:15:00+00:00", "2026-10-31T00:45:00+00:00"),
                ("2026-10-31T07:30:00+00:00", "2026-10-31T08:00:00+00:00"),
                ("2026-10-31T13:30:00+00:00", "2026-10-31T14:00:00+00:00"),
                ("2026-10-31T23:30:00+00:00", "2026-10-31T23:55:00+00:00"),
            ]
            for dep_iso, arr_iso in run_times:
                srun = ShuttleRun(
                    route_name=f"Campus to {prop.name}",
                    vehicle_id=v_id,
                    property_id=prop.id,
                    departure_at=datetime.fromisoformat(dep_iso),
                    arrival_at=datetime.fromisoformat(arr_iso),
                    capacity=15,
                    passengers_assigned=12,
                    escort_staff_id="ST02",
                    status="SCHEDULED",
                )
                session.add(srun)
        session.flush()

    # ------------------------------------------------------------------
    # 5. Seed Guardian Approvals for Minors in External Stays (~71 minors)
    # ------------------------------------------------------------------
    existing_gdn = session.exec(select(GuardianApproval)).first()
    if not existing_gdn:
        all_participants = session.exec(select(Participant)).all()
        # Filter minors (<18 years old)
        minors = [p for p in all_participants if p.age is not None and p.age < 18]
        # Target baseline: 71 minors in external stays
        target_minors = minors[:71] if len(minors) >= 71 else minors
        prop_ids = [p.id for p in properties] or ["EXT01", "EXT02", "EXT03", "EXT04", "EXT05", "EXT06"]

        for idx, m in enumerate(target_minors):
            prop_choice = prop_ids[idx % len(prop_ids)]
            gdn = GuardianApproval(
                id=f"gdn_{idx+1:03d}",
                participant_id=m.id,
                contingent_id=m.contingent_id,
                property_id=prop_choice,
                stay_duration_days=3,
                escort_staff_id=f"ST{(idx % 12) + 1:02d}",
                approval_status="PENDING",
                responsible_coordinator_id="ST02",
                notes="Parental consent and escort declaration pending field verification",
            )
            session.add(gdn)

        session.flush()
        logger.info(f"Seeded {len(target_minors)} minor guardian approval records.")

    session.flush()
    logger.info("Staff and transport seeder completed successfully.")
