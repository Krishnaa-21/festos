# OWNER: P1
import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.change_service import ChangeRequest, execute_change
from app.core.config import settings
from app.engines.inventory_ledger import PureInventoryLedger
from app.engines.merchandise import PureMerchandiseEngine
from app.models.inventory import (
    EntitlementPolicy,
    InventoryItem,
    InventoryMovement,
    MerchClaim,
)
from app.models.participants import Participant
from app.schemas.common import Actor

logger = logging.getLogger("festos.merchandise.service")


def get_catalog(session: Session) -> Dict[str, Any]:
    """Returns merchandise items with current stock buckets."""
    items = session.exec(select(InventoryItem).where(InventoryItem.kind == "merch")).all()
    results = []
    for it in items:
        mvts = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == it.id)).all()]
        proj = PureInventoryLedger.calculate_projection(mvts, target_item_id=it.id)
        results.append({
            "id": it.id,
            "name": it.name,
            "size": it.size or "NA",
            "category": it.category,
            "on_hand": proj.on_hand,
            "reserved": proj.reserved,
            "available": proj.available,
            "is_per_head": it.name.lower() in PureMerchandiseEngine.PER_HEAD_ITEMS,
        })
    return {"items": results, "total": len(results)}


def get_policy_and_demand(session: Session) -> Dict[str, Any]:
    """Returns entitlement policy and size-wise demand vs stock analysis."""
    policies = session.exec(select(EntitlementPolicy)).all()
    rules = [
        {
            "item": p.item_name,
            "entitlement": f"{p.default_quantity} per canonical participant" if p.per_head else "Event result allocation only",
            "per_head": p.per_head,
            "description": p.description,
        }
        for p in policies
    ]

    # Compute t-shirt stock by size
    tshirt_items = session.exec(
        select(InventoryItem).where(InventoryItem.kind == "merch", InventoryItem.name == "T-shirt")
    ).all()

    stock_by_size = {}
    for it in tshirt_items:
        mvts = [m.model_dump() for m in session.exec(select(InventoryMovement).where(InventoryMovement.item_id == it.id)).all()]
        proj = PureInventoryLedger.calculate_projection(mvts, target_item_id=it.id)
        sz = (it.size or "").upper()
        stock_by_size[sz] = proj.available

    participants = [p.model_dump() for p in session.exec(select(Participant)).all()]
    demand_report = PureMerchandiseEngine.calculate_size_demand_and_shortages(participants, stock_by_size)

    return {
        "policy_name": "Standard Fest Entitlement Baseline",
        "is_editable": True,
        "rules": rules,
        "size_breakdown": demand_report["breakdown"],
        "policy_assumption": demand_report["policy_assumption"],
        "is_policy_dependent": True,
    }


def get_qr(session: Session, participant_id: str) -> Optional[Dict[str, Any]]:
    """Generates signed HMAC QR token and SVG for a participant."""
    p = session.get(Participant, participant_id)
    if not p:
        return None

    canonical_id = p.canonical_id or p.id
    secret = settings.QR_SECRET
    token = PureMerchandiseEngine.generate_token(canonical_id, secret)
    svg = PureMerchandiseEngine.generate_svg(token, title=f"Aarohan Swag: {p.name[:18]}")

    claims = [c.model_dump() for c in session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == canonical_id)).all()]
    catalog = [it.model_dump() for it in session.exec(select(InventoryItem).where(InventoryItem.kind == "merch")).all()]
    entitlements = PureMerchandiseEngine.evaluate_entitlements(canonical_id, p.model_dump(), claims, catalog)

    return {
        "participant_id": participant_id,
        "canonical_participant_id": canonical_id,
        "name": p.name,
        "token": token,
        "svg": svg,
        "entitlements": entitlements,
    }


