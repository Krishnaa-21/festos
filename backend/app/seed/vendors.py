# OWNER: P2
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from sqlmodel import Session, select

from app.core.clock import now
from app.core.registry import register_seeder
from app.models.vendors import EmergencySpend, MealSlot, Vendor, VendorAssignment, VendorSettlement

logger = logging.getLogger("festos.seed.vendors")

BASE_RATES: Dict[str, float] = {
    "VND01": 180.0,
    "VND02": 190.0,
    "VND03": 195.0,
    "VND04": 185.0,
    "VND05": 175.0,
    "VND06": 180.0,
    "VND07": 210.0,
    "VND08": 160.0,
    "VND09": 190.0,
    "VND10": 230.0,
    "VND11": 220.0,
    "VND12": 200.0,
    "VND13": 170.0,
    "VND14": 165.0,
}

FESTIVAL_DATES = ["2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"]

SLOT_DEFS = [
    {"name": "BREAKFAST", "start": "07:30", "end": "10:00", "type": "REGULAR"},
    {"name": "LUNCH", "start": "12:00", "end": "15:00", "type": "MAIN"},
    {"name": "SNACKS", "start": "16:30", "end": "18:00", "type": "LIGHT"},
    {"name": "DINNER", "start": "19:30", "end": "22:30", "type": "MAIN"},
    {"name": "LATE_NIGHT", "start": "23:00", "end": "02:00", "type": "LATE"},
]


