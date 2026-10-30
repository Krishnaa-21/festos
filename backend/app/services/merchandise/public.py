# OWNER: P1
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.engines.inventory_ledger import PureInventoryLedger
from app.engines.merchandise import PureMerchandiseEngine
from app.models.inventory import (
    InventoryItem,
    InventoryMovement,
    MerchClaim,
)
from app.models.participants import Participant
from app.schemas.common import EntityRef, RiskItem


def summary(session: Session, now: datetime) -> Dict[str, Any]:
    """Returns merchandise KPI summary as of `now`."""
    items = session.exec(select(InventoryItem).where(InventoryItem.kind == "merch")).all()
    movements = [m.model_dump() for m in session.exec(select(InventoryMovement)).all()]

    total_on_hand = 0
    total_reserved = 0
    total_available = 0

    for it in items:
        item_mvts = [m for m in movements if m.get("item_id") == it.id]
        proj = PureInventoryLedger.calculate_projection(item_mvts, target_item_id=it.id)
        total_on_hand += proj.on_hand
        total_reserved += proj.reserved
        total_available += proj.available

    claims = session.exec(select(MerchClaim).where(MerchClaim.status != "VOIDED")).all()
    total_participants = session.exec(
        select(Participant).where(Participant.status.notin_(["INVALID", "MERGED"]))
    ).all()

    total_parts_count = len(total_participants)
    claim_rate = (len(claims) / total_parts_count * 100) if total_parts_count > 0 else 0.0

    return {
        "module": "merchandise",
        "status": "OPERATIONAL",
        "catalog_items_count": len(items),
        "total_on_hand": total_on_hand,
        "total_available": total_available,
        "total_reserved": total_reserved,
        "total_claims_issued": len(claims),
        "claim_rate_percent": round(claim_rate, 1),
    }


def risks(session: Session, now: datetime) -> List[RiskItem]:
    """Returns active risks evaluated as of `now`."""
    risk_list: List[RiskItem] = []

    # Calculate size demand vs stock
    tshirt_items = session.exec(
        select(InventoryItem).where(InventoryItem.kind == "merch", InventoryItem.name == "T-shirt")
    ).all()
    stock_by_size = {}
    for it in tshirt_items:
        mvts = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == it.id)).all()]
        proj = PureInventoryLedger.calculate_projection(mvts, target_item_id=it.id)
        stock_by_size[(it.size or "").upper()] = proj.available

    participants = [p.model_dump() for p in session.exec(select(Participant)).all()]
    demand_report = PureMerchandiseEngine.calculate_size_demand_and_shortages(participants, stock_by_size)

    # 1. Size shortage risks
    for sz, b in demand_report["breakdown"].items():
        if sz == "UNKNOWN":
            continue
        if b.get("shortage_alert"):
            risk_list.append(
                RiskItem(
                    id=f"risk_merch_shortage_{sz.lower()}",
                    module="merchandise",
                    kind="SIZE_SHORTAGE",
                    title=f"T-shirt size {sz} deficit: demand exceeds available stock by {b['shortage']} units",
                    severity=3,
                    hours_to_impact=12,
                    people_affected=b["shortage"],
                    uncertainty=0.1,
                    resource_criticality=3,
                    entity_refs=[EntityRef(type="merch_size", id=sz, label=f"Size {sz}")],
                    action={
                        "label": "Emergency Sizing Reorder / Buffer Swap",
                        "route": "/merchandise",
                        "api": "/api/v1/merchandise/catalog",
                    },
                    explanation=f"Based on confirmed attendee sizes, {b['demand']} attendees require {sz} but only {b['stock']} units remain available.",
                )
            )

    # 2. Unknown sizes risk
    unknown_count = demand_report["breakdown"].get("UNKNOWN", {}).get("count", 0)
    if unknown_count > 0:
        risk_list.append(
            RiskItem(
                id="risk_merch_unknown_sizes",
                module="merchandise",
                kind="DATA_GAP",
                title=f"{unknown_count} attendees have unrecorded T-shirt sizes",
                severity=2,
                hours_to_impact=24,
                people_affected=unknown_count,
                uncertainty=0.8,
                resource_criticality=2,
                entity_refs=[],
                action={
                    "label": "Prompt Desk Sizing On Check-in",
                    "route": "/merchandise",
                    "api": "/api/v1/merchandise/policy",
                },
                explanation="Attendees with missing shirt sizes create unpredictable stock draw at registration desks.",
            )
        )

    return risk_list


def dependents(session: Session, entity_type: str, entity_id: str) -> List[EntityRef]:
    """Returns downstream entities affected by entity_type:entity_id."""
    if entity_type == "inventory_item":
        claims = session.exec(
            select(MerchClaim).where(MerchClaim.item_id == entity_id, MerchClaim.status != "VOIDED")
        ).all()
        return [
            EntityRef(type="participant", id=c.canonical_participant_id, label=c.canonical_participant_id)
            for c in claims
        ]
    return []