def scan_qr(
    session: Session,
    token: str,
    counter_id: str = "DESK_CENTRAL",
    auto_issue_items: Optional[List[str]] = None,
    actor: Optional[Actor] = None,
) -> Dict[str, Any]:
    """Validates HMAC QR token, looks up canonical participant, and returns entitlement status."""
    secret = settings.QR_SECRET
    is_valid, pid = PureMerchandiseEngine.verify_token(token, secret)
    if not is_valid or not pid:
        return {"valid": False, "message": "Invalid or forged QR token signature"}

    p = session.get(Participant, pid)
    if not p:
        return {"valid": False, "message": f"Participant {pid} not found in database"}

    canonical_id = p.canonical_id or p.id
    can_p = session.get(Participant, canonical_id) or p

    catalog = [it.model_dump() for it in session.exec(select(InventoryItem).where(InventoryItem.kind == "merch")).all()]

    issued_results = []
    if auto_issue_items and actor:
        for itm_id in auto_issue_items:
            req = ChangeRequest(
                action="merchandise.issue",
                entity_type="merch_claim",
                entity_id=f"clm_{canonical_id}_{itm_id}",
                payload={
                    "participant_id": canonical_id,
                    "item_id": itm_id,
                    "counter_id": counter_id,
                },
                actor=actor,
            )
            res = execute_change(req, session)
            issued_results.append({
                "item_id": itm_id,
                "status": res.status,
                "violations": [v.model_dump() for v in res.violations],
            })

    # Reload claims
    updated_claims = [c.model_dump() for c in session.exec(select(MerchClaim).where(MerchClaim.canonical_participant_id == canonical_id)).all()]
    updated_entitlements = PureMerchandiseEngine.evaluate_entitlements(canonical_id, can_p.model_dump(), updated_claims, catalog)

    return {
        "valid": True,
        "canonical_participant_id": canonical_id,
        "name": can_p.name,
        "contingent_id": can_p.contingent_id or "UNKNOWN",
        "tshirt_size": can_p.tshirt_size or "UNKNOWN",
        "entitlements": updated_entitlements,
        "issued_results": issued_results,
    }


def sync_offline_batch(
    session: Session,
    operations: List[Dict[str, Any]],
    actor: Actor,
) -> Dict[str, Any]:
    """Applies offline scan/issue operations idempotently by client_op_id."""
    synced = 0
    failed = 0
    results = []

    for op in operations:
        client_op_id = op.get("client_op_id")
        pid = op.get("participant_id")
        itm_id = op.get("item_id")
        counter_id = op.get("counter_id", "OFFLINE_DESK")

        # Check if already issued
        p = session.get(Participant, pid)
        canonical_id = (p.canonical_id or p.id) if p else pid

        existing = session.exec(
            select(MerchClaim).where(
                MerchClaim.canonical_participant_id == canonical_id,
                MerchClaim.item_id == itm_id,
                MerchClaim.status != "VOIDED",
            )
        ).first()

        if existing:
            results.append({
                "client_op_id": client_op_id,
                "status": "ALREADY_APPLIED",
                "claim_id": existing.id,
            })
            synced += 1
            continue

        req = ChangeRequest(
            action="merchandise.issue",
            entity_type="merch_claim",
            entity_id=f"clm_{client_op_id}",
            payload={
                "participant_id": canonical_id,
                "item_id": itm_id,
                "counter_id": counter_id,
            },
            reason=f"Offline sync operation {client_op_id}",
            actor=actor,
        )
        res = execute_change(req, session)
        if res.status == "APPLIED":
            synced += 1
            claim_id = res.data.get("claim_id") if res.data else None
            results.append({
                "client_op_id": client_op_id,
                "status": "APPLIED",
                "claim_id": claim_id,
            })
        else:
            failed += 1
            results.append({
                "client_op_id": client_op_id,
                "status": res.status,
                "violations": [v.model_dump() for v in res.violations],
            })

    return {
        "synced_count": synced,
        "failed_count": failed,
        "results": results,
    }
