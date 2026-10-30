# OWNER: P1
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import app.services.logistics.handlers  # noqa: F401
from app.core.change_service import ChangeRequest, execute_change
from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.logistics import service as logistics_service
from app.services.logistics.public import equipment_gap_csv, inventory_plan_csv
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/logistics", tags=["logistics"])


class RecordMovementBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class CreateTransferBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


class StocktakeAdjustBody(BaseModel):
    expected_version: Optional[int] = None
    reason: Optional[str] = None
    dry_run: bool = False
    payload: Dict[str, Any]


@router.get("/items", response_model=Envelope[Dict[str, Any]])
def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List inventory items with projected stock buckets."""
    data = logistics_service.list_items(
        session=session,
        page=page,
        page_size=page_size,
        kind=kind,
        q=q,
        location_id=location_id,
    )
    return Envelope(data=data)


@router.get("/items/{id}", response_model=Envelope[Dict[str, Any]])
def get_item(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Get single inventory item profile with location breakdown."""
    data = logistics_service.get_item(session, id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Inventory item {id} not found")
    return Envelope(data=data)


@router.get("/locations", response_model=Envelope[List[Dict[str, Any]]])
def list_locations(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List inventory locations."""
    data = logistics_service.list_locations(session)
    return Envelope(data=data)


@router.get("/movements", response_model=Envelope[Dict[str, Any]])
def list_movements(
    item_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List inventory movements from the immutable ledger."""
    data = logistics_service.list_movements(
        session=session,
        item_id=item_id,
        location_id=location_id,
        page=page,
        page_size=page_size,
    )
    return Envelope(data=data)


@router.post("/movements", response_model=Envelope[Dict[str, Any]])
def record_movement(
    body: RecordMovementBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Record an inventory movement in the ledger via ChangeService."""
    req = ChangeRequest(
        action="logistics.record_movement",
        entity_type="inventory_movement",
        entity_id=f"mvt_req_{body.payload.get('item_id')}",
        payload=body.payload,
        reason=body.reason,
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=422,
            detail=[v.model_dump() for v in res.violations],
        )
    return Envelope(data=res.model_dump())


@router.get("/transfers", response_model=Envelope[List[Dict[str, Any]]])
def list_transfers(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List transfers."""
    data = logistics_service.list_transfers(session)
    return Envelope(data=data)


@router.post("/transfers", response_model=Envelope[Dict[str, Any]])
def create_transfer(
    body: CreateTransferBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Initiate an equipment transfer between locations."""
    req = ChangeRequest(
        action="logistics.create_transfer",
        entity_type="inventory_transfer",
        entity_id=f"trf_{body.payload.get('item_id')}",
        payload=body.payload,
        reason=body.reason,
        actor=actor,
        expected_version=body.expected_version,
        dry_run=body.dry_run,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(
            status_code=422,
            detail=[v.model_dump() for v in res.violations],
        )
    return Envelope(data=res.model_dump())


@router.post("/transfers/{id}/complete", response_model=Envelope[Dict[str, Any]])
def complete_transfer(
    id: str,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Complete an in-transit transfer."""
    req = ChangeRequest(
        action="logistics.complete_transfer",
        entity_type="inventory_transfer",
        entity_id=id,
        payload={},
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())


@router.get("/equipment/find", response_model=Envelope[Dict[str, Any]])
def find_equipment(
    item_name: str = Query(...),
    venue_id: str = Query(...),
    start_at: str = Query(...),
    end_at: str = Query(...),
    quantity_needed: int = Query(1, ge=1),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Searches equipment units for a venue session window and evaluates transfer feasibility."""
    try:
        dt_start = datetime.fromisoformat(start_at.replace(" ", "+"))
        dt_end = datetime.fromisoformat(end_at.replace(" ", "+"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid ISO-8601 datetime format: {exc}")

    if dt_start.tzinfo is None:
        dt_start = dt_start.replace(tzinfo=timezone.utc)
    if dt_end.tzinfo is None:
        dt_end = dt_end.replace(tzinfo=timezone.utc)

    data = logistics_service.find_equipment(
        session=session,
        item_name=item_name,
        venue_id=venue_id,
        start_at=dt_start,
        end_at=dt_end,
        quantity_needed=quantity_needed,
    )
    return Envelope(data=data)


@router.get("/equipment/{id}/failure-analysis", response_model=Envelope[Dict[str, Any]])
def failure_analysis(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Analyzes dependent sessions, alternatives, and transfer feasibility for equipment failure."""
    data = logistics_service.analyze_failure(session, id)
    return Envelope(data=data)


@router.post("/stocktake", response_model=Envelope[Dict[str, Any]])
def stocktake_adjust(
    body: StocktakeAdjustBody,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Records stocktake discrepancy adjustment with mandatory justification reason."""
    req = ChangeRequest(
        action="logistics.stocktake_adjust",
        entity_type="inventory_item",
        entity_id=body.payload.get("item_id", ""),
        payload=body.payload,
        reason=body.reason or body.payload.get("reason"),
        actor=actor,
        idempotency_key=idempotency_key,
    )
    res = execute_change(req, session)
    if res.status == "REJECTED":
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in res.violations])
    return Envelope(data=res.model_dump())


@router.get("/ledger/balance", response_model=Envelope[Dict[str, Any]])
def verify_ledger_balance(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Verifies double-entry ledger balance consistency across all items and locations."""
    data = logistics_service.verify_balance(session)
    return Envelope(data=data)


@router.get("/reconciliation-flags", response_model=Envelope[List[Dict[str, Any]]])
def get_reconciliation_flags(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Surfaces ambiguous data flags (the 'camera' case and 'tables' needs check)."""
    data = logistics_service.get_reconciliation_flags(session)
    return Envelope(data=data)


@router.get("/reports/inventory-plan")
def get_inventory_plan_report(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Exports inventory_plan.csv."""
    csv_data = inventory_plan_csv(session)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_plan.csv"},
    )


@router.get("/reports/equipment-gap")
def get_equipment_gap_report(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Exports equipment_gap.csv."""
    csv_data = equipment_gap_csv(session)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=equipment_gap.csv"},
    )
