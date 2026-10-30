# OWNER: P1
import csv
import logging
from pathlib import Path

from sqlmodel import Session, select

from app.core.clock import now
from app.core.registry import register_participant_section, register_seeder
from app.models.inventory import (
    EntitlementPolicy,
    InventoryItem,
    InventoryLocation,
    InventoryMovement,
    MerchClaim,
)
from app.models.participants import Participant

logger = logging.getLogger("festos.seed.inventory")


def _get_loc_slug(loc_name: str) -> str:
    cleaned = loc_name.strip().lower().replace(" ", "_").replace("-", "_")
    return f"loc_{cleaned}"


CATEGORY_MAP = {
    "mic": "audio",
    "speaker": "audio",
    "mixer": "audio",
    "extension cord": "power",
    "barricade": "infrastructure",
    "table": "furniture",
    "chair": "furniture",
    "projector": "video",
    "generator": "power",
    "signage": "branding",
    "first-aid kit": "safety",
    "walkie-talkie": "comms",
    "tripod": "video",
    "camera": "video",
    "stage panel": "stage",
    "lighting rig": "lighting",
    "power strip": "power",
    "registration desk": "furniture",
}


@register_seeder("inventory", 40)
def seed_inventory(session: Session) -> None:
    """Order 40: Seeds inventory locations, logistics equipment, merchandise, and movements."""
    raw_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw"
    logistics_file = raw_dir / "inventory_logistics.csv"
    merch_file = raw_dir / "inventory_merch.csv"

    if not logistics_file.exists() or not merch_file.exists():
        logger.warning(f"Inventory seed files not found in {raw_dir}")
        return

    logger.info("Seeding inventory locations, logistics, and merchandise...")

    # 1. Base locations map
    known_locations = {
        "Registration Desk": ("loc_reg_desk", "DESK", "Main Entrance"),
        "Store Room A": ("loc_store_a", "STORAGE", "Admin Block"),
        "Main Stage": ("loc_main_stage", "VENUE", "Auditorium"),
        "Van 1": ("loc_van_1", "IN_TRANSIT", "Mobile Fleet"),
        "Sports Complex": ("loc_sports_complex", "VENUE", "Athletic Center"),
        "Merchandise Central Warehouse": ("loc_merch_warehouse", "STORAGE", "Student Center"),
        "Repair Center": ("loc_repair", "REPAIR", "Maintenance Workshop"),
    }

    for loc_name, (loc_id, loc_type, bldg) in known_locations.items():
        existing = session.get(InventoryLocation, loc_id)
        if not existing:
            loc = InventoryLocation(
                id=loc_id,
                name=loc_name,
                code=loc_id.upper(),
                building=bldg,
                location_type=loc_type,
            )
            session.add(loc)
    session.flush()

    # 2. Ingest inventory_logistics.csv
    with open(logistics_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["item_id"].strip()
            name = row["item"].strip()
            qty = int(row["quantity"].strip())
            loc_name = row["location"].strip()
            cond = row["condition"].strip().lower()

            loc_info = known_locations.get(loc_name)
            loc_id = loc_info[0] if loc_info else _get_loc_slug(loc_name)

            if not session.get(InventoryLocation, loc_id):
                new_loc = InventoryLocation(
                    id=loc_id,
                    name=loc_name,
                    code=loc_id.upper(),
                    building="CAMPUS",
                    location_type="VENUE",
                )
                session.add(new_loc)
                session.flush()

            itm_id = f"itm_{code.lower().replace('-', '_')}"
            existing_item = session.get(InventoryItem, itm_id)
            if not existing_item:
                cat = CATEGORY_MAP.get(name.lower(), "equipment")
                avail_qty = 0 if cond == "under repair" else qty

                item_obj = InventoryItem(
                    id=itm_id,
                    name=name,
                    code=code,
                    kind="equipment",
                    category=cat,
                    condition=cond,
                    quantity=qty,
                    reserved_quantity=0,
                    available_quantity=avail_qty,
                    location=loc_name,
                    location_id=loc_id,
                    low_stock_threshold=3,
                    status="AVAILABLE" if cond == "good" else cond.upper().replace(" ", "_"),
                    created_at=now(),
                    updated_at=now(),
                )
                session.add(item_obj)
                session.flush()

                # Movement 1: Initial RECEIVE
                mvt_recv = InventoryMovement(
                    item_id=itm_id,
                    from_location_id=None,
                    to_location_id=loc_id,
                    quantity=qty,
                    movement_type="RECEIVE",
                    reason="Initial raw pack ingestion",
                    moved_by="SYSTEM",
                    moved_at=now(),
                )
                session.add(mvt_recv)

                # Movement 2: If under repair, record SEND_REPAIR
                if cond == "under repair":
                    mvt_repair = InventoryMovement(
                        item_id=itm_id,
                        from_location_id=loc_id,
                        to_location_id="loc_repair",
                        quantity=qty,
                        movement_type="SEND_REPAIR",
                        reason=f"Item logged as under repair in {loc_name}",
                        moved_by="SYSTEM",
                        moved_at=now(),
                    )
                    session.add(mvt_repair)

    # 3. Ingest inventory_merch.csv
    merch_loc_id = "loc_merch_warehouse"
    with open(merch_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_name = row["item"].strip()
            raw_size = row["size"].strip()
            size = raw_size if raw_size != "NA" else None
            qty = int(row["quantity"].strip())
            res_qty = int(row["reserved_quantity"].strip())

            slug_name = item_name.lower().replace(" ", "_").replace("-", "_")
            slug_size = size.lower() if size else "na"
            itm_id = f"mch_{slug_name}_{slug_size}"

            existing_item = session.get(InventoryItem, itm_id)
            if not existing_item:
                avail_qty = max(0, qty - res_qty)
                item_obj = InventoryItem(
                    id=itm_id,
                    name=item_name,
                    code=itm_id.upper(),
                    kind="merch",
                    category="swag" if "t-shirt" not in item_name.lower() else "apparel",
                    size=size,
                    condition="good",
                    quantity=qty,
                    reserved_quantity=res_qty,
                    available_quantity=avail_qty,
                    location="Merchandise Central Warehouse",
                    location_id=merch_loc_id,
                    low_stock_threshold=20,
                    status="AVAILABLE",
                    created_at=now(),
                    updated_at=now(),
                )
                session.add(item_obj)
                session.flush()

                # Movement 1: RECEIVE
                mvt_recv = InventoryMovement(
                    item_id=itm_id,
                    from_location_id=None,
                    to_location_id=merch_loc_id,
                    quantity=qty,
                    movement_type="RECEIVE",
                    reason="Initial merchandise delivery",
                    moved_by="SYSTEM",
                    moved_at=now(),
                )
                session.add(mvt_recv)

                # Movement 2: RESERVE if reserved_quantity > 0
                if res_qty > 0:
                    mvt_res = InventoryMovement(
                        item_id=itm_id,
                        from_location_id=merch_loc_id,
                        to_location_id=merch_loc_id,
                        quantity=res_qty,
                        movement_type="RESERVE",
                        reason="Pre-festival reserved allocation",
                        moved_by="SYSTEM",
                        moved_at=now(),
                    )
                    session.add(mvt_res)

    # 4. Default Entitlement Policies
    policies = [
        ("T-shirt", True, 1, "1 T-shirt per confirmed canonical participant"),
        ("ID card", True, 1, "Official festival accreditation credential badge"),
        ("lanyard", True, 1, "Official Aarohan lanyard"),
        ("tote", True, 1, "Fest welcome kit tote bag"),
        ("special badge", True, 1, "Special access badge for designated roles"),
        ("winner medal", False, 0, "Award medals allocated strictly via event results"),
    ]

    for item_name, per_head, def_qty, desc in policies:
        pol_id = f"pol_{item_name.lower().replace(' ', '_').replace('-', '_')}"
        if not session.get(EntitlementPolicy, pol_id):
            pol = EntitlementPolicy(
                id=pol_id,
                item_name=item_name,
                per_head=per_head,
                default_quantity=def_qty,
                is_editable=True,
                description=desc,
                updated_at=now(),
            )
            session.add(pol)

    session.flush()
    logger.info("Inventory seeder completed successfully.")


@register_participant_section("merchandise")
def participant_merchandise_section(participant_id: str, session: Session) -> dict:
    """Dynamic participant 360 section showing merchandise entitlements and claims."""
    p = session.get(Participant, participant_id)
    canonical_id = (p.canonical_id or p.id) if p else participant_id

    claims = session.exec(
        select(MerchClaim).where(
            MerchClaim.canonical_participant_id == canonical_id,
            MerchClaim.status != "VOIDED",
        )
    ).all()
    claimed_names = {c.item_name.lower() for c in claims if c.item_name}

    entitlements = []
    per_head_names = ["T-shirt", "ID card", "lanyard", "tote"]

    for name in per_head_names:
        is_claimed = name.lower() in claimed_names
        claim_match = next((c for c in claims if c.item_name and c.item_name.lower() == name.lower()), None)
        entitlements.append({
            "item_name": name,
            "status": "ISSUED" if is_claimed else "PENDING",
            "size": p.tshirt_size if (name == "T-shirt" and p) else None,
            "claim_id": claim_match.id if claim_match else None,
            "claimed_at": claim_match.claimed_at.isoformat() if claim_match and claim_match.claimed_at else None,
        })

    return {
        "canonical_participant_id": canonical_id,
        "is_merged_record": (p is not None and p.canonical_id is not None),
        "tshirt_size": p.tshirt_size if p else "UNKNOWN",
        "size_flag": "NEEDS_SIZE_COLLECTION" if (not p or p.tshirt_size in (None, "", "UNKNOWN")) else None,
        "total_claimed": len(claims),
        "entitlements": entitlements,
    }