def seed_vendors_data(session: Session) -> None:
    """Seed all 14 food vendors, meal slots, initial assignments, and commercial settlements (Order 50)."""
    csv_path = Path("data/raw/vendors.csv")
    if not csv_path.exists():
        logger.warning(f"vendors.csv not found at {csv_path}, skipping seed.")
        return

    # 1. Seed Vendors
    existing_vendors = {v.id for v in session.exec(select(Vendor)).all()}
    vendors_to_add: List[Vendor] = []

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        idx = 1
        for row in reader:
            vid = row["vendor_id"].strip()
            if vid in existing_vendors:
                continue

            cap = int(row["capacity"].strip()) if row.get("capacity") else 200
            rate = BASE_RATES.get(vid, 180.0)

            v = Vendor(
                id=vid,
                name=row["vendor_name"].strip(),
                menu_description=row.get("menu", "").strip(),
                dietary_options=row.get("dietary_options", "").strip(),
                hygiene_certificate_expiry=row.get("hygiene_certificate_expiry", "").strip(),
                hours=row.get("hours", "07:00-23:00").strip(),
                capacity=cap,
                payment_terms=row.get("payment_terms", "minimum guarantee").strip(),
                base_rate_per_meal_inr=rate,
                contact_phone=f"+91-9876543{idx:03d}",
                status="ACTIVE",
                created_at=now(),
                updated_at=now(),
            )
            vendors_to_add.append(v)
            idx += 1

    if vendors_to_add:
        session.add_all(vendors_to_add)
        session.commit()
        logger.info(f"Seeded {len(vendors_to_add)} vendors from vendors.csv.")

    # 2. Seed Meal Slots for all 4 festival days
    existing_slots = {f"{s.date}_{s.name}": s for s in session.exec(select(MealSlot)).all()}
    slots_to_add: List[MealSlot] = []

    for d in FESTIVAL_DATES:
        for sdef in SLOT_DEFS:
            key = f"{d}_{sdef['name']}"
            if key not in existing_slots:
                slot = MealSlot(
                    id=f"msl_{d.replace('-', '')}_{sdef['name'].lower()}",
                    name=sdef["name"],
                    date=d,
                    start_time=sdef["start"],
                    end_time=sdef["end"],
                    meal_type=sdef["type"],
                )
                slots_to_add.append(slot)

    if slots_to_add:
        session.add_all(slots_to_add)
        session.commit()
        logger.info(f"Seeded {len(slots_to_add)} festival meal slots.")

    all_slots = session.exec(select(MealSlot)).all()
    all_vendors = session.exec(select(Vendor)).all()

    # 3. Seed Vendor Assignments to Venues & Meal Slots
    existing_assignments = session.exec(select(VendorAssignment)).all()
    if not existing_assignments and all_vendors and all_slots:
        assignments_to_add: List[VendorAssignment] = []
        venues_pool = ["V04", "V05", "V06", "V01", "V08"]
        loc_names = ["Amphitheatre Food Court", "Quadrangle Eatery", "Hostel Dining Hall", "Main Stage Plaza", "Sports Complex Stalls"]

        # Assign vendors across slots
        for s in all_slots:
            # Main meals get broader vendor coverage
            if s.name in ["LUNCH", "DINNER"]:
                assigned_vends = all_vendors[:10]  # First 10 vendors
            elif s.name == "BREAKFAST":
                assigned_vends = [v for v in all_vendors if v.id in ["VND01", "VND02", "VND04", "VND07", "VND14", "VND03"]]
            elif s.name == "SNACKS":
                assigned_vends = [v for v in all_vendors if v.id in ["VND03", "VND05", "VND06", "VND08", "VND12", "VND13"]]
            else:  # LATE_NIGHT
                assigned_vends = [v for v in all_vendors if v.id in ["VND03", "VND06", "VND07", "VND10"]]

            for i, v in enumerate(assigned_vends):
                v_idx = i % len(venues_pool)
                vna = VendorAssignment(
                    id=f"vna_{s.id}_{v.id}",
                    vendor_id=v.id,
                    meal_slot_id=s.id,
                    venue_id=venues_pool[v_idx],
                    location_name=loc_names[v_idx],
                    date=s.date,
                    allocated_capacity=v.capacity or 200,
                    rate_per_meal_inr=v.base_rate_per_meal_inr,
                    status="SCHEDULED",
                )
                assignments_to_add.append(vna)

        session.add_all(assignments_to_add)
        session.commit()
        logger.info(f"Seeded {len(assignments_to_add)} vendor assignments across meal slots.")

    # 4. Seed Vendor Settlements
    existing_settlements = {s.vendor_id for s in session.exec(select(VendorSettlement)).all()}
    settlements_to_add: List[VendorSettlement] = []

    for v in all_vendors:
        if v.id in existing_settlements:
            continue

        cap = v.capacity or 200
        # Contract total = 4 meals * 3 days * capacity * rate / 2 approx
        contract_total = round(cap * v.base_rate_per_meal_inr * 4.0, 2)

        terms = v.payment_terms.lower()
        if "50%" in terms or "advance" in terms:
            advance = round(contract_total * 0.50, 2)
            stat = "PARTIALLY_PAID"
        elif "minimum" in terms:
            advance = round(contract_total * 0.35, 2)
            stat = "PARTIALLY_PAID"
        else:
            advance = 0.0
            stat = "PENDING_VERIFICATION"

        balance = round(contract_total - advance, 2)

        # VND02 has dispute case per spec
        disp_reason = None
        disp_amt = 0.0
        disp_user = None
        disp_at = None
        if v.id == "VND02":
            stat = "DISPUTED"
            disp_reason = "Billed for 120 unauthorized extra lunch packs during Oct 31 storm delay without voucher."
            disp_amt = 18500.0
            disp_user = "Finance Manager"
            disp_at = datetime(2026, 10, 31, 15, 0, tzinfo=timezone.utc)

        stl = VendorSettlement(
            id=f"stl_{v.id.lower()}",
            vendor_id=v.id,
            invoice_number=f"INV-EPINOIA-2026-{v.id}",
            contract_amount_inr=contract_total,
            advance_paid_inr=advance,
            balance_due_inr=balance,
            payment_terms=v.payment_terms,
            due_date="2026-11-05" if v.id != "VND02" else "2026-11-02",
            status=stat,
            dispute_reason=disp_reason,
            disputed_amount_inr=disp_amt,
            dispute_opened_by=disp_user,
            dispute_opened_at=disp_at,
            created_at=now(),
            updated_at=now(),
        )
        settlements_to_add.append(stl)

    if settlements_to_add:
        session.add_all(settlements_to_add)
        session.commit()
        logger.info(f"Seeded {len(settlements_to_add)} vendor settlement accounts.")

    # 5. Seed Emergency Spend Baseline
    existing_spends = session.exec(select(EmergencySpend)).all()
    if not existing_spends:
        spends_to_add = [
            EmergencySpend(
                id="emg_01",
                description="Backup Diesel Generator for Main Stage sound rig",
                amount_inr=35000.0,
                category="VENDOR_BACKUP",
                reason="Grid transformer voltage fluctuation threat during Inauguration",
                approved_by="Festival Director",
                approved_at=datetime(2026, 10, 31, 6, 15, tzinfo=timezone.utc),
                audit_link="aud_emg_991",
                status="APPROVED",
                created_at=now(),
            ),
            EmergencySpend(
                id="emg_02",
                description="Heavy-duty waterproof tarpaulins for Amphitheatre dining area",
                amount_inr=25000.0,
                category="VENDOR_BACKUP",
                reason="Sudden weather bulletin predicting rain showers",
                approved_by="Festival Director",
                approved_at=datetime(2026, 10, 31, 12, 30, tzinfo=timezone.utc),
                audit_link="aud_emg_992",
                status="APPROVED",
                created_at=now(),
            ),
        ]
        session.add_all(spends_to_add)
        session.commit()
        logger.info(f"Seeded {len(spends_to_add)} baseline emergency expenditures.")


@register_seeder("vendors", 50)
def seed_vendors(session: Session) -> None:
    seed_vendors_data(session)
